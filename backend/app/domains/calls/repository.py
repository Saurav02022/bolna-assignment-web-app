"""Data access for calls + idempotency tracking.

Talks only to the abstract ``Store`` protocol.
"""

from typing import Any

from app.core.db import Store


class CallRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def upsert(self, call: dict[str, Any]) -> dict[str, Any]:
        return await self._store.upsert_call(call)

    async def get(self, call_id: str) -> dict[str, Any] | None:
        return await self._store.get_call(call_id)

    async def list_for_order(self, order_id: str) -> list[dict[str, Any]]:
        return await self._store.list_calls_for_order(order_id)

    async def already_processed(self, call_id: str) -> bool:
        return await self._store.is_call_processed(call_id)

    async def mark_processed(self, call_id: str) -> None:
        await self._store.mark_call_processed(call_id)

    async def clear_processed(self, call_id: str) -> None:
        await self._store.clear_call_processed(call_id)
