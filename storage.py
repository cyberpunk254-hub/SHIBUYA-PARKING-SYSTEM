# storage.py — Shibuya Parking System
# All shared data structures (the "dynamic database" of the design document).
# Keeping them in one module avoids circular imports between modules.

# ---------------------------------------------------------------
# Table 4: parking_slots — slotID -> status
# ---------------------------------------------------------------

TOTAL_SLOTS = 50

parking_slots = {}
for number in range(1, TOTAL_SLOTS + 1):
    slot_id = "A" + str(number).zfill(2)   # 1 -> "A01"
    parking_slots[slot_id] = "AVAILABLE"


# ---------------------------------------------------------------
# Table 1: vehicle_capture — vehicleID -> visit record
# ---------------------------------------------------------------

vehicle_capture = {}


# ---------------------------------------------------------------
# Active hash map — numberPlate -> {vehicleID, entryTime, slotTaken}
# Fast index of vehicles currently inside.
# ---------------------------------------------------------------

active_vehicles = {}


# ---------------------------------------------------------------
# Table 2: billing — transactionID -> payment attempt
# ---------------------------------------------------------------

billing = {}


# ---------------------------------------------------------------
# Table 3: rate_rules — ruleID -> fee bracket
# The hour brackets are fixed here. The fee amounts can be changed by
# management from the Admin page; their changes are saved to
# rates.json and loaded back on startup, so no code edit is needed.
# 9999 means "no upper limit".
# ---------------------------------------------------------------

import json
from pathlib import Path

RATES_FILE = Path(__file__).parent / "rates.json"

DEFAULT_RATE_RULES = {
    "RATE001": {"minHours": 0, "maxHours": 0.5, "fee": 0},
    "RATE002": {"minHours": 0.5, "maxHours": 2, "fee": 50},
    "RATE003": {"minHours": 2, "maxHours": 4, "fee": 100},
    "RATE004": {"minHours": 4, "maxHours": 6, "fee": 300},
    "RATE005": {"minHours": 6, "maxHours": 9999, "fee": 500},
}

# Start from a copy of the defaults...
rate_rules = {rule_id: dict(rule) for rule_id, rule in DEFAULT_RATE_RULES.items()}

# ...then apply any fees management has saved before.
if RATES_FILE.exists():
    try:
        saved_fees = json.loads(RATES_FILE.read_text())
        for rule_id, fee in saved_fees.items():
            if rule_id in rate_rules:
                rate_rules[rule_id]["fee"] = fee
    except (json.JSONDecodeError, OSError):
        pass   # a damaged file falls back to the default fees


def save_rate_fees():
    """Write the current fee amounts to rates.json."""
    fees = {rule_id: rule["fee"] for rule_id, rule in rate_rules.items()}
    RATES_FILE.write_text(json.dumps(fees, indent=2))


# ---------------------------------------------------------------
# Table 5: exception_log — appended in time order
# ---------------------------------------------------------------

exception_log = []


# ---------------------------------------------------------------
# ID counters, wrapped in a dictionary.
# A dictionary is used so other modules can update the numbers
# without needing the `global` keyword across files.
# ---------------------------------------------------------------

counters = {
    "vehicle": 1,
    "transaction": 1
}