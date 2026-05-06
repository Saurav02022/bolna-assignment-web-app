"""Demo seed data so the dashboard is non-empty on first launch."""

from datetime import datetime, timedelta, timezone

from app.core.db import Store
from app.core.settings import settings
from app.domains.orders.mutator import new_order_record
from app.domains.orders.schemas import OrderCreate

# Fallback when DEMO_RECIPIENT_NUMBER is unset — not a reachable number on Bolna trial.
DEMO_PHONE_PLACEHOLDER = "+910000000000"


def _demo_phone_for_seed() -> str:
    demo = settings.DEMO_RECIPIENT_NUMBER
    if demo and demo.strip():
        return demo.strip()
    return DEMO_PHONE_PLACEHOLDER


async def seed_demo_orders(store: Store) -> None:
    """Idempotent: only seeds when the store is empty."""
    existing = await store.list_orders()
    if existing:
        return

    now = datetime.now(timezone.utc)
    phone = _demo_phone_for_seed()

    samples = [
        OrderCreate(
            customer_name="Riya Kapoor",
            phone=phone,
            product_summary="Cotton Kurta size L",
            order_value=1299,
            address_short="Indiranagar, Bengaluru 560038",
            scheduled_slot="7 May, 2 PM se 6 PM",
            brand_name="RetailKart",
        ),
        OrderCreate(
            customer_name="Priya",
            phone=phone,
            product_summary="Wireless Earbuds Pro",
            order_value=2499,
            address_short="Andheri West, Mumbai 400053",
            scheduled_slot="8 May, 10 AM se 1 PM",
            brand_name="RetailKart",
        ),
        OrderCreate(
            customer_name="Rohan",
            phone=phone,
            product_summary="Smart LED Bulb 12W",
            order_value=499,
            address_short="Saket, New Delhi 110017",
            scheduled_slot="9 May, 5 PM se 8 PM",
            brand_name="RetailKart",
        ),
    ]

    for index, payload in enumerate(samples):
        record = new_order_record(
            payload,
            now=now - timedelta(minutes=index * 7),
            order_id=f"ORD-{1001 + index}",
        )
        await store.upsert_order(record)


async def reconcile_placeholder_phones(store: Store) -> None:
    """Backfill seeded placeholder contacts after DEMO_RECIPIENT_NUMBER is configured.

    First boot may have seeded ``DEMO_PHONE_PLACEHOLDER`` into Firestore; later the same
    env/secret carries the user's Bolna-verified handset. Idempotent."""
    recipient = settings.DEMO_RECIPIENT_NUMBER
    if not recipient or not recipient.strip():
        return
    recipient = recipient.strip()

    orders = await store.list_orders()
    now = datetime.now(timezone.utc)
    for row in orders:
        current = (row.get("phone") or "").strip()
        if current == DEMO_PHONE_PLACEHOLDER:
            await store.upsert_order({**row, "phone": recipient, "updated_at": now})
