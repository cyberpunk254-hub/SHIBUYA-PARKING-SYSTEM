# slot_management.py — Slot Management Module
# Monitors slot status, allocates slots and releases them.

from storage import parking_slots


def calculate_available_slots():
    """Algorithm 1: count how many slots are currently AVAILABLE."""
    available = 0
    for status in parking_slots.values():
        if status == "AVAILABLE":
            available += 1
    return available


def allocate_parking_slot():
    """Algorithm 2: mark the first AVAILABLE slot as OCCUPIED and
    return its ID. Returns None when the lot is full."""
    for slot_id, status in parking_slots.items():
        if status == "AVAILABLE":
            parking_slots[slot_id] = "OCCUPIED"
            return slot_id          # stops the search immediately
    return None                     # loop ended: "Parking Full"


def release_parking_slot(slot_taken):
    """Algorithm 3: mark a slot AVAILABLE again after a vehicle leaves."""
    if slot_taken in parking_slots:
        parking_slots[slot_taken] = "AVAILABLE"