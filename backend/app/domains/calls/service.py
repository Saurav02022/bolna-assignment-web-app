"""Call orchestration — trigger outbound calls and process Bolna webhooks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import AppError
from app.core.settings import settings
from app.domains.calls.mutator import (
    apply_completion,
    coerce_status,
    extract_call_id,
    extract_extractions,
    extract_order_id,
    is_terminal_status,
    new_call_record,
    normalise_outcome_tag,
)
from app.domains.calls.repository import CallRepository
from app.domains.calls.schemas import (
    BolnaWebhookPayload,
    CallRecord,
    CallStatus,
    TriggerCallResponse,
    WebhookAck,
)
from app.domains.orders.mutator import apply_call_outcome, mark_call_failed, mark_verifying
from app.domains.orders.repository import OrderRepository
from app.domains.orders.schemas import OrderResponse
from app.domains.orders.service import OrderNotFound
from app.shared.bolna_client import BolnaClient, BolnaError

log = logging.getLogger(__name__)


class BolnaNotConfigured(AppError):
    def __init__(self) -> None:
        super().__init__(
            message="BOLNA_API_KEY or BOLNA_AGENT_ID is missing — set them in .env.",
            code="BOLNA_NOT_CONFIGURED",
            status_code=503,
        )


class CallTriggerFailed(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            message=f"Failed to place call via Bolna: {detail}",
            code="CALL_TRIGGER_FAILED",
            status_code=502,
        )


class CallService:
    def __init__(
        self,
        *,
        call_repo: CallRepository,
        order_repo: OrderRepository,
        bolna: BolnaClient,
        agent_id: str | None,
        from_number: str | None,
        demo_recipient: str | None,
    ) -> None:
        self._call_repo = call_repo
        self._order_repo = order_repo
        self._bolna = bolna
        self._agent_id = agent_id
        self._from_number = from_number
        self._demo_recipient = demo_recipient

    async def verify_order(self, order_id: str) -> TriggerCallResponse:
        if not self._agent_id or not self._bolna:
            raise BolnaNotConfigured()

        order = await self._order_repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        recipient = self._resolve_recipient(order["phone"])
        user_data = self._build_user_data(order)
        now = datetime.now(timezone.utc)

        try:
            response = await self._bolna.place_call(
                agent_id=self._agent_id,
                recipient_phone_number=recipient,
                from_phone_number=self._from_number or None,
                user_data=user_data,
            )
        except BolnaError as exc:
            failed_state = mark_call_failed(order, now=now)
            await self._order_repo.update(order["id"], failed_state)
            raise CallTriggerFailed(exc.message) from exc

        call_id = response.get("execution_id") or response.get("call_id") or "unknown"
        bolna_status = response.get("status") or "queued"

        call = new_call_record(
            call_id=call_id,
            order_id=order["id"],
            bolna_status=bolna_status,
            now=now,
        )
        await self._call_repo.upsert(call)

        verifying_state = mark_verifying(order, call_id=call_id, now=now)
        saved_order = await self._order_repo.update(order["id"], verifying_state)

        return TriggerCallResponse(
            order=OrderResponse.model_validate(saved_order),
            call_id=call_id,
            bolna_status=bolna_status,
        )

    async def handle_webhook(self, payload: BolnaWebhookPayload) -> WebhookAck:
        call_id = extract_call_id(payload)
        if not call_id:
            log.warning("Webhook received without call_id/execution_id; ignoring.")
            return WebhookAck(received=True, applied=False, reason="missing_call_id")

        existing_call = await self._call_repo.get(call_id)

        # Bolna does not echo our `order_id` in the webhook (it only persists
        # keys declared as agent variables). Fallback to the call record we
        # created at trigger time, which always carries the linkage.
        order_id = extract_order_id(payload) or (
            existing_call.get("order_id") if existing_call else None
        )
        order = await self._order_repo.get(order_id) if order_id else None

        if not is_terminal_status(payload.status):
            now = datetime.now(timezone.utc)
            base = existing_call or new_call_record(
                call_id=call_id,
                order_id=order["id"] if order else (order_id or "unknown"),
                bolna_status=payload.status,
                now=now,
            )
            base["status"] = coerce_status(
                payload.status,
                default=base.get("status") or CallStatus.queued,
            )
            await self._call_repo.upsert(base)
            log.info(
                "Webhook progress: call_id=%s status=%s (non-terminal, no outcome applied)",
                call_id,
                payload.status,
            )
            return WebhookAck(
                received=True,
                call_id=call_id,
                order_id=order["id"] if order else order_id,
                applied=False,
                reason=f"non_terminal:{payload.status}",
            )

        if await self._call_repo.already_processed(call_id):
            log.info("Webhook duplicate for call_id=%s; idempotent skip.", call_id)
            return WebhookAck(
                received=True,
                call_id=call_id,
                applied=False,
                reason="duplicate",
            )

        if order is None:
            log.warning("Webhook for call_id=%s has no matching order_id=%s.", call_id, order_id)
            return WebhookAck(
                received=True,
                call_id=call_id,
                order_id=order_id,
                applied=False,
                reason="order_not_found",
            )

        extractions = extract_extractions(payload)
        outcome_tag = normalise_outcome_tag(extractions.get("outcome_tag"))
        if outcome_tag is None and payload.answered_by_voice_mail:
            outcome_tag = "unreachable"

        # Bolna fires `call-disconnected` first, then later (sometimes) a
        # second terminal webhook with extractions populated. Only finalise
        # (mark processed) when we actually have a usable signal.
        has_signal = bool(extractions) or bool(payload.answered_by_voice_mail)

        now = datetime.now(timezone.utc)
        base_call = existing_call or new_call_record(
            call_id=call_id,
            order_id=order["id"],
            bolna_status=payload.status,
            now=now,
        )

        updated_call = apply_completion(
            base_call,
            payload=payload,
            extractions=extractions,
            outcome_tag=outcome_tag,
            now=now,
        )
        await self._call_repo.upsert(updated_call)

        if has_signal or outcome_tag is not None:
            updated_order = apply_call_outcome(
                order,
                outcome_tag=outcome_tag,
                extractions=extractions,
                transcript_url=updated_call["transcript_url"],
                recording_url=updated_call["recording_url"],
                summary=updated_call["summary"],
                now=now,
            )
            await self._order_repo.update(order["id"], updated_order)
            order_status = updated_order["status"]
        else:
            # Terminal but no extractions yet — keep order in `verifying` and
            # wait for the follow-up webhook with `extracted_data` populated.
            order_status = order["status"]
            log.info(
                "Terminal webhook without extractions yet (call_id=%s status=%s) — "
                "awaiting follow-up.",
                call_id,
                payload.status,
            )

        if has_signal:
            await self._call_repo.mark_processed(call_id)

        log.info(
            "Webhook applied: order_id=%s call_id=%s outcome=%s status=%s signal=%s",
            order["id"],
            call_id,
            outcome_tag,
            order_status,
            has_signal,
        )

        return WebhookAck(
            received=True,
            call_id=call_id,
            order_id=order["id"],
            applied=True,
        )

    async def refresh_call_from_bolna(
        self,
        order_id: str,
        *,
        call_id: str | None = None,
        force: bool = False,
    ) -> OrderResponse:
        """Pull the latest execution data from Bolna for the order's last call.

        Webhooks are best-effort and Bolna's extraction pipeline runs async
        after `call-disconnected`. This endpoint is the deterministic escape
        hatch: it fetches the canonical execution record and runs the same
        completion logic, so the order ends up in its final state regardless
        of webhook delivery.

        - `call_id` lets callers replay a specific execution (e.g. after a
          server restart wipes the in-memory state, or to re-process an old
          call once Bolna's extraction step finally fires).
        - `force=True` clears the idempotency mark so we re-apply the call
          (useful when extractions arrive late).
        """
        if not self._bolna:
            raise BolnaNotConfigured()

        order = await self._order_repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        execution_id = call_id or order.get("last_call_id")
        if not execution_id:
            raise CallTriggerFailed("No call has been placed for this order yet.")

        try:
            payload_dict = await self._bolna.get_execution(execution_id)
        except BolnaError as exc:
            raise CallTriggerFailed(exc.message) from exc

        log.info(
            "Refreshed execution=%s status=%s extracted=%s",
            execution_id,
            payload_dict.get("status"),
            bool(payload_dict.get("extracted_data") or payload_dict.get("custom_extractions")),
        )

        # If the caller passed an explicit call_id, ensure our local record
        # exists so handle_webhook can resolve order_id from the call linkage.
        if call_id:
            now = datetime.now(timezone.utc)
            existing = await self._call_repo.get(call_id)
            if existing is None:
                await self._call_repo.upsert(
                    new_call_record(
                        call_id=call_id,
                        order_id=order["id"],
                        bolna_status=payload_dict.get("status"),
                        now=now,
                    )
                )
            if order.get("last_call_id") != call_id:
                order = {**order, "last_call_id": call_id, "updated_at": now}
                await self._order_repo.update(order["id"], order)

        if force:
            await self._call_repo.clear_processed(execution_id)

        # Reuse webhook handler — GET /executions response shape matches it.
        payload = BolnaWebhookPayload.model_validate(payload_dict)
        await self.handle_webhook(payload)

        refreshed = await self._order_repo.get(order_id)
        return OrderResponse.model_validate(refreshed)

    async def list_calls_for_order(self, order_id: str) -> list[CallRecord]:
        records = await self._call_repo.list_for_order(order_id)
        records.sort(key=lambda c: c["triggered_at"], reverse=True)
        return [CallRecord.model_validate(r) for r in records]

    def _resolve_recipient(self, order_phone: str) -> str:
        """Trial plan only allows verified numbers — override during demo."""
        if settings.is_demo_override_active:
            override = self._demo_recipient or order_phone
            if override != order_phone:
                log.info(
                    "DEMO override active: routing call to %s instead of %s",
                    override,
                    order_phone,
                )
            return override
        return order_phone

    @staticmethod
    def _build_user_data(order: dict[str, Any]) -> dict[str, Any]:
        """Variables consumed by the agent prompt at runtime."""
        return {
            "order_id": order["id"],
            "customer_name": order["customer_name"],
            "product_summary": order["product_summary"],
            "order_value": order["order_value"],
            "address_short": order["address_short"],
            "scheduled_slot": order["scheduled_slot"],
            "brand_name": order["brand_name"],
        }
