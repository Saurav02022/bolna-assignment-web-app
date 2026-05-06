"""Pure transforms for call records and webhook payload normalisation."""

import re
from datetime import datetime
from typing import Any

from app.domains.calls.schemas import BolnaWebhookPayload, CallStatus

ALLOWED_OUTCOME_TAGS = {
    "confirmed",
    "address_correction",
    "reschedule",
    "cancel_requested",
    "needs_followup",
    "unreachable",
}


def new_call_record(
    *,
    call_id: str,
    order_id: str,
    bolna_status: str | None,
    now: datetime,
) -> dict[str, Any]:
    """Initial call record stored when we kick off a call."""
    return {
        "id": call_id,
        "order_id": order_id,
        "status": _coerce_status(bolna_status, default=CallStatus.queued),
        "triggered_at": now,
        "completed_at": None,
        "outcome_tag": None,
        "extractions": {},
        "transcript_url": None,
        "recording_url": None,
        "summary": None,
        "duration_sec": None,
        "language_detected": None,
        "sentiment": None,
    }


def coerce_status(value: str | None, *, default: CallStatus) -> CallStatus:
    if not value:
        return default
    normalised = value.strip().lower().replace("-", "_")
    try:
        return CallStatus(normalised)
    except ValueError:
        return default


_coerce_status = coerce_status


def normalise_outcome_tag(raw: Any) -> str | None:
    """Bolna may send the tag wrapped in different keys; we accept various."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text or text in {"null", "none"}:
        return None
    return text if text in ALLOWED_OUTCOME_TAGS else "needs_followup"


TERMINAL_STATUSES = {
    "completed",
    "ended",
    "failed",
    "error",
    "no-answer",
    "call-disconnected",
    "disconnected",
    "hangup",
    "voicemail",
}


def is_terminal_status(status: str | None) -> bool:
    """Bolna fires intermediate webhooks (initiated/ringing/in-progress).

    We only apply business logic on the final webhook for an execution.
    """
    if not status:
        return False
    return status.strip().lower().replace("_", "-") in TERMINAL_STATUSES


def extract_call_id(payload: BolnaWebhookPayload) -> str | None:
    """Bolna sends the identifier as `id` (verified live); accept aliases too."""
    return payload.id or payload.call_id or payload.execution_id


def extract_order_id(payload: BolnaWebhookPayload) -> str | None:
    """The user_data we sent is echoed under one of these containers."""
    sources: list[dict[str, Any]] = [
        payload.user_data or {},
        payload.metadata or {},
        payload.context_details or {},
        payload.agent_context_details or {},
        payload.recipient_data or {},
    ]
    for src in sources:
        candidate = src.get("order_id") if isinstance(src, dict) else None
        if candidate:
            return str(candidate)
        nested = src.get("recipient_data") if isinstance(src, dict) else None
        if isinstance(nested, dict) and nested.get("order_id"):
            return str(nested["order_id"])
    return None


def _coalesce_extractions(source: Any) -> dict[str, Any]:
    """Bolna may send extractions as a dict, or as a list of {name, value}."""
    if isinstance(source, dict):
        return dict(source)
    if isinstance(source, list):
        flat: dict[str, Any] = {}
        for entry in source:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("key")
            value = entry.get("value") if "value" in entry else entry.get("answer")
            if name:
                flat[str(name)] = value
        return flat
    return {}


_OUTCOME_RE = re.compile(
    r"outcome[_ ]?tag\s*[:=]\s*([a-zA-Z_]+)",
    re.IGNORECASE,
)
_LANDMARK_RE = re.compile(
    r"new[_ ]?address[_ ]?landmark\s*[:=]\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SLOT_RE = re.compile(
    r"new[_ ]?slot\s*[:=]\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CANCEL_RE = re.compile(
    r"cancel[_ ]?reason\s*[:=]\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FOLLOWUP_RE = re.compile(
    r"followup[_ ]?question\s*[:=]\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_from_transcript(transcript: str) -> dict[str, Any]:
    """Parse outcome + capture fields the agent speaks at the end of the call.

    Bolna's `extracted_data` step does not always fire (paid pipeline, async).
    Our agent prompt instructs the LLM to emit `outcome_tag: <value>` and the
    other capture fields in the final assistant turn — we mine them as a
    deterministic fallback so the order can transition without human review.
    """
    extracted: dict[str, Any] = {}

    outcome_match = _OUTCOME_RE.search(transcript)
    if outcome_match:
        extracted["outcome_tag"] = outcome_match.group(1).strip().lower()

    for key, regex in (
        ("new_address_landmark", _LANDMARK_RE),
        ("new_slot", _SLOT_RE),
        ("cancel_reason", _CANCEL_RE),
        ("followup_question", _FOLLOWUP_RE),
    ):
        match = regex.search(transcript)
        if match:
            value = match.group(1).strip().strip(",.")
            if value and value.lower() not in {"null", "none", "n/a"}:
                extracted[key] = value

    return extracted


def extract_extractions(payload: BolnaWebhookPayload) -> dict[str, Any]:
    """Custom extractions live in `custom_extractions`; older payloads use `extracted_data`.

    When Bolna's extraction step is silent, fall back to mining the transcript
    (the agent speaks the outcome and capture fields per its system prompt).
    """
    candidates: list[Any] = [
        payload.custom_extractions,
        payload.extracted_data,
        payload.extracted,
        payload.extractions,
        payload.agent_extraction,
    ]
    for source in candidates:
        if source:
            data = _coalesce_extractions(source)
            if data:
                return data

    if isinstance(payload.transcript, str) and payload.transcript.strip():
        mined = _extract_from_transcript(payload.transcript)
        if mined:
            return mined

    return {}


def extract_transcript_url(payload: BolnaWebhookPayload) -> str | None:
    if payload.transcript_url:
        return payload.transcript_url
    if isinstance(payload.transcript, str):
        return payload.transcript
    return None


def apply_completion(
    call: dict[str, Any],
    *,
    payload: BolnaWebhookPayload,
    extractions: dict[str, Any],
    outcome_tag: str | None,
    now: datetime,
) -> dict[str, Any]:
    """Pure: merge the webhook signal onto the existing call record."""
    duration = payload.duration_sec or payload.duration or payload.conversation_duration
    recording = payload.recording_url
    if not recording and isinstance(payload.telephony_data, dict):
        recording = payload.telephony_data.get("recording_url")
    return {
        **call,
        "status": _coerce_status(payload.status, default=CallStatus.completed),
        "completed_at": now,
        "outcome_tag": outcome_tag,
        "extractions": extractions,
        "transcript_url": extract_transcript_url(payload),
        "recording_url": recording,
        "summary": payload.summary,
        "duration_sec": int(duration) if duration is not None else None,
        "language_detected": payload.language_detected or payload.language,
        "sentiment": payload.sentiment,
    }
