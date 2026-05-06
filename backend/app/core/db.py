"""Pluggable persistence layer.

Two implementations:
- ``InMemoryStore``  — fast, dict-backed; used for tests and local dev.
- ``FirestoreStore`` — Google Cloud Firestore (Native mode); used in prod.

The repository layer talks only to the abstract ``Store`` protocol so swapping
backends (or adding Postgres later) does not ripple into services or routers.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

from app.core.settings import settings

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------


class Store(Protocol):
    """Async interface every storage backend must satisfy."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    # Orders
    async def get_order(self, order_id: str) -> dict[str, Any] | None: ...
    async def list_orders(self) -> list[dict[str, Any]]: ...
    async def upsert_order(self, order: dict[str, Any]) -> dict[str, Any]: ...

    # Calls
    async def get_call(self, call_id: str) -> dict[str, Any] | None: ...
    async def list_calls_for_order(self, order_id: str) -> list[dict[str, Any]]: ...
    async def upsert_call(self, call: dict[str, Any]) -> dict[str, Any]: ...

    # Idempotency
    async def is_call_processed(self, call_id: str) -> bool: ...
    async def mark_call_processed(self, call_id: str) -> None: ...
    async def clear_call_processed(self, call_id: str) -> None: ...


# ---------------------------------------------------------------------------
# In-memory implementation (tests, local demo)
# ---------------------------------------------------------------------------


class InMemoryStore:
    """Single-process, dict-backed store. Resets on every process start."""

    def __init__(self) -> None:
        self._connected = False
        self.orders: dict[str, dict[str, Any]] = {}
        self.calls: dict[str, dict[str, Any]] = {}
        self.processed_call_ids: set[str] = set()

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        log.info("InMemoryStore initialised (demo mode).")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def reset(self) -> None:
        self.orders.clear()
        self.calls.clear()
        self.processed_call_ids.clear()

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self.orders.get(order_id)

    async def list_orders(self) -> list[dict[str, Any]]:
        return list(self.orders.values())

    async def upsert_order(self, order: dict[str, Any]) -> dict[str, Any]:
        self.orders[order["id"]] = order
        return order

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        return self.calls.get(call_id)

    async def list_calls_for_order(self, order_id: str) -> list[dict[str, Any]]:
        return [c for c in self.calls.values() if c.get("order_id") == order_id]

    async def upsert_call(self, call: dict[str, Any]) -> dict[str, Any]:
        self.calls[call["id"]] = call
        return call

    async def is_call_processed(self, call_id: str) -> bool:
        return call_id in self.processed_call_ids

    async def mark_call_processed(self, call_id: str) -> None:
        self.processed_call_ids.add(call_id)

    async def clear_call_processed(self, call_id: str) -> None:
        self.processed_call_ids.discard(call_id)


# ---------------------------------------------------------------------------
# Firestore implementation (Cloud Run prod)
# ---------------------------------------------------------------------------


_ORDERS = "orders"
_CALLS = "calls"
_PROCESSED = "processed_call_ids"


class FirestoreStore:
    """Google Cloud Firestore (Native mode) backend.

    Uses Application Default Credentials — works seamlessly on Cloud Run with
    a service account that has roles/datastore.user.

    Locally, run ``gcloud auth application-default login`` first.
    """

    def __init__(self, *, project_id: str | None = None) -> None:
        self._project_id = project_id
        self._connected = False
        self._client: Any = None  # firestore.AsyncClient — lazy-imported

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        # Lazy import so test environments without google-cloud-firestore
        # installed (or without GCP credentials) can still run.
        from google.cloud import firestore  # type: ignore[import-not-found]

        self._client = firestore.AsyncClient(project=self._project_id)
        self._connected = True
        log.info("FirestoreStore connected (project=%s)", self._project_id or "default")

    async def disconnect(self) -> None:
        # Firestore async client manages its own gRPC channel; explicit close
        # is a best-effort.
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if close is not None:
                try:
                    result = close()
                    if hasattr(result, "__await__"):
                        await result
                except Exception:  # pragma: no cover — best-effort
                    log.exception("FirestoreStore close failed")
        self._connected = False

    # --- helpers ------------------------------------------------------------

    def _orders(self) -> Any:
        return self._client.collection(_ORDERS)

    def _calls(self) -> Any:
        return self._client.collection(_CALLS)

    def _processed(self) -> Any:
        return self._client.collection(_PROCESSED)

    # --- orders -------------------------------------------------------------

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        snap = await self._orders().document(order_id).get()
        if not snap.exists:
            return None
        return _from_firestore(snap.to_dict() or {})

    async def list_orders(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        async for snap in self._orders().stream():
            data = snap.to_dict() or {}
            out.append(_from_firestore(data))
        return out

    async def upsert_order(self, order: dict[str, Any]) -> dict[str, Any]:
        await self._orders().document(order["id"]).set(_to_firestore(order))
        return order

    # --- calls --------------------------------------------------------------

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        snap = await self._calls().document(call_id).get()
        if not snap.exists:
            return None
        return _from_firestore(snap.to_dict() or {})

    async def list_calls_for_order(self, order_id: str) -> list[dict[str, Any]]:
        query = self._calls().where("order_id", "==", order_id)
        out: list[dict[str, Any]] = []
        async for snap in query.stream():
            out.append(_from_firestore(snap.to_dict() or {}))
        return out

    async def upsert_call(self, call: dict[str, Any]) -> dict[str, Any]:
        await self._calls().document(call["id"]).set(_to_firestore(call))
        return call

    # --- idempotency --------------------------------------------------------

    async def is_call_processed(self, call_id: str) -> bool:
        snap = await self._processed().document(call_id).get()
        return snap.exists

    async def mark_call_processed(self, call_id: str) -> None:
        await self._processed().document(call_id).set({"call_id": call_id})

    async def clear_call_processed(self, call_id: str) -> None:
        await self._processed().document(call_id).delete()


def _to_firestore(record: dict[str, Any]) -> dict[str, Any]:
    """Firestore accepts datetimes natively; only enums / sets need coercion."""
    return {k: _coerce_for_firestore(v) for k, v in record.items()}


def _coerce_for_firestore(value: Any) -> Any:
    # Pydantic enums / Python Enums
    if hasattr(value, "value") and not isinstance(value, (str, int, bool, float)):
        try:
            return value.value
        except AttributeError:  # pragma: no cover
            pass
    if isinstance(value, set):
        return list(value)
    if isinstance(value, dict):
        return {k: _coerce_for_firestore(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_for_firestore(v) for v in value]
    return value


def _from_firestore(record: dict[str, Any]) -> dict[str, Any]:
    """Firestore returns native Python types; no transform needed today."""
    return record


# ---------------------------------------------------------------------------
# Factory + lifespan
# ---------------------------------------------------------------------------


def make_store() -> Store:
    """Pick the backend based on env. Default = memory (safe for tests/CI)."""
    backend = (settings.STORE_BACKEND or "memory").lower()
    if backend == "firestore":
        return FirestoreStore(project_id=settings.GCP_PROJECT_ID)
    return InMemoryStore()


@asynccontextmanager
async def store_lifespan() -> AsyncIterator[Store]:
    store = make_store()
    await store.connect()
    try:
        yield store
    finally:
        await store.disconnect()
