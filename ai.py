import json
import os
from dataclasses import dataclass

from openai import OpenAI

ALLOWED_INTENTS = {
    "check_availability",
    "make_reservation",
    "reschedule_reservation",
    "cancel_reservation",
}


@dataclass
class IntentPayload:
    intent: str | None
    requested_date: str | None = None
    requested_time_window: str | None = None
    service_type: str | None = None
    is_unclear: bool = False


def extract_intent(message: str) -> IntentPayload:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = OpenAI(api_key=api_key)
    prompt = (
        "Extract a cleaning booking intent from this SMS and return JSON only. "
        "intent must be one of: check_availability, make_reservation, "
        "reschedule_reservation, cancel_reservation. "
        "Use null for unknown values."
    )

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "intent_payload",
                "schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": ["string", "null"],
                            "enum": sorted(list(ALLOWED_INTENTS)) + [None],
                        },
                        "requested_date": {"type": ["string", "null"]},
                        "requested_time_window": {"type": ["string", "null"]},
                        "service_type": {"type": ["string", "null"]},
                    },
                    "required": [
                        "intent",
                        "requested_date",
                        "requested_time_window",
                        "service_type",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    payload = json.loads(response.output_text)
    intent = payload.get("intent")
    if intent not in ALLOWED_INTENTS:
        return IntentPayload(
            intent=None,
            requested_date=payload.get("requested_date"),
            requested_time_window=payload.get("requested_time_window"),
            service_type=payload.get("service_type"),
            is_unclear=True,
        )

    return IntentPayload(
        intent=intent,
        requested_date=payload.get("requested_date"),
        requested_time_window=payload.get("requested_time_window"),
        service_type=payload.get("service_type"),
        is_unclear=False,
    )
