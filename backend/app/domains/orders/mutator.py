"""Pure transformations for orders. No I/O, no clocks, no randomness."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domains.orders.schemas import OrderCreate, OrderStatus

OUTCOME_TO_STATUS: dict[str, OrderStatus] = {
    "confirmed": OrderStatus.ship_approved,
    "address_correction": OrderStatus.address_correction_requested,
    "reschedule": OrderStatus.reschedule_requested,
    "cancel_requested": OrderStatus.cancelled,
    "needs_followup": OrderStatus.needs_followup,
    "unreachable": OrderStatus.unreachable,
}


def new_order_record(payload: OrderCreate, *, now: datetime, order_id: str | None = None) -> dict[str, Any]:
    """Create a fresh order record from input + clock + id (all injected)."""
    return {
        "id": order_id or str(uuid4()),
        "customer_name": payload.customer_name,
        "phone": payload.phone,
        "product_summary": payload.product_summary,
        "order_value": payload.order_value,
        "address_short": payload.address_short,
        "scheduled_slot": payload.scheduled_slot,
        "brand_name": payload.brand_name,
        "status": OrderStatus.pending_verification,
        "last_call_id": None,
        "last_call_outcome": None,
        "captured_address_landmark": None,
        "captured_new_slot": None,
        "captured_cancel_reason": None,
        "captured_followup_question": None,
        "last_transcript_url": None,
        "last_recording_url": None,
        "last_summary": None,
        "created_at": now,
        "updated_at": now,
    }


def mark_verifying(order: dict[str, Any], *, call_id: str, now: datetime) -> dict[str, Any]:
    """Order entered the in-flight verification state."""
    return {
        **order,
        "status": OrderStatus.verifying,
        "last_call_id": call_id,
        "updated_at": now,
    }


def mark_call_failed(order: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """Bolna API rejected the call request before placing it."""
    return {
        **order,
        "status": OrderStatus.call_failed,
        "updated_at": now,
    }


def outcome_to_status(outcome_tag: str | None) -> OrderStatus:
    """Map LLM-extracted outcome tag to canonical order status. Falls back safely."""
    if not outcome_tag:
        return OrderStatus.needs_followup
    normalised = outcome_tag.strip().lower()
    return OUTCOME_TO_STATUS.get(normalised, OrderStatus.needs_followup)


def apply_call_outcome(
    order: dict[str, Any],
    *,
    outcome_tag: str | None,
    extractions: dict[str, Any],
    transcript_url: str | None,
    recording_url: str | None,
    summary: str | None,
    now: datetime,
) -> dict[str, Any]:
    """Pure: take an order + post-call signals, return the new order state."""
    return {
        **order,
        "status": outcome_to_status(outcome_tag),
        "last_call_outcome": outcome_tag,
        "captured_address_landmark": extractions.get("new_address_landmark"),
        "captured_new_slot": extractions.get("new_slot"),
        "captured_cancel_reason": extractions.get("cancel_reason"),
        "captured_followup_question": extractions.get("followup_question"),
        "last_transcript_url": transcript_url,
        "last_recording_url": recording_url,
        "last_summary": summary,
        "updated_at": now,
    }
