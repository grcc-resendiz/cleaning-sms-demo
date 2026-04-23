import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from pydantic import BaseModel
from twilio.rest import Client

from ai import extract_intent
from booking import (
    cancel_reservation,
    check_availability,
    make_reservation,
    reschedule_reservation,
    save_state,
)
from db import init_db
from seed import seed_next_7_days

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleaning-sms-demo")

app = FastAPI(title="Cleaning SMS Demo")


class SMSPayload(BaseModel):
    From: str
    Body: str


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() == "true"


def send_sms(to_phone: str, message: str) -> dict[str, Any]:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone = os.getenv("TWILIO_PHONE_NUMBER")

    logger.info("Outgoing message to=%s body=%s", to_phone, message)

    if is_demo_mode() or not (sid and token and from_phone):
        mode = "demo" if is_demo_mode() else "missing_twilio_credentials"
        logger.info("Demo transport active (%s). Message logged only; no SMS sent.", mode)
        return {"transport": "demo", "sent": False, "mode": mode}

    client = Client(sid, token)
    client.messages.create(from_=from_phone, to=to_phone, body=message)
    return {"transport": "twilio", "sent": True, "mode": "live_twilio"}


def handle_sms_logic(phone: str, body: str) -> dict[str, Any]:
    logger.info("Inbound SMS from=%s body=%s", phone, body)

    try:
        parsed = extract_intent(body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Intent extraction failed: {exc}") from exc

    logger.info(
        "Extracted intent intent=%s date=%s window=%s service=%s unclear=%s",
        parsed.intent,
        parsed.requested_date,
        parsed.requested_time_window,
        parsed.service_type,
        parsed.is_unclear,
    )

    if parsed.is_unclear or not parsed.intent:
        reply = "Sorry—reply with: availability, book, reschedule, or cancel."
        logger.info("Selected action=clarify")
        delivery = send_sms(phone, reply)
        return {"ok": True, "intent": None, "reply": reply, "delivery": delivery}

    save_state(
        phone=phone,
        intent=parsed.intent,
        requested_date=parsed.requested_date,
        requested_time_window=parsed.requested_time_window,
        service_type=parsed.service_type,
    )

    if parsed.intent == "check_availability":
        logger.info("Selected action=check_availability")
        slots = check_availability(parsed.requested_date)
        if not slots:
            reply = "No open slots right now."
        else:
            formatted = ", ".join([f"{s['appointment_date']} {s['time_window']}" for s in slots])
            reply = f"Open: {formatted}."
    elif parsed.intent == "make_reservation":
        logger.info("Selected action=make_reservation")
        slot = make_reservation(phone, parsed.requested_date, parsed.requested_time_window, parsed.service_type)
        reply = f"Booked: {slot['appointment_date']} {slot['time_window']}." if slot else "No matching slot. Try another."
    elif parsed.intent == "reschedule_reservation":
        logger.info("Selected action=reschedule_reservation")
        old_slot, new_slot = reschedule_reservation(phone, parsed.requested_date, parsed.requested_time_window)
        if not old_slot:
            reply = "No active booking to move."
        elif not new_slot:
            reply = "No new slot found."
        else:
            reply = f"Moved: {new_slot['appointment_date']} {new_slot['time_window']}."
    elif parsed.intent == "cancel_reservation":
        logger.info("Selected action=cancel_reservation")
        old = cancel_reservation(phone)
        reply = f"Canceled: {old['appointment_date']} {old['time_window']}." if old else "No booking found to cancel."
    else:
        logger.info("Selected action=unknown")
        reply = "Reply: availability, book, reschedule, or cancel."

    delivery = send_sms(phone, reply)
    return {"ok": True, "intent": parsed.intent, "reply": reply, "delivery": delivery}


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    seed_next_7_days()


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": is_demo_mode()}


@app.post("/sms")
async def sms_webhook(request: Request, payload: SMSPayload | None = Body(default=None)):
    # Supports Swagger JSON testing and Twilio form posts.
    if payload is not None:
        return handle_sms_logic(phone=payload.From, body=payload.Body)

    form = await request.form()
    phone = form.get("From")
    body = form.get("Body")
    if not phone or not body:
        raise HTTPException(status_code=400, detail="From and Body are required")

    return handle_sms_logic(phone=phone, body=body)


@app.get("/demo")
def demo(phone: str, message: str):
    return handle_sms_logic(phone=phone, body=message)
