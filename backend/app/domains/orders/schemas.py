from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Lifecycle of an order across pre-dispatch verification."""

    pending_verification = "pending_verification"
    verifying = "verifying"
    ship_approved = "ship_approved"
    address_correction_requested = "address_correction_requested"
    reschedule_requested = "reschedule_requested"
    cancelled = "cancelled"
    needs_followup = "needs_followup"
    unreachable = "unreachable"
    call_failed = "call_failed"


class OrderCreate(BaseModel):
    """Input payload to create a new order."""

    customer_name: str = Field(..., examples=["Priya Patel"])
    phone: str = Field(..., examples=["+919572365331"], description="E.164 format")
    product_summary: str = Field(..., examples=["Cotton Kurta size L"])
    order_value: int = Field(..., examples=[1299], ge=0)
    address_short: str = Field(..., examples=["Indiranagar, Bengaluru 560038"])
    scheduled_slot: str = Field(..., examples=["7 May, 2 PM se 6 PM"])
    brand_name: str = Field(default="RetailKart", examples=["RetailKart"])


class OrderUpdate(BaseModel):
    """Partial patch for ops — Bolna-derived fields stay unless changed elsewhere."""

    customer_name: str | None = Field(default=None)
    phone: str | None = Field(default=None, description="E.164 format")
    product_summary: str | None = None
    order_value: int | None = Field(default=None, ge=0)
    address_short: str | None = None
    scheduled_slot: str | None = None
    brand_name: str | None = None


class OrderResponse(BaseModel):
    """Full order record returned by the API."""

    id: str
    customer_name: str
    phone: str
    product_summary: str
    order_value: int
    address_short: str
    scheduled_slot: str
    brand_name: str

    status: OrderStatus
    last_call_id: str | None = None
    last_call_outcome: str | None = None
    captured_address_landmark: str | None = None
    captured_new_slot: str | None = None
    captured_cancel_reason: str | None = None
    captured_followup_question: str | None = None
    last_transcript_url: str | None = None
    last_recording_url: str | None = None
    last_summary: str | None = None

    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """Paginated-style envelope (no pagination yet, demo scope)."""

    items: list[OrderResponse]
    total: int
