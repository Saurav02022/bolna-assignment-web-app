"""Demo seed data so the dashboard is non-empty on first launch."""

from datetime import datetime, timedelta, timezone

from app.core.db import Store
from app.core.settings import settings
from app.domains.orders.mutator import new_order_record
from app.domains.orders.schemas import OrderCreate

_DEMO_PHONE_FALLBACK = "+910000000000"


def _demo_phone() -> str:
    return settings.DEMO_RECIPIENT_NUMBER or _DEMO_PHONE_FALLBACK


async def seed_demo_orders(store: Store) -> None:
    """Idempotent: only seeds when the store is empty."""
    existing = await store.list_orders()
    if existing:
        return

    now = datetime.now(timezone.utc)
    phone = _demo_phone()

    samples = [
        OrderCreate(
            customer_name="Saurav",
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
