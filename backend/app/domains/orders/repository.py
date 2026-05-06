"""Data access for orders.

Talks only to the abstract ``Store`` protocol so swapping backends
(InMemoryStore ↔ FirestoreStore ↔ a future Postgres impl) does not affect
services or routers.
"""

from typing import Any

from app.core.db import Store


class OrderRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def insert(self, order: dict[str, Any]) -> dict[str, Any]:
        return await self._store.upsert_order(order)

    async def replace(self, order: dict[str, Any]) -> dict[str, Any]:
        """Full-document replace (caller supplies merged snapshot including id)."""
        return await self._store.upsert_order(order)

    async def delete(self, order_id: str) -> None:
        await self._store.delete_order(order_id)

    async def get(self, order_id: str) -> dict[str, Any] | None:
        return await self._store.get_order(order_id)

    async def list(self) -> list[dict[str, Any]]:
        return await self._store.list_orders()

    async def update(self, order_id: str, new_state: dict[str, Any]) -> dict[str, Any]:
        return await self._store.upsert_order({**new_state, "id": order_id})
