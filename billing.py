# billing.py — Billing & Payment Module
# Calculates parking duration and fees, and records payment attempts.

from datetime import datetime
from storage import billing, rate_rules, counters, save_rate_fees

import time

from mpesa import daraja_enabled, stk_push, stk_query
from exception_handling import log_exception

def generate_transaction_id():
    """Produce the next unique payment attempt ID: TXN001, TXN002 ..."""
    transaction_id = "TXN" + str(counters["transaction"]).zfill(3)
    counters["transaction"] += 1
    return transaction_id


def calculate_duration_hours(entry_time, current_time):
    """Steps 3 to 5: how long the vehicle stayed, in hours.

    Subtracting two datetime objects gives the exact gap including
    whole days, so stays crossing midnight or lasting over 24 hours
    are handled correctly.
    """
    difference = current_time - entry_time
    duration_minutes = difference.total_seconds() / 60
    duration_hours = duration_minutes / 60
    return duration_hours


def calculate_fee(duration_hours):
    """Step 6: find the matching rate rule and return its fee.

    A rule matches when minHours < durationHours <= maxHours.
    The first rule also covers a duration of exactly 0.
    """
    for rule in rate_rules.values():
        if rule["minHours"] < duration_hours <= rule["maxHours"]:
            return rule["fee"]
        if duration_hours == 0 and rule["minHours"] == 0:
            return rule["fee"]
    return None


def has_pending_payment(vehicle_id):
    """Step 10: block a new attempt while one is still PENDING,
    so a slow confirmation cannot cause a double payment."""
    for transaction in billing.values():
        if transaction["vehicleID"] == vehicle_id and transaction["paymentStatus"] == "PENDING":
            return True
    return False


def create_payment_transaction(vehicle_id, fee_amount, payment_method):
    """Step 9: record a new payment attempt with status PENDING."""
    transaction_id = generate_transaction_id()
    billing[transaction_id] = {
        "vehicleID": vehicle_id,
        "feeAmount": fee_amount,
        "paymentStatus": "PENDING",
        "payment_method": payment_method,
        "payment_reference": None,
        "created_at": datetime.now()
    }
    return transaction_id


def confirm_payment(transaction_id, payment_reference=None):
    """Step 11: mark an attempt VERIFIED and store its reference code."""
    billing[transaction_id]["paymentStatus"] = "VERIFIED"
    billing[transaction_id]["payment_reference"] = payment_reference


def fail_payment(transaction_id):
    """Step 12: mark an attempt FAILED so the driver may retry."""
    billing[transaction_id]["paymentStatus"] = "FAILED"


def update_rate_fees(new_fees):
    """Management changes fee amounts. Brackets stay fixed.

    Every value is checked before anything changes, so a bad entry
    can never leave the rates half-updated.
    """
    for rule_id, fee in new_fees.items():
        if rule_id not in rate_rules:
            return {"success": False, "message": "Unknown rate " + rule_id + "."}
        if fee < 0:
            return {"success": False, "message": "Fees can't be negative."}

    for rule_id, fee in new_fees.items():
        rate_rules[rule_id]["fee"] = fee

    save_rate_fees()
    return {"success": True, "message": "Rates saved. The next vehicle to exit pays the new rates."}


def _hours_text(hours):
    """0.5 -> '30 minutes', 1 -> '1 hour', 4 -> '4 hours'."""
    if hours < 1:
        return str(int(hours * 60)) + " minutes"
    if hours == 1:
        return "1 hour"
    return "{:g}".format(hours) + " hours"


def rate_labels():
    """Plain-language description of each bracket, for display.

    Built from rate_rules every time it's called, so the website
    always shows the current rates.
    """
    labels = []
    for rule_id, rule in rate_rules.items():
        if rule["maxHours"] >= 9999:
            label = "Over " + _hours_text(rule["minHours"])
        else:
            label = "Up to " + _hours_text(rule["maxHours"])
        labels.append({
            "ruleID": rule_id,
            "label": label,
            "fee": rule["fee"],
            "feeText": "Free" if rule["fee"] == 0 else "Ksh " + str(rule["fee"]),
        })
    return labels

# ---------------------------------------------------------------
# M-PESA (DARAJA)
# ---------------------------------------------------------------

# When each M-Pesa payment was last checked, so the barrier's
# 2-second polling doesn't flood Safaricom with requests.
_last_mpesa_check = {}

# Step 12 of the design: a payment with no confirmation within this
# time becomes FAILED, so the driver is never stuck waiting forever.
PAYMENT_TIME_LIMIT_SECONDS = 120

def request_mpesa_payment(transaction_id, phone):
    """Send the STK Push prompt for a transaction that is already PENDING.

    If Safaricom refuses, the attempt is marked FAILED straight away,
    so the driver can retry with a new transaction.
    """
    transaction = billing[transaction_id]
    result = stk_push(phone, transaction["feeAmount"], transaction_id, "Parking fee")

    if not result["ok"]:
        fail_payment(transaction_id)
        log_exception("PAYMENT_FAILED", transaction["vehicleID"])
        return result

    # With the query method, Safaricom's CheckoutRequestID is the
    # reference that identifies this payment.
    transaction["payment_reference"] = result["checkoutRequestID"]
    return result


def refresh_mpesa_status(transaction_id):
    """For a PENDING M-Pesa payment, ask Safaricom for the latest result
    and update paymentStatus. Returns Safaricom's answer, or None if
    no check was needed or it's too soon to check again.
    """
    transaction = billing.get(transaction_id)
    if (transaction is None
            or transaction["paymentStatus"] != "PENDING"
            or transaction["payment_method"] != "M-Pesa"
            or not transaction["payment_reference"]
            or not daraja_enabled()):
        return None

    # Ask Safaricom at most once every 5 seconds per payment.
    now = time.time()
    if now - _last_mpesa_check.get(transaction_id, 0) < 5:
        return None
    _last_mpesa_check[transaction_id] = now

    outcome = stk_query(transaction["payment_reference"])

    if outcome["status"] == "VERIFIED":
        transaction["paymentStatus"] = "VERIFIED"
    elif outcome["status"] == "FAILED":
        transaction["paymentStatus"] = "FAILED"
        log_exception("PAYMENT_FAILED", transaction["vehicleID"])
    else:
        # Still PENDING: give up once the time limit has passed.
        waited = (datetime.now() - transaction["created_at"]).total_seconds()
        if waited > PAYMENT_TIME_LIMIT_SECONDS:
            transaction["paymentStatus"] = "FAILED"
            log_exception("PAYMENT_FAILED", transaction["vehicleID"])
            outcome = {"status": "FAILED", "message": "No confirmation arrived within 2 minutes."}

    return outcome