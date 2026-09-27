# main.py — Shibuya Parking System
# Entry point of the web application. Defines the routes that connect
# the browser to the system's modules.

from datetime import datetime

from fastapi import FastAPI

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
)
from exception_handling import log_exception
from reporting import generate_report

app = FastAPI(title="Shibuya Parking System")


# ---------------------------------------------------------------
# SLOT DISPLAY
# ---------------------------------------------------------------

@app.get("/")
def home():
    """Live availability, as shown on the board at the gate."""
    return {
        "system": "Shibuya Parking System",
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
    result = record_vehicle_entry(number_plate)
    result["availableSlots"] = calculate_available_slots()
    return result


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
def start_payment(number_plate: str, payment_method: str):
    """Step 9: create a payment attempt with status PENDING."""
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
    transaction_id = create_payment_transaction(vehicle_id, fee_amount, payment_method)

    return {
        "success": True,
        "transactionID": transaction_id,
        "feeAmount": fee_amount,
        "paymentStatus": "PENDING",
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
    if transaction_id not in billing:
        return {"success": False, "message": "Unknown transaction."}

    status = billing[transaction_id]["paymentStatus"]

    if status == "PENDING":
        return {
            "barrierOpen": False,
            "paymentStatus": status,
            "message": "Waiting for payment confirmation. Please wait.",
        }

    if status == "FAILED":
        return {
            "barrierOpen": False,
            "paymentStatus": status,
            "message": "Payment not received. The barrier remains closed.",
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
# ADMINISTRATIVE REPORTING
# ---------------------------------------------------------------

@app.get("/admin/report")
def admin_report():
    """Management view: visits, payments, totals and exceptions."""
    return generate_report()


@app.get("/admin/exceptions")
def admin_exceptions():
    """The exception audit trail."""
    return exception_log