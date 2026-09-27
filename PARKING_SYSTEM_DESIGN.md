# SHIBUYA PARKING SYSTEM

**MULTIMEDIA UNIVERSITY OF KENYA**

| | |
|---|---|
| **Name** | Allan Gachuki Gichuru |
| **Registration Number** | CIT-227-058/2025 |
| **Programme** | Software Engineering |
| **Faculty** | Computing and Information Technology |
| **Unit** | CCS 2124 Data Structures and Algorithms |
| **Assignment** | Development of a Modern Parking System |
| **Lecturer** | Patrick Mokodir |
| **Date of Submission** | 27th September 2026 |

---

## Analysis of Terms of Reference

After a deep analysis of the task at hand, I came to a conclusion that the main functions of the system would be visual display of slots, recording vehicles on arrival, calculating time + fees on exit and opening the barrier on payment. I decided to break down the client's requirements into specific modules each with a clear job (like departments in a company). That is a piece of code that's responsible for one clear task, and that can talk to other modules when needed, but doesn't try to do everything itself. The scope explicitly excludes online pre-booking of bays, valet operations, integration with third-party loyalty schemes and automated number plate blacklisting.

### The proposed modules are as follows

1. **Slot Management Module** – monitors slot status, allocates available slots, releases occupied slots and displays live availability.
2. **Vehicle Capture Module** – records vehicles' data (plate, time, slot allocated) during entry and handles exit lookup (finds the matching entry record when a car leaves).
3. **Billing & Payment Module** – takes the entry/exit times from Vehicle Capture, calculates duration, derives the fees to be paid and handles payment.
4. **Barrier Control Module** – opens the exit barrier after payment is verified.
5. **Exception Handling Module** – handles system exceptions such as unavailable slots, missing vehicle records and payment failures.
6. **Administrative Reporting Module** – uses vehicle and payment records to support administrative reporting.

### The flow of the system

Slot Management (availability/allocation) → Vehicle Capture (entry) → Vehicle Capture (exit) → Billing & Payment → Barrier Control → Slot Management (slot released/display updated)

The developed algorithms for each module are as listed below.

---

## a. Slot Management Module

**Data structure:** Dictionary (slot ID → status). Each parking slot is represented by a unique slot ID and its current status, either `AVAILABLE` or `OCCUPIED`.

```python
parking_slots = {"A01": "OCCUPIED", "A02": "AVAILABLE", "A03": "AVAILABLE"}
```

### Algorithm 1: Calculate Available Slots

```
1. Begin
2. Set availableSlots = 0
3. For each slot in parking_slots:
       4. If the slot status is AVAILABLE, increase availableSlots by 1
5. Display availableSlots
6. Repeat as required to keep the display updated
7. End
```

### Algorithm 2: Allocate Parking Slot

```
1. Begin
2. For each slot in parking_slots (loop)
       3. If the slot status is AVAILABLE, take it.
       4. Mark the slot as OCCUPIED
       5. Return the slot ID as slotTaken and stop the search
6. If the loop ends without finding an available slot, report "Parking Full"
7. End
```

### Algorithm 3: Release Parking Slot

```
1. Begin
2. Receive slotTaken from the vehicle's parking record
3. Find slotTaken in parking_slots
4. Mark the slot as AVAILABLE
5. Update the slot display
6. End
```

---

## b. Vehicle Capture Module (Entry)

```
1.  Begin
2.  If availableSlots > 0, driver proceeds; else driver leaves
3.  Vehicle approaches gate
4.  Capture numberPlate (scanned/typed) and entryTime (automatic, including the date).
4a. If numberPlate already exists in the active hash map → do not create a new
    record or overwrite the existing one; keep the entry barrier closed, alert the
    attendant and log the exception in the Exception Handling module. Continue only
    after the attendant resolves it.
4b. Request a slot from the Slot Management Module. If it returns "Parking Full" →
    keep the entry barrier closed, display "Parking Full – all slots occupied" and
    end the entry process. Otherwise receive slotTaken and open the entry barrier.
5.  Generate a new vehicleID (e.g. VC007) and create the visit record in
    vehicle_capture (numberPlate, entryTime, slotTaken) with exitTime = None.
6.  Store {vehicleID, entryTime, slotTaken} in the active hash map, keyed by
    numberPlate, for fast lookup at exit.
7.  Vehicle parks at assigned slot
8.  End
```

---

## c. Vehicle Capture Module (Exit)

```
1.  Begin
2.  Vehicle approaches barrier; barrier remains closed until payment clears.
3.  numberPlate scanned/typed again
4.  Run numberPlate through hash function → locates record
4a. If no matching record is found for the scanned numberPlate:
       - Alert attendant
       - Attendant asks driver for their slotTaken (e.g. "D47")
       - System searches the active hash map for a record where slotTaken = "D47"
         (every record in the active hash map belongs to a vehicle currently inside).
       - If found and the attendant confirms the vehicle's numberPlate matches the
         record → proceed with that record from step 5 onward
5.  Set currentTime to the time the vehicle reaches the barrier.
6.  Billing & Payment Module receives entryTime + currentTime, calculates duration
    and fees.
7.  Billing & Payment processes the fee; each payment attempt is recorded in billing
    using the vehicleID from the active record.
8.  If paymentStatus = VERIFIED, record exitTime (with its date) in the vehicle's
    vehicle_capture record.
9.  Barrier opens, vehicle leaves.
10. Release the slot using the Release Parking Slot algorithm.
11. Remove the vehicle's entry from the active hash map (its permanent record is
    already complete in vehicle_capture).
12. End
```

> **Slot Release Ordering:** The parking slot remains `OCCUPIED` until the vehicle has been authorized to exit and has passed through the barrier. After the vehicle leaves, the slot is marked `AVAILABLE`. This prevents the system from displaying or allocating a slot as available while it is still physically occupied.

### Why currentTime matters

Suppose:

- Entry time = 10:00
- Vehicle reaches barrier = 14:00
- Fee calculated using 14:00 → duration = 4 hours
- M-Pesa payment takes 2 minutes to confirm
- Payment confirmed = 14:02
- Vehicle leaves = 14:03

The clean design is: Billing uses the current time when the vehicle reaches the exit to calculate the fee, while `exitTime` in the parking record is only finalized when the vehicle is actually authorized to leave.

---

## d. Billing & Payment Module

```
1.  Begin
2.  Retrieve entryTime (with its date) from Vehicle Capture and receive currentTime
    (with its date) from the exit process.
3.  Convert the clock part of entryTime and currentTime to total minutes since
    midnight, giving conv_entryTime and conv_currentTime.
4.  dayDifference = number of days between the entry date and the current date.
    durationMinutes = (dayDifference × 1440) + (conv_currentTime − conv_entryTime)
5.  durationHours = durationMinutes / 60
6.  Loop through rate_rules and find the rule where
    minHours < durationHours ≤ maxHours (the first rule also includes
    durationHours = 0). Set feeAmount to that rule's fee. Because the step uses only
    the rule fields, management can change the brackets in rate_rules without
    changing this algorithm.
7.  Display feeAmount
8.  Driver selects payment method (M-Pesa, card, or cash)
9.  Create a new payment transaction with paymentStatus = PENDING.
10. Process the selected payment method. While paymentStatus = PENDING, the driver
    cannot start another payment attempt.
11. If payment is confirmed → paymentStatus = VERIFIED and record the payment
    details.
12. If payment is rejected, or no confirmation arrives within the time limit →
    paymentStatus = FAILED and record the failed attempt.
13. If VERIFIED → clear to proceed. If FAILED → keep the barrier closed and allow a
    retry, which creates a new transaction.
14. End
```

> **Why this matters:** Including the date allows the calculation to handle every case correctly: same-day stays, stays that cross midnight, and stays longer than 24 hours. For example, entry Monday 10:00 and exit Tuesday 11:00 gives (1 × 1440) + (660 − 600) = 1500 minutes = 25 hours, rather than the incorrect 1 hour.

```python
rate_rules = {
    "RATE001": {"minHours": 0, "maxHours": 0.5, "fee": 0},
    "RATE002": {"minHours": 0.5, "maxHours": 2, "fee": 50},
    "RATE003": {"minHours": 2, "maxHours": 4, "fee": 100},
    "RATE004": {"minHours": 4, "maxHours": 6, "fee": 300},
    "RATE005": {"minHours": 6, "maxHours": 9999, "fee": 500},  # 9999 means no upper limit
}
```

---

## e. Barrier Control Module

```
1. Begin
2. Retrieve paymentStatus from the Billing & Payment module
3. If paymentStatus = VERIFIED → barrier opens; if PENDING → wait and re-check
   paymentStatus (payment confirmation delay); if FAILED → barrier remains closed,
   and alert the attendant if payment still fails after retries.
4. End
```

Retries are handled by the Billing & Payment module, which creates a new transaction for each attempt. Barrier Control only reads `paymentStatus` and does not initiate payment.

The entry barrier is controlled by the Vehicle Capture module during entry (step 4b), which opens it only after a slot has been successfully allocated. Barrier Control governs the exit barrier.

---

## f. Exception Handling Module

```
1.  Begin
2.  Monitor the system for exceptions during entry, exit and payment processing.
3.  If no available slot is found → display "Parking Full" and prevent vehicle entry.
3a. If a scanned numberPlate at entry already exists in the active hash map → keep
    the entry barrier closed, do not overwrite the existing record, log the exception
    and require attendant assistance.
4.  If no matching vehicle record is found at exit → alert attendant and request
    slotTaken for a manual search.
5.  If the vehicle record is still not found → log the exception and require
    attendant assistance before proceeding.
6.  If paymentStatus = FAILED → keep the barrier closed, record the failed attempt
    and allow payment retry.
7.  If the exception is resolved → continue with the normal process; otherwise keep
    the affected operation on hold.
8.  End
```

---

## g. Administrative Reporting Module

```
1. Begin
2. Retrieve completed vehicle records from vehicle_capture (records whose exitTime
   is not empty).
3. Retrieve payment records from billing.
4. Retrieve exception records from exception_log.
5. Generate administrative information such as:
       • Number of vehicles that have completed parking visits.
       • Vehicle visit details such as vehicleID, numberPlate, entryTime, exitTime,
         and slotTaken.
       • Payment details such as transactionID, vehicleID, feeAmount, paymentStatus,
         and payment_method.
       • Total amount collected from verified payments.
       • FAILED payment attempts.
       • Exceptions recorded and how they were resolved.
6. Present the information to management for monitoring and reconciliation.
7. End
```

Administrative Reporting uses the existing `vehicle_capture`, `billing` and `exception_log` records. No new data structure is required for this module.

---

## Key assumptions I made during the process of algorithm design

- Driver assumed to be logical – won't approach gate if `availableSlots = 0`. The available slots are displayed on an electronic board at the gate that can be seen by drivers from afar. But also, `availableSlots` value would also be exposed via the web-based system in web or mobile view.
- **Barrier operation assumption:** The barrier can be opened automatically or manually by the attendant, so if automatic opening fails, an attendant can always open it manually.
- Time stored/converted to minutes-since-midnight to avoid incorrect clock subtraction.
  - For example, if time is captured normally like 1800 and 1630, the computer might subtract them like normal numbers e.g. 1800 - 1630 = 170. Real answer: 1hr 30mins.
  - **Actual fix:** Convert both numbers into total minutes since midnight first (e.g. 18:00 → 18*60 = 1080 minutes; 16:30 → 16*60 + 30 = 990 minutes), then subtract those two as plain numbers - now its honest arithmetic. The algorithm also uses the date part of `entryTime` and `currentTime` (`dayDifference` × 1440), so stays that cross midnight or last longer than 24 hours are calculated correctly.
- Hash table chosen for Vehicle Capture module because it gives near-instant lookup by number plate regardless of how many vehicles are parked, versus sorted/alphabetical search which gets slower as records grow.
- Payment retry logic added to handle real-world payment delays (e.g. M-Pesa confirmation lag).

---

## Description of the data structures and reasons for their use

**1) Slot Management Module**

The data structure used is a Dictionary (slot ID → status). Each slot has a unique identifier and a current status, so the system can monitor which slots are available or occupied, allocate an available slot, release it when a vehicle exits and support the live availability display.

**2) Vehicle Capture Module**

The data structures used are a hash map (keyed by `numberPlate`) and the `vehicle_capture` dictionary. The active hash map gives near-instant lookup of vehicles currently inside, regardless of how many vehicles are parked. At entry, the module also creates each visit's permanent record in `vehicle_capture`, a dictionary of dictionaries keyed by `vehicleID`, so that every visit is recorded even if the system restarts.

**3) Billing & Payment Module**

The data structures used are `rate_rules` and `billing`. `rate_rules` is a dictionary of dictionaries keyed by `ruleID`, stored separately from the algorithm, so management can edit parking rates at any time without a software change. `billing` is a dictionary of dictionaries keyed by `transactionID`, where each payment attempt is recorded as a new entry. The module also reads the vehicle's `vehicleID` and `entryTime` from the Vehicle Capture module's active hash map.

**4) Barrier Control Module**

The data structure used is a variable (`paymentStatus`) — a single flag, so no collection is needed.

**5) Exception Handling Module**

The data structure used is `exception_log`, a list. Each exception (for example, a duplicate number plate at entry or a missing vehicle record at exit) is appended to the end of the list with its time, type, number plate and resolution. A list is appropriate because exceptions are only ever added in time order and reviewed in that same order, so no lookup by key is needed. The module also reads the existing structures (the active hash map, `vehicle_capture` and `billing`) when investigating an exception.

**6) Administrative Reporting Module**

No new data structure is required. The module reads the existing `vehicle_capture`, `billing` and `exception_log` records to produce reports for monitoring and reconciliation.

---

## Dynamic Database Design

**Note on implementation approach:** Per the lecturer's guidance to implement the database using data structures first before considering a full database engine, this design is implemented as nested dictionaries (dictionary of dictionaries) in Python, rather than as SQL tables. The design logic (fields, keys, relationships) remains the same as a formal database design would require — only the storage mechanism differs.

The active hash map is a fast in-memory index of vehicles currently inside, pointing to their `vehicle_capture` records by `vehicleID`. If the system restarts, it can be rebuilt from `vehicle_capture` records whose `exitTime` is still `None`.

**Active hash map structure:** `numberPlate` → `{vehicleID, entryTime, slotTaken}`

```python
"KDA 123X" → {"vehicleID": "VC007", "entryTime": "2026-09-20 10:00", "slotTaken": "A03"}
```

### Table 1: vehicle_capture

Represents one specific parking visit. Keyed by `vehicleID` (a surrogate key, e.g. VC001), rather than `numberPlate`, because the same vehicle can visit the parking lot multiple times across different days — `numberPlate` alone cannot reliably identify one unique visit.

**Fields:**

- `vehicleID` (primary key) — uniquely identifies one visit
- `numberPlate` — the vehicle's registration number
- `entryTime` — captured automatically on arrival, including the date
- `exitTime` — recorded with its date once the vehicle is authorized to leave (empty while the vehicle is still parked)
- `slotTaken` — the specific slot assigned (e.g. D47)

**Justification example:** `slotTaken` is retained permanently (not discarded after the vehicle leaves) because it supports real-world scenarios such as disputes — for instance, if a driver later reports having dropped their keys while boarding, an attendant can look up which specific slot they parked in to narrow down the search.

**Implemented as:**

```python
vehicle_capture = {
    "VC001": {
        "numberPlate": "KDA 123X",
        "entryTime": "2026-09-20 14:00",
        "exitTime": None,
        "slotTaken": "D47"
    }
}
```

### Table 2: billing

Represents one payment attempt tied to a specific visit. Keyed by `transactionID` (e.g. TXN001), separate from `vehicleID`, because a single visit can generate multiple billing attempts (e.g. a failed M-Pesa payment followed by a retry) — this makes the relationship between `vehicle_capture` and `billing` one-to-many, not one-to-one.

**Fields:**

- `transactionID` (primary key) — uniquely identifies one payment attempt
- `vehicleID` (foreign key → `vehicle_capture`) — links the transaction to its visit
- `feeAmount` — the calculated fee for that visit
- `paymentStatus` — PENDING / VERIFIED / FAILED, permanently recorded to support dispute resolution (e.g. "I paid but the barrier didn't open")
- `payment_method` — e.g. M-Pesa, Card, Cash
- `payment_reference` — the payment confirmation code from the provider (e.g. M-Pesa code QCH7588966); left empty for cash payments since not all payments generate one
- `created_at` — the date and time of that specific payment attempt

**Justification example:** if a driver's first M-Pesa payment times out and they retry a minute later, the system creates a second `billing` row (new `transactionID`) rather than overwriting the first, preserving a complete, honest history of what happened — both attempts remain linked to the same `vehicleID`.

**Implemented as:**

```python
billing = {
    "TXN001": {
        "vehicleID": "VC001",
        "feeAmount": 50,
        "paymentStatus": "VERIFIED",
        "payment_method": "M-Pesa",
        "payment_reference": "QCH7588966",
        "created_at": "2026-09-20 15:30"
    }
}
```

> **Note:** The `billing` and `vehicle_capture` records support administrative reporting, since management can review all transactions and visits for reconciliation.

### Table 3: rate_rules

Represents the parking fee structure as configuration data, kept separate from the Billing algorithm's logic. This satisfies the requirement that management should be able to change parking rates at any time without requiring a software/code change — updating a rate becomes a matter of editing this data, not the algorithm itself.

Unlike `vehicle_capture` and `billing`, which store per-visit transaction records, `rate_rules` stores a small, fixed set of business rules that rarely change but must remain easily editable by management.

**Fields:**

- `ruleID` (primary key) — uniquely identifies one rate bracket
- `minHours` — lower bound of the duration range
- `maxHours` — upper bound of the duration range
- `fee` — the amount charged (Ksh) for durations falling within this range

**Implemented as:**

```python
rate_rules = {
    "RATE001": {"minHours": 0, "maxHours": 0.5, "fee": 0},
    "RATE002": {"minHours": 0.5, "maxHours": 2, "fee": 50},
    "RATE003": {"minHours": 2, "maxHours": 4, "fee": 100},
    "RATE004": {"minHours": 4, "maxHours": 6, "fee": 300},
    "RATE005": {"minHours": 6, "maxHours": 9999, "fee": 500},  # 9999 means no upper limit
}
```

**Billing & Payment Module's use of rate_rules:** instead of hardcoded if/elseif thresholds, the Billing algorithm loops through each rule in `rate_rules`, checking whether `durationHours` falls between that rule's `minHours` and `maxHours`, and sets `feeAmount` to the matching rule's `fee`. This decouples the rate values from the algorithm's logic entirely. In the implementation, `rate_rules` will be stored in an editable source (such as a file or an admin page) rather than written directly in the program code, so management can update it without a software change.

### Table 4: parking_slots

Represents the current status of every parking slot. Unlike `vehicle_capture` and `billing`, which grow as new records are added, `parking_slots` holds a fixed set of slots whose status changes as vehicles enter and leave. It is the source for the live availability display.

**Fields:**

- `slotID` (key) — uniquely identifies one parking slot (e.g. A01)
- `status` — AVAILABLE or OCCUPIED

**Implemented as:**

```python
parking_slots = {"A01": "OCCUPIED", "A02": "AVAILABLE", "A03": "AVAILABLE"}
```

### Table 5: exception_log

Records every exception the system detects, providing an audit trail of problems and how they were resolved. It is implemented as a list rather than a dictionary because entries are only appended in time order and are never looked up by a key.

**Fields:**

- `created_at` — when the exception occurred
- `type` — e.g. DUPLICATE_PLATE, VEHICLE_NOT_FOUND, PAYMENT_FAILED
- `numberPlate` — the vehicle involved
- `resolution` — how the attendant resolved it (empty until resolved)

**Implemented as:**

```python
exception_log = [
    {"created_at": "2026-09-20 14:05", "type": "DUPLICATE_PLATE", "numberPlate": "KDA 123X", "resolution": "Old visit closed; slot A03 was empty"},
    {"created_at": "2026-09-20 15:10", "type": "VEHICLE_NOT_FOUND", "numberPlate": "KBZ 456Y", "resolution": None}
]
```

**Why this qualifies as "dynamic":** new records are continuously added as the system operates — a new `vehicle_capture` entry every time a vehicle enters, and a new `billing` entry every time a payment attempt is made — rather than working with a fixed, unchanging dataset.

**Searching by numberPlate:** since `vehicle_capture` is keyed by `vehicleID`, looking up a record by `numberPlate` (e.g. for attendant disputes) requires checking each record one at a time until a match is found — this is a **linear search**, as opposed to the near-instant lookup available when searching directly by `vehicleID`. Binary search was considered but ruled out, since it requires sorted data, and these records are not sorted by `numberPlate`. In a full database implementation, this limitation would be addressed by adding an **index** on `numberPlate` — a database feature that creates a fast-access shortcut on a non-primary-key column, conceptually similar to a hash table, so lookups don't require scanning every row. Vehicles currently inside are unaffected, since the active hash map is keyed by `numberPlate` and finds them instantly; this linear search applies only to completed visits in `vehicle_capture`.

**Data type note:** `feeAmount` should be stored using a currency-safe numeric type (e.g. `DECIMAL` in a formal database) rather than a basic float, to avoid floating-point rounding errors — even though current fee brackets (0, 50, 100, 300, 500) are whole numbers, this protects against future changes such as percentage-based discounts.

---

## Requirement-to-Design Mapping

| System requirement | Module | Algorithm / process | Data structure |
|---|---|---|---|
| Display available parking slots | Slot Management | Calculate Available Slots | `parking_slots` dictionary |
| Allocate an available slot | Slot Management | Allocate Parking Slot | `parking_slots` dictionary |
| Release a slot after vehicle leaves | Slot Management | Release Parking Slot | `parking_slots` dictionary |
| Record vehicle arrival | Vehicle Capture | Vehicle Capture — Entry | Active hash map + `vehicle_capture` |
| Find vehicle at exit | Vehicle Capture | Vehicle Capture — Exit | Active hash map |
| Calculate parking duration | Billing & Payment | Duration calculation | `entryTime` + `currentTime` |
| Calculate parking fee | Billing & Payment | `rate_rules` matching | `rate_rules` dictionary |
| Let management change parking rates | Billing & Payment | `rate_rules` matching | `rate_rules` dictionary |
| Accept M-Pesa, card or cash | Billing & Payment | Payment processing | `billing` dictionary |
| Record payment attempts | Billing & Payment | Payment transaction process | `billing`, keyed by `transactionID` |
| Open barrier after verified payment | Barrier Control | Barrier Control algorithm | `paymentStatus` from `billing` |
| Handle unavailable slots, missing records and failed payments | Exception Handling | Exception Handling algorithm | `exception_log` list + existing data structures |
| Provide management records/reconciliation | Administrative Reporting | Administrative Reporting algorithm | `vehicle_capture` + `billing` + `exception_log` |
