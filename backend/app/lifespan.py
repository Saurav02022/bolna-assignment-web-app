from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import store_lifespan
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    async with store_lifespan() as store:
        app.state.store = store
        from app.domains.orders.seed import reconcile_placeholder_phones, seed_demo_orders

        await seed_demo_orders(store)
        await reconcile_placeholder_phones(store)
        yield
