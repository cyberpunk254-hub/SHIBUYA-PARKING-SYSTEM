# billing.py — Billing & Payment Module
# Calculates parking duration and fees, and records payment attempts.

from datetime import datetime
from storage import billing, rate_rules, counters, save_rate_fees


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
