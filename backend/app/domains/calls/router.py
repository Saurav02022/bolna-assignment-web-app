import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.deps import get_call_service
from app.domains.calls.schemas import (
    BolnaWebhookPayload,
    CallRecord,
    TriggerCallResponse,
    WebhookAck,
)
from app.domains.calls.service import CallService
from app.domains.orders.schemas import OrderResponse

log = logging.getLogger(__name__)

orders_action_router = APIRouter(prefix="/orders", tags=["calls"])


@orders_action_router.post(
    "/{order_id}/verify",
    response_model=TriggerCallResponse,
    summary="Trigger a Bolna outbound verification call for an order",
)
async def verify_order(
    order_id: str,
    svc: Annotated[CallService, Depends(get_call_service)],
) -> TriggerCallResponse:
    return await svc.verify_order(order_id)


@orders_action_router.get(
    "/{order_id}/calls",
    response_model=list[CallRecord],
    summary="List calls placed for an order (newest first)",
)
async def list_calls(
    order_id: str,
    svc: Annotated[CallService, Depends(get_call_service)],
) -> list[CallRecord]:
    return await svc.list_calls_for_order(order_id)


@orders_action_router.post(
    "/{order_id}/refresh",
    response_model=OrderResponse,
    summary="Pull the latest execution data from Bolna for the order's last call",
)
async def refresh_order(
    order_id: str,
    svc: Annotated[CallService, Depends(get_call_service)],
    call_id: str | None = None,
    force: bool = False,
) -> OrderResponse:
    return await svc.refresh_call_from_bolna(order_id, call_id=call_id, force=force)


webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhook_router.post(
    "/bolna",
    response_model=WebhookAck,
    summary="Receive post-call execution data from Bolna",
)
async def bolna_webhook(
    request: Request,
    svc: Annotated[CallService, Depends(get_call_service)],
) -> WebhookAck:
    raw = await request.json()
    if isinstance(raw, dict):
        log.info("BOLNA_WEBHOOK status=%s id=%s keys=%s", raw.get("status"), raw.get("id"), list(raw.keys()))
        for sub in ("context_details", "agent_context_details", "recipient_data", "custom_extractions", "extracted_data", "agent_extraction"):
            log.info("BOLNA_WEBHOOK.%s = %s", sub, json.dumps(raw.get(sub), default=str)[:1500])
    payload = BolnaWebhookPayload.model_validate(raw)
    return await svc.handle_webhook(payload)
