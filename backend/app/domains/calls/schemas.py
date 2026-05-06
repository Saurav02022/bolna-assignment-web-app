from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.orders.schemas import OrderResponse


class CallStatus(str, Enum):
    """Lifecycle of a single outbound call."""

    queued = "queued"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class CallRecord(BaseModel):
    """Internal snapshot of a call as we know it."""

    id: str
    order_id: str
    status: CallStatus
    triggered_at: datetime
    completed_at: datetime | None = None

    outcome_tag: str | None = None
    extractions: dict[str, Any] = Field(default_factory=dict)

    transcript_url: str | None = None
    recording_url: str | None = None
    summary: str | None = None
    duration_sec: int | None = None
    language_detected: str | None = None
    sentiment: str | None = None


class TriggerCallResponse(BaseModel):
    """Response from POST /orders/{id}/verify."""

    order: OrderResponse
    call_id: str
    bolna_status: str


class BolnaWebhookPayload(BaseModel):
    """Loose schema for Bolna's post-call webhook.

    Bolna's actual payload (verified live) puts the call identifier in `id`
    at the top level, the agent variables in `context_details`, and our
    custom extractions in `custom_extractions` (with `extracted_data` empty
    until the agent's own first-class extraction runs). We accept all common
    aliases so platform changes do not break us.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    execution_id: str | None = None
    call_id: str | None = None
    agent_id: str | None = None
    status: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    user_data: dict[str, Any] = Field(default_factory=dict)
    context_details: dict[str, Any] | None = None
    agent_context_details: dict[str, Any] | None = None
    recipient_data: dict[str, Any] | None = None

    transcript: Any | None = None
    transcript_url: str | None = None
    recording_url: str | None = None
    summary: str | None = None
    duration: float | int | None = None
    duration_sec: float | int | None = None
    conversation_duration: float | int | None = None
    language_detected: str | None = None
    language: str | None = None
    sentiment: str | None = None
    answered_by_voice_mail: bool | None = None

    extracted_data: dict[str, Any] | None = None
    extracted: dict[str, Any] | None = None
    extractions: dict[str, Any] | None = None
    custom_extractions: dict[str, Any] | list[Any] | None = None
    agent_extraction: dict[str, Any] | None = None
    telephony_data: dict[str, Any] | None = None


class WebhookAck(BaseModel):
    """We always 200 OK so Bolna does not retry. Body is informational."""

    received: bool = True
    call_id: str | None = None
    order_id: str | None = None
    applied: bool = False
    reason: str | None = None
