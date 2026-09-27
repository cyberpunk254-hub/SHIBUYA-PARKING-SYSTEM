# main.py — Shibuya Parking System
# Entry point of the web application. Defines the routes that connect
# the browser to the system's modules.

from datetime import datetime

from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from storage import parking_slots, vehicle_capture, active_vehicles, billing, exception_log
from slot_management import calculate_available_slots
from vehicle_capture import (
    record_vehicle_entry,
    find_vehicle_by_plate,
    find_vehicle_by_slot,
    complete_vehicle_exit,
)
from billing import (
    calculate_duration_hours,
    calculate_fee,
    has_pending_payment,
    create_payment_transaction,
    confirm_payment,
    fail_payment,
    update_rate_fees,
    rate_labels,
    request_mpesa_payment,
    refresh_mpesa_status,

)
from exception_handling import log_exception
from reporting import generate_report

from mpesa import daraja_enabled, normalize_phone

app = FastAPI(title="Shibuya Parking System")

# Serve CSS and other static files from the /static folder.
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML pages are rendered from the /templates folder.
templates = Jinja2Templates(directory="templates")

# Every template can call rate_labels() to show the current rates.
templates.env.globals["rate_labels"] = rate_labels


# ---------------------------------------------------------------
# SLOT DISPLAY
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def display_board(request: Request):
    """Slot Display: the live board drivers see before entry."""
    return templates.TemplateResponse(request, "display.html", {
        "available": calculate_available_slots(),
        "total": len(parking_slots),
        "slots": parking_slots,
    })

@app.get("/api/availability")
def api_availability():
    """JSON version of the board, kept for testing via /docs."""
    return {
        "availableSlots": calculate_available_slots(),
        "totalSlots": len(parking_slots),
    }


@app.get("/slots")
def view_slots():
    """The full status of every slot."""
    return parking_slots


# ---------------------------------------------------------------
# ENTRY
# ---------------------------------------------------------------

@app.post("/entry")
def vehicle_entry(number_plate: str):
    """Record a vehicle arriving at the entry gate."""
    # "kda 123x " and "KDA 123X" are the same vehicle, so store one form.
    number_plate = number_plate.strip().upper()

    if not number_plate:
        return {
            "success": False,
            "reason": "EMPTY_PLATE",
            "message": "Enter a number plate to check in.",
        }

    result = record_vehicle_entry(number_plate)
    result["availableSlots"] = calculate_available_slots()
    return result

@app.get("/entry-page", response_class=HTMLResponse)
def entry_page(request: Request):
    """Check-in screen used at the entry gate."""
    return templates.TemplateResponse(request, "entry.html", {
        "available": calculate_available_slots(),
        "total": len(parking_slots),
    })

# ---------------------------------------------------------------
# EXIT
# ---------------------------------------------------------------

@app.post("/exit/lookup")
def exit_lookup(number_plate: str):
    """Step 4: find the vehicle's record and calculate its fee.

    The fee is calculated from currentTime, the moment the vehicle
    reaches the barrier. exitTime is only recorded later, once
    payment is verified.
    """
    number_plate = number_plate.strip().upper()
    record = find_vehicle_by_plate(number_plate)

    if record is None:
        log_exception("VEHICLE_NOT_FOUND", number_plate)
        return {
            "success": False,
            "reason": "VEHICLE_NOT_FOUND",
            "message": "No record found for this number plate. Attendant assistance required.",
        }

    current_time = datetime.now()
    duration_hours = calculate_duration_hours(record["entryTime"], current_time)
    fee_amount = calculate_fee(duration_hours)

    return {
        "success": True,
        "vehicleID": record["vehicleID"],
        "numberPlate": number_plate,
        "slotTaken": record["slotTaken"],
        "entryTime": record["entryTime"],
        "currentTime": current_time,
        "durationHours": round(duration_hours, 2),
        "feeAmount": fee_amount,
    }


@app.post("/exit/lookup-by-slot")
def exit_lookup_by_slot(slot_taken: str):
    """Step 4a fallback: attendant searches by slot when the plate
    cannot be matched."""
    slot_taken = slot_taken.strip().upper()
    number_plate, record = find_vehicle_by_slot(slot_taken)

    if record is None:
        return {
            "success": False,
            "reason": "VEHICLE_NOT_FOUND",
            "message": "No vehicle is recorded in that slot.",
        }

    return {
        "success": True,
        "numberPlate": number_plate,
        "message": "Confirm this number plate with the driver before continuing.",
    }


# ---------------------------------------------------------------
# PAYMENT
# ---------------------------------------------------------------

@app.post("/payment/start")
def start_payment(number_plate: str, payment_method: str, phone: str = None):
    """Step 9: create a payment attempt with status PENDING.

    For M-Pesa with Daraja switched on, this also sends the STK Push
    prompt to the driver's phone.
    """
    number_plate = number_plate.strip().upper()
    record = find_vehicle_by_plate(number_plate)
    if record is None:
        return {"success": False, "message": "No active record for this number plate."}

    vehicle_id = record["vehicleID"]

    # Step 10: one attempt at a time, so a slow confirmation cannot
    # cause the driver to pay twice.
    if has_pending_payment(vehicle_id):
        return {
            "success": False,
            "reason": "PAYMENT_PENDING",
            "message": "A payment attempt is already pending for this vehicle.",
        }

    duration_hours = calculate_duration_hours(record["entryTime"], datetime.now())
    fee_amount = calculate_fee(duration_hours)

    use_daraja = payment_method == "M-Pesa" and daraja_enabled() and fee_amount > 0
    if use_daraja:
        msisdn = normalize_phone(phone or "")
        if msisdn is None:
            return {"success": False, "message": "Enter a valid Safaricom number, for example 0712 345 678."}

    transaction_id = create_payment_transaction(vehicle_id, fee_amount, payment_method)

    if use_daraja:
        push = request_mpesa_payment(transaction_id, msisdn)
        if not push["ok"]:
            return {
                "success": False,
                "message": "M-Pesa couldn't send the prompt (" + push["message"] + "). Try again or choose another method.",
            }

    return {
        "success": True,
        "transactionID": transaction_id,
        "feeAmount": fee_amount,
        "paymentStatus": "PENDING",
        "paymentMode": "daraja" if use_daraja else "simulate",
    }


@app.post("/payment/confirm")
def payment_confirm(transaction_id: str, payment_reference: str = None):
    """Step 11: the payment provider confirms the attempt."""
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    confirm_payment(transaction_id, payment_reference)
    return {
        "success": True,
        "transactionID": transaction_id,
        "paymentStatus": "VERIFIED",
    }


@app.post("/payment/fail")
def payment_fail(transaction_id: str):
    """Step 12: the attempt was rejected or timed out."""
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    fail_payment(transaction_id)
    log_exception("PAYMENT_FAILED", billing[transaction_id]["vehicleID"])
    return {
        "success": True,
        "transactionID": transaction_id,
        "paymentStatus": "FAILED",
        "message": "Payment failed. The driver may retry, which creates a new transaction.",
    }


# ---------------------------------------------------------------
# BARRIER CONTROL
# ---------------------------------------------------------------

@app.post("/payment/start")
def start_payment(number_plate: str, payment_method: str, phone: str = None):
    """Step 9: create a payment attempt with status PENDING.

    For M-Pesa with Daraja switched on, this also sends the STK Push
    prompt to the driver's phone.
    """
    number_plate = number_plate.strip().upper()
    record = find_vehicle_by_plate(number_plate)
    if record is None:
        return {"success": False, "message": "No active record for this number plate."}

    vehicle_id = record["vehicleID"]

    # Step 10: one attempt at a time, so a slow confirmation cannot
    # cause the driver to pay twice.
    if has_pending_payment(vehicle_id):
        return {
            "success": False,
            "reason": "PAYMENT_PENDING",
            "message": "A payment attempt is already pending for this vehicle.",
        }

    duration_hours = calculate_duration_hours(record["entryTime"], datetime.now())
    fee_amount = calculate_fee(duration_hours)

    use_daraja = payment_method == "M-Pesa" and daraja_enabled() and fee_amount > 0
    if use_daraja:
        msisdn = normalize_phone(phone or "")
        if msisdn is None:
            return {"success": False, "message": "Enter a valid Safaricom number, for example 0712 345 678."}

    transaction_id = create_payment_transaction(vehicle_id, fee_amount, payment_method)

    if use_daraja:
        push = request_mpesa_payment(transaction_id, msisdn)
        if not push["ok"]:
            return {
                "success": False,
                "message": "M-Pesa couldn't send the prompt (" + push["message"] + "). Try again or choose another method.",
            }

    return {
        "success": True,
        "transactionID": transaction_id,
        "feeAmount": fee_amount,
        "paymentStatus": "PENDING",
        "paymentMode": "daraja" if use_daraja else "simulate",
    }

@app.post("/payment/confirm")
def payment_confirm(transaction_id: str, payment_reference: str = None):
    """Step 11: the payment provider confirms the attempt."""
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    confirm_payment(transaction_id, payment_reference)
    return {
        "success": True,
        "transactionID": transaction_id,
        "paymentStatus": "VERIFIED",
    }


@app.post("/payment/fail")
def payment_fail(transaction_id: str):
    """Step 12: the attempt was rejected or timed out."""
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    fail_payment(transaction_id)
    log_exception("PAYMENT_FAILED", billing[transaction_id]["vehicleID"])
    return {
        "success": True,
        "transactionID": transaction_id,
        "paymentStatus": "FAILED",
        "message": "Payment failed. The driver may retry, which creates a new transaction.",
    }


# ---------------------------------------------------------------
# BARRIER CONTROL
# ---------------------------------------------------------------

@app.post("/barrier/exit")
def barrier_exit(number_plate: str, transaction_id: str):
    """Barrier Control: open the exit barrier only on a VERIFIED payment,
    then complete the exit (steps 8 to 11)."""
    number_plate = number_plate.strip().upper()
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    # For a real M-Pesa payment, ask Safaricom for the latest result first.
    outcome = refresh_mpesa_status(transaction_id)

    status = billing[transaction_id]["paymentStatus"]

    if status == "PENDING":
        return {
            "barrierOpen": False,
            "paymentStatus": status,
            "message": "Waiting for payment confirmation. Please wait.",
        }

    if status == "FAILED":
        reason = outcome["message"] if outcome and outcome["status"] == "FAILED" else None
        return {
            "barrierOpen": False,
            "paymentStatus": status,
            "message": "Payment not received. The barrier remains closed.",
            "reason": reason,
        }

    # VERIFIED: the vehicle may leave.
    completed = complete_vehicle_exit(number_plate)
    if completed is None:
        return {"success": False, "message": "No active record for this number plate."}

    return {
        "barrierOpen": True,
        "paymentStatus": status,
        "exitTime": completed["exitTime"],
        "slotReleased": completed["slotTaken"],
        "availableSlots": calculate_available_slots(),
    }


# ---------------------------------------------------------------
# PAGES
# ---------------------------------------------------------------

@app.get("/exit-page", response_class=HTMLResponse)
def exit_page(request: Request):
    """Pay-and-exit screen used at the exit barrier."""
    return templates.TemplateResponse(request, "exit.html", {
        "mpesa_live": bool(daraja_enabled()),
    })
# ---------------------------------------------------------------
# ADMINISTRATIVE REPORTING
# ---------------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """Management dashboard: reads everything from generate_report()."""
    return templates.TemplateResponse(request, "admin.html", {})


@app.get("/admin/report")
def admin_report():
    """Management view: visits, payments, totals and exceptions."""
    return generate_report()


@app.get("/admin/exceptions")
def admin_exceptions():
    """The exception audit trail."""
    return exception_log


@app.get("/api/rates")
def api_rates():
    """Current rates, in plain language."""
    return rate_labels()


@app.post("/admin/rates")
def admin_update_rates(fees: dict[str, int] = Body(...)):
    """Management saves new fee amounts, e.g. {"RATE002": 60}."""
    return update_rate_fees(fees)