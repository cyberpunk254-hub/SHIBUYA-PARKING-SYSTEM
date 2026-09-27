# mpesa.py — M-Pesa Daraja integration (sandbox)
# Sends STK Push prompts and checks their result for the Billing &
# Payment Module. Credentials are read from .env, never written here.

import base64
import os
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()   # reads the .env file into environment variables

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "simulate")
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
PASSKEY = os.getenv("MPESA_PASSKEY", "")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://example.com/mpesa/callback")

BASE_URL = "https://sandbox.safaricom.co.ke"

# The access token lasts about an hour, so it's reused until shortly
# before it expires instead of requesting a new one every time.
_token = {"value": None, "expires_at": 0}


def daraja_enabled():
    """True when .env asks for real M-Pesa and the credentials are present."""
    return PAYMENT_MODE == "daraja" and CONSUMER_KEY and CONSUMER_SECRET and PASSKEY


def get_access_token():
    """Swap the consumer key and secret for a temporary access token."""
    if _token["value"] and time.time() < _token["expires_at"]:
        return _token["value"]

    response = httpx.get(
        BASE_URL + "/oauth/v1/generate",
        params={"grant_type": "client_credentials"},
        auth=(CONSUMER_KEY, CONSUMER_SECRET),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    _token["value"] = data["access_token"]
    # Refresh a minute early, so a token never expires mid-request.
    _token["expires_at"] = time.time() + int(data.get("expires_in", 3599)) - 60
    return _token["value"]


def _timestamp():
    """Daraja's required time format: YYYYMMDDHHMMSS."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _password(timestamp):
    """Base64(Shortcode + Passkey + Timestamp), as the portal describes."""
    raw = SHORTCODE + PASSKEY + timestamp
    return base64.b64encode(raw.encode()).decode()


def normalize_phone(phone):
    """Turn 0712345678, +254712345678 or 712345678 into 254712345678.

    Returns None if it isn't a valid Kenyan mobile number.
    """
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith("254") and len(digits) == 12:
        local = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        local = digits[1:]
    elif len(digits) == 9:
        local = digits
    else:
        return None

    if local[0] not in ("7", "1"):   # Kenyan mobile numbers start 07 or 01
        return None
    return "254" + local


def stk_push(phone, amount, reference, description="Parking fee"):
    """Show the M-Pesa PIN prompt on the driver's phone.

    Returns {"ok": True, "checkoutRequestID": ...} if Safaricom accepted
    the request, or {"ok": False, "message": ...} if it didn't.
    """
    timestamp = _timestamp()
    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": _password(timestamp),
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference[:12],     # Daraja limit: 12 characters
        "TransactionDesc": description[:13],    # Daraja limit: 13 characters
    }

    try:
        response = httpx.post(
            BASE_URL + "/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": "Bearer " + get_access_token()},
            timeout=30,
        )
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        return {"ok": False, "message": "Couldn't reach M-Pesa: " + str(error)}

    if str(data.get("ResponseCode")) == "0":
        return {"ok": True, "checkoutRequestID": data["CheckoutRequestID"]}

    return {"ok": False, "message": data.get("errorMessage") or data.get("ResponseDescription") or "M-Pesa refused the request."}


def stk_query(checkout_request_id):
    """Ask Safaricom whether an STK Push has been paid.

    Returns one of your design's statuses: "VERIFIED", "FAILED" or
    "PENDING", plus Safaricom's explanation.
    """
    timestamp = _timestamp()
    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": _password(timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    try:
        response = httpx.post(
            BASE_URL + "/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={"Authorization": "Bearer " + get_access_token()},
            timeout=30,
        )
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        # Can't tell yet: keep waiting rather than failing the driver,
        # but keep the reason so it shows up while testing.
        return {"status": "PENDING", "message": "Still checking with M-Pesa (" + str(error) + ")."}

    # While the driver hasn't answered, Safaricom may reply with an error
    # saying the transaction is still being processed.
    if "errorCode" in data:
        return {"status": "PENDING", "message": data.get("errorMessage", "Still processing.")}

    result_code = str(data.get("ResultCode"))
    description = data.get("ResultDesc", "")

    if result_code == "0":
        return {"status": "VERIFIED", "message": description or "Paid."}

    # Safaricom sometimes reports "still under processing" with a result
    # code (4999) instead of an error. That isn't a failure: the driver
    # may still be entering their PIN, so keep waiting.
    if result_code == "4999" or "processing" in description.lower():
        return {"status": "PENDING", "message": description or "Still processing."}

    # Anything else is a final failure: cancelled (1032), timed out
    # (1037), insufficient funds (1), wrong PIN (2001) and so on.
    return {"status": "FAILED", "message": description or "Payment was not completed."}