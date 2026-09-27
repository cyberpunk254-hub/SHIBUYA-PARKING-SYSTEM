# SHIBUYA-PARKING-SYSTEM

A modern parking system. Designed by Allan Gachuki.

| | |
|---|---|
| **Name** | Allan Gachuki Gichuru |
| **Registration Number** | CIT-227-058/2025 |
| **Programme** | Software Engineering, Multimedia University of Kenya |
| **Unit** | CCS 2124 Data Structures and Algorithms |
| **Lecturer** | Patrick Mokodir |
| **Assignment** | Development of a Modern Parking System |

---

## Overview

Shibuya Parking System automates a car park in Kenya. Drivers see how many slots are free before they enter, are given a slot when they check in, and pay on the way out. The system works out how long each vehicle stayed and what it owes, and the exit barrier only opens once payment is confirmed.

It is a web application written in **Python** with **FastAPI**, following the modules, algorithms and data structures in the design document: [`PARKING_SYSTEM_DESIGN.md`](PARKING_SYSTEM_DESIGN.md).

## Features

- **Live slot display.** A board shows free and taken slots and updates on its own every few seconds as vehicles come and go.
- **Check in.** Enter a number plate and the system assigns the first free slot and records the arrival time.
- **Pay and exit.** Look up a vehicle, see the time parked and the fee, pay by M-Pesa, card or cash, and watch the barrier lift once payment is confirmed.
- **Real M-Pesa payments (sandbox).** M-Pesa payments send an STK Push prompt to the driver's phone through Safaricom's Daraja API.
- **Editable parking rates.** Management changes fees from the Admin page, with no code changes.
- **Admin dashboard.** Completed visits, every payment attempt, total collected and the exception log, for monitoring and reconciliation.
- **Exception handling.** Parking full, duplicate number plates, vehicles not found at exit and failed payments are all handled and logged.

## Use cases

![Use case diagram](docs/use-case-diagram.svg)

| Actor | Use case | Notes |
|---|---|---|
| Driver | View available slots | Live board on the homepage and at the gate. |
| Driver | Check in vehicle | Includes *Allocate parking slot*. Refused if the car park is full or the plate is already inside. |
| Driver | Pay and exit | Includes *Look up vehicle record*, *Calculate parking fee*, *Pay parking fee* and *Open exit barrier*. |
| Driver | Pay with M-Pesa | Extends *Pay parking fee*. Uses the M-Pesa (Daraja) system actor. |
| Driver | Retry failed payment | Extends *Pay parking fee*. Every retry is a new transaction. |
| Attendant | Search vehicle by slot | Extends *Look up vehicle record* when a plate can't be matched at exit. |
| Attendant | Resolve exception | Handles duplicate plates, missing records and repeated payment failures. |
| Administrator | Change parking rates | Edits fee amounts; the time brackets stay fixed. |
| Administrator | View reports | Visits, payment attempts, total collected and exceptions. |

A PNG copy of the diagram is in [`docs/use-case-diagram.png`](docs/use-case-diagram.png).

## Parking fees

| Time parked | Fee |
|---|---|
| Up to 30 minutes | Free |
| Up to 2 hours | Ksh 50 |
| Up to 4 hours | Ksh 100 |
| Up to 6 hours | Ksh 300 |
| Over 6 hours | Ksh 500 |

Exactly 2 hours pays Ksh 50, not Ksh 100: each bracket includes its upper limit. These are the default fees; management can change them from the Admin page.

## Modules

Each module from the design document is its own Python file.

| Module | File | Responsibility |
|---|---|---|
| Slot Management | `slot_management.py` | Counts free slots, allocates the first free slot, releases slots after exit. |
| Vehicle Capture | `vehicle_capture.py` | Records entries, finds vehicles at exit (by plate or by slot), completes exits. |
| Billing & Payment | `billing.py` | Duration and fee calculation, payment transactions, editable rates. |
| M-Pesa integration | `mpesa.py` | Daraja access token, STK Push and payment status queries. |
| Barrier Control | `main.py` (`/barrier/exit`) | Opens the exit barrier only when payment is VERIFIED. |
| Exception Handling | `exception_handling.py` | Records every exception in an audit log. |
| Administrative Reporting | `reporting.py` | Builds the management report from existing records. |
| Shared data | `storage.py` | All data structures in one place, so modules never import each other's data in a circle. |

## Data structures

As the lecturer asked, the database is implemented with Python data structures rather than a database engine.

| Structure | Type | Key | Why |
|---|---|---|---|
| `parking_slots` | Dictionary | Slot ID (A01–A50) | Direct access to any slot's status. |
| `active_vehicles` | Hash map (dictionary) | Number plate | Near-instant lookup of a vehicle at the exit barrier. |
| `vehicle_capture` | Dictionary of dictionaries | Visit ID (VC001…) | Permanent record of every visit. The same car can visit many times. |
| `billing` | Dictionary of dictionaries | Transaction ID (TXN001…) | Every payment attempt, so one visit can have several attempts (one-to-many). |
| `rate_rules` | Dictionary of dictionaries | Rule ID (RATE001…) | Fee brackets kept as data, separate from the billing algorithm. |
| `exception_log` | List | — | Exceptions are only appended in time order and read in that order. |

Searching completed visits by number plate is a linear search, because `vehicle_capture` is keyed by visit ID. Vehicles still inside are found instantly through `active_vehicles`. See the design document for the full reasoning.

## Tech stack

- **Python 3.13+** (developed on 3.14)
- **FastAPI** and **Uvicorn** for the web server
- **Jinja2** for HTML templates
- **Motion** (the plain-JavaScript version of Framer Motion) for animations and scroll effects, plus the browser's View Transitions for page transitions
- **httpx** and **python-dotenv** for the M-Pesa Daraja integration

## Project structure

```
SHIBUYA-PARKING-SYSTEM/
├── main.py                  # FastAPI app: pages and API routes
├── storage.py               # Shared data structures (the "database")
├── slot_management.py       # Slot Management Module
├── vehicle_capture.py       # Vehicle Capture Module
├── billing.py               # Billing & Payment Module
├── mpesa.py                 # M-Pesa Daraja integration
├── exception_handling.py    # Exception Handling Module
├── reporting.py             # Administrative Reporting Module
├── templates/
│   ├── base.html            # Shared layout, header, rate ticker
│   ├── display.html         # Homepage and live slot board
│   ├── entry.html           # Check in
│   ├── exit.html            # Pay and exit, barrier
│   └── admin.html           # Admin dashboard
├── static/
│   ├── style.css
│   ├── favicon.svg
│   └── images/
├── docs/
│   ├── use-case-diagram.svg
│   └── use-case-diagram.png
├── PARKING_SYSTEM_DESIGN.md # Task One: modules, algorithms, data structures, database
├── requirements.txt
├── .env.example             # Settings template (copy to .env)
└── .gitignore
```

## Running the system

**1. Clone the repository**

```
git clone https://github.com/cyberpunk254-hub/SHIBUYA-PARKING-SYSTEM.git
cd SHIBUYA-PARKING-SYSTEM
```

**2. Create and activate a virtual environment**

```
python -m venv venv
```

Windows:
```
.\venv\Scripts\activate
```

macOS / Linux:
```
source venv/bin/activate
```

**3. Install the packages**

```
pip install -r requirements.txt
```

**4. Create your settings file**

Windows:
```
copy .env.example .env
```

macOS / Linux:
```
cp .env.example .env
```

The default, `PAYMENT_MODE=simulate`, runs everything without an M-Pesa account. See [M-Pesa payments](#m-pesa-payments) to switch on real sandbox payments.

**5. Start the server**

```
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000**.

## Pages

| Page | Address | Used by |
|---|---|---|
| Live slots | `/` | Drivers, gate display |
| Check in | `/entry-page` | Entry gate |
| Pay and exit | `/exit-page` | Exit barrier |
| Admin | `/admin` | Management |
| API documentation | `/docs` | Testing every route directly |

## M-Pesa payments

Payment mode is set by `PAYMENT_MODE` in `.env`:

- **`simulate`** (default): payments go PENDING, and two clearly labelled demo buttons stand in for the payment provider's confirmation or failure.
- **`daraja`**: M-Pesa payments send a real STK Push prompt to the driver's phone through the Safaricom Daraja **sandbox**. No real money is involved. Card and cash payments still use the demo buttons.

To use Daraja:

1. Create an account at [developer.safaricom.co.ke](https://developer.safaricom.co.ke) and create an app with the M-Pesa Express (Lipa Na M-Pesa) sandbox product.
2. Copy the app's **Consumer Key** and **Consumer Secret** into `.env`.
3. Copy the sandbox **passkey** from the M-Pesa Express simulator into `MPESA_PASSKEY`. The sandbox shortcode is `174379`.
4. Set `PAYMENT_MODE=daraja` and restart the server.

`.env` is listed in `.gitignore` and must never be committed, because it contains the Daraja secret.

## How to test it

1. **Check in** a vehicle, for example `KDA 123X`. It's assigned slot A01, and the live board shows the car within 5 seconds.
2. Check in **the same plate again**. It's refused as a duplicate and logged as an exception.
3. On **Pay and exit**, enter the plate. A stay under 30 minutes is free, so the barrier lifts straight away.
4. To test payments, set "Up to 30 minutes" to a small fee on the **Admin** page, then pay again:
   - choose a method, pay, then press **Simulate payment failed**, then **Try again** and **Simulate payment confirmed**;
   - or, in `daraja` mode, choose M-Pesa, enter a Safaricom number and enter your PIN on the phone.
5. Open **Admin**: both attempts appear under the same visit, one FAILED and one VERIFIED, with the failure in the exceptions tab.
6. Set the first fee back to 0.

## Design decisions

- **Data is kept in memory.** Following the lecturer's instruction to implement the database with data structures first, visits, payments and exceptions reset when the server restarts. Only the fee amounts are saved, to `rates.json`, so management's rate changes survive a restart.
- **Rates are data, not code.** The billing algorithm never contains a fee amount; it matches the duration against `rate_rules`. The rate ticker and admin page are generated from the same data, so they always show the current prices.
- **Payment statuses are PENDING, VERIFIED and FAILED.** A driver can't start a new payment while one is pending, which prevents double payments. A payment with no confirmation within 2 minutes becomes FAILED so the driver can retry.
- **Every retry is a new transaction**, so the payment history stays complete for auditing.
- **Free stays still create a record.** A stay under 30 minutes records a Ksh 0 transaction with method "Free", so every exit has a payment record.
- **M-Pesa reference.** The integration checks payment results by querying Safaricom, which works without a public server address. The query result doesn't include the M-Pesa receipt code, so M-Pesa payments store Safaricom's **CheckoutRequestID** as their reference instead.
- **The slot is released only after the vehicle leaves**, so a slot is never shown as free while a car is still in it.
- **User input is escaped** before it's shown on any page, which protects against cross-site scripting (XSS) through the number plate box.
- **Accessibility.** Pages respect the "reduce motion" system setting, tabs support keyboard arrow keys, and decorative images are hidden from screen readers.

## Future improvements

- A persistent database (for example SQLite or PostgreSQL), with an index on number plates for fast lookups of past visits.
- The M-Pesa callback URL on a deployed server, to store the M-Pesa receipt code and confirm payments faster.
- Real card payments through a payment provider.
- Login for the Admin page.
- Compressing all photos before deployment (currently only the hero image is compressed).
- Automatic number plate recognition at the gates.

## Credits

- Photographs: free-licence stock photos.
- Animations: [Motion](https://motion.dev).
- Payments: [Safaricom Daraja API](https://developer.safaricom.co.ke) (sandbox).
