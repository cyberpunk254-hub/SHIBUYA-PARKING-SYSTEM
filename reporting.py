# reporting.py — Administrative Reporting Module
# Reads existing records to produce management information.
# No new data structure is required for this module.

from storage import vehicle_capture, billing, exception_log


def generate_report():
    """Administrative Reporting algorithm, steps 2 to 6."""

    # Step 2: completed visits are those whose exitTime is not empty.
    completed_visits = {}
    for vehicle_id, record in vehicle_capture.items():
        if record["exitTime"] is not None:
            completed_visits[vehicle_id] = record

    # Steps 3 and 4 read billing and exception_log directly.

    # Step 5: the figures management needs.
    total_collected = 0
    failed_attempts = []
    for transaction_id, transaction in billing.items():
        if transaction["paymentStatus"] == "VERIFIED":
            total_collected += transaction["feeAmount"]
        elif transaction["paymentStatus"] == "FAILED":
            failed_attempts.append(transaction_id)

    return {
        "completedVisits": completed_visits,
        "completedCount": len(completed_visits),
        "payments": billing,
        "totalCollected": total_collected,
        "failedAttempts": failed_attempts,
        "exceptions": exception_log
    }