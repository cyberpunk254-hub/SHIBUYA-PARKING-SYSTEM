# vehicle_capture.py — Vehicle Capture Module
# Records vehicles on entry and finds their records on exit.

from datetime import datetime

from storage import vehicle_capture, active_vehicles, counters
from slot_management import allocate_parking_slot, release_parking_slot
from exception_handling import log_exception


def generate_vehicle_id():
    """Produce the next unique visit ID: VC001, VC002, VC003 ..."""
    vehicle_id = "VC" + str(counters["vehicle"]).zfill(3)
    counters["vehicle"] += 1
    return vehicle_id


# ---------------------------------------------------------------
# ENTRY
# ---------------------------------------------------------------

def record_vehicle_entry(number_plate):
    """Vehicle Capture (Entry), steps 4 to 7.

    Returns a dictionary describing the outcome, so the caller can
    show the driver the right message.
    """

    # Step 4a: the plate must not already be inside.
    if number_plate in active_vehicles:
        log_exception("DUPLICATE_PLATE", number_plate)
        return {
            "success": False,
            "reason": "DUPLICATE_PLATE",
            "message": "This number plate is already recorded inside the parking lot. Attendant assistance required."
        }

    # Step 4b: ask Slot Management for a slot.
    slot_taken = allocate_parking_slot()
    if slot_taken is None:
        log_exception("PARKING_FULL", number_plate)
        return {
            "success": False,
            "reason": "PARKING_FULL",
            "message": "Parking Full - all slots occupied."
        }

    # Step 4: entryTime is captured automatically, with its date.
    entry_time = datetime.now()

    # Step 5: create the permanent visit record.
    vehicle_id = generate_vehicle_id()
    vehicle_capture[vehicle_id] = {
        "numberPlate": number_plate,
        "entryTime": entry_time,
        "exitTime": None,
        "slotTaken": slot_taken
    }

    # Step 6: store the fast-lookup entry used while the car is inside.
    active_vehicles[number_plate] = {
        "vehicleID": vehicle_id,
        "entryTime": entry_time,
        "slotTaken": slot_taken
    }

    return {
        "success": True,
        "vehicleID": vehicle_id,
        "slotTaken": slot_taken,
        "entryTime": entry_time
    }


# ---------------------------------------------------------------
# EXIT
# ---------------------------------------------------------------

def find_vehicle_by_plate(number_plate):
    """Step 4: hash-map lookup by number plate.

    Python dictionaries are hash maps, so this is the near-instant
    lookup described in the design document.
    """
    return active_vehicles.get(number_plate)


def find_vehicle_by_slot(slot_taken):
    """Step 4a fallback: attendant search by slot.

    Every record in the active map belongs to a vehicle currently
    inside, so a match here is the car occupying that slot. This is
    a linear search, since the map is keyed by number plate.
    """
    for number_plate, record in active_vehicles.items():
        if record["slotTaken"] == slot_taken:
            return number_plate, record
    return None, None


def complete_vehicle_exit(number_plate):
    """Steps 8 to 11, run only after payment is VERIFIED.

    Records exitTime, releases the slot, and removes the vehicle
    from the active map. The permanent record stays in
    vehicle_capture.
    """
    record = active_vehicles.get(number_plate)
    if record is None:
        return None

    vehicle_id = record["vehicleID"]

    # Step 8: exitTime is finalized once the vehicle may leave.
    vehicle_capture[vehicle_id]["exitTime"] = datetime.now()

    # Step 10: the slot is only released after the vehicle leaves.
    release_parking_slot(record["slotTaken"])

    # Step 11: remove from the active map; the permanent record remains.
    del active_vehicles[number_plate]

    return vehicle_capture[vehicle_id]