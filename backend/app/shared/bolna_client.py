"""Thin async wrapper around the Bolna HTTP API.

Lives in `shared/` because it could later serve other domains (campaigns,
batches, scheduled retries). Only the outbound-call action is wired today.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.shared.constants import HTTP_TIMEOUT_S

log = logging.getLogger(__name__)


class BolnaError(Exception):
    """Raised when Bolna returns a non-2xx response or transport fails."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BolnaClient:
    """Stateless client; create per-request or reuse via dependency injection."""

    def __init__(self, *, api_key: str, base_url: str = "https://api.bolna.ai") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def place_call(
        self,
        *,
        agent_id: str,
        recipient_phone_number: str,
        user_data: dict[str, Any] | None = None,
        from_phone_number: str | None = None,
        scheduled_at: str | None = None,
    ) -> dict[str, Any]:
        """POST /call — start an outbound call from a Bolna agent.

        Returns Bolna's JSON, which contains `execution_id` and `status`.
        Raises ``BolnaError`` on non-2xx.
        """
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "recipient_phone_number": recipient_phone_number,
        }
        if from_phone_number:
            payload["from_phone_number"] = from_phone_number
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at
        if user_data:
            payload["user_data"] = user_data

        url = f"{self._base_url}/call"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        log.info("Bolna place_call to %s for agent %s", recipient_phone_number, agent_id)

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise BolnaError(f"Network error calling Bolna: {exc}") from exc

        if response.status_code >= 400:
            raise BolnaError(
                f"Bolna API {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        """GET /executions/{execution_id} — fetch the full state of a call.

        Useful when post-call webhooks have not (yet) delivered extractions:
        Bolna's extraction LLM runs asynchronously after `call-disconnected`,
        and polling this endpoint is the deterministic way to resolve a call.
        """
        url = f"{self._base_url}/executions/{execution_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        log.info("Bolna get_execution for %s", execution_id)

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise BolnaError(f"Network error calling Bolna: {exc}") from exc

        if response.status_code >= 400:
            raise BolnaError(
                f"Bolna API {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        return response.json()
