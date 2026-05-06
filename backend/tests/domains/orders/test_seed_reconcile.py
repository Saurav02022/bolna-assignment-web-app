"""Smoke tests for demo seed phone backfill."""

from datetime import datetime, timezone

import pytest

from app.core.db import InMemoryStore
from app.domains.orders import seed as seed_module
from app.domains.orders.mutator import new_order_record
from app.domains.orders.schemas import OrderCreate


@pytest.mark.anyio
async def test_reconcile_placeholder_to_demo(monkeypatch) -> None:
    monkeypatch.setattr(seed_module.settings, "DEMO_RECIPIENT_NUMBER", "+919887766554")

    store = InMemoryStore()
    await store.connect()
    now = datetime.now(timezone.utc)
    payload = OrderCreate(
        customer_name="T",
        phone=seed_module.DEMO_PHONE_PLACEHOLDER,
        product_summary="X",
        order_value=1,
        address_short="A",
        scheduled_slot="1 May",
        brand_name="B",
    )
    row = new_order_record(payload, now=now, order_id="ORD-TEST1")
    await store.upsert_order(row)

    await seed_module.reconcile_placeholder_phones(store)

    got = await store.get_order("ORD-TEST1")
    assert got is not None
    assert got["phone"] == "+919887766554"


@pytest.mark.anyio
async def test_reconcile_skips_when_demo_missing(monkeypatch) -> None:
    monkeypatch.setattr(seed_module.settings, "DEMO_RECIPIENT_NUMBER", "")

    store = InMemoryStore()
    await store.connect()
    now = datetime.now(timezone.utc)
    payload = OrderCreate(
        customer_name="T",
        phone=seed_module.DEMO_PHONE_PLACEHOLDER,
        product_summary="X",
        order_value=1,
        address_short="A",
        scheduled_slot="1 May",
        brand_name="B",
    )
    row = new_order_record(payload, now=now, order_id="ORD-TEST2")
    await store.upsert_order(row)

    await seed_module.reconcile_placeholder_phones(store)

    got = await store.get_order("ORD-TEST2")
    assert got is not None
    assert got["phone"] == seed_module.DEMO_PHONE_PLACEHOLDER

