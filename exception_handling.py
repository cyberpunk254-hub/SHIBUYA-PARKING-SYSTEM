# exception_handling.py — Exception Handling Module
# Records every exception the system detects, providing an audit trail.

from datetime import datetime
from storage import exception_log


def log_exception(exception_type, number_plate, resolution=None):
    """Append an exception to exception_log.

    A list is used because entries are only ever added in time order
    and reviewed in that order, so no lookup by key is needed.
    """
    exception_log.append({
        "created_at": datetime.now(),
        "type": exception_type,
        "numberPlate": number_plate,
        "resolution": resolution
    })