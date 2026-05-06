from typing import Annotated

from fastapi import Depends, Request

from app.core.db import Store
from app.core.settings import settings
from app.domains.calls.repository import CallRepository
from app.domains.calls.service import CallService
from app.domains.health.repository import HealthRepository
from app.domains.health.service import HealthService
from app.domains.orders.repository import OrderRepository
from app.domains.orders.service import OrderService
from app.shared.bolna_client import BolnaClient


def get_store(request: Request) -> Store:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise RuntimeError("Store not initialised on app state — check lifespan.")
    return store


def get_health_repository(
    store: Annotated[Store, Depends(get_store)],
) -> HealthRepository:
    return HealthRepository(db=store)


def get_health_service(
    repo: Annotated[HealthRepository, Depends(get_health_repository)],
) -> HealthService:
    return HealthService(repo=repo)


def get_order_repository(
    store: Annotated[Store, Depends(get_store)],
) -> OrderRepository:
    return OrderRepository(store=store)


def get_order_service(
    repo: Annotated[OrderRepository, Depends(get_order_repository)],
) -> OrderService:
    return OrderService(repo=repo)


def get_call_repository(
    store: Annotated[Store, Depends(get_store)],
) -> CallRepository:
    return CallRepository(store=store)


def get_bolna_client() -> BolnaClient:
    return BolnaClient(
        api_key=settings.BOLNA_API_KEY or "",
        base_url=settings.BOLNA_API_BASE_URL,
    )


def get_call_service(
    call_repo: Annotated[CallRepository, Depends(get_call_repository)],
    order_repo: Annotated[OrderRepository, Depends(get_order_repository)],
    bolna: Annotated[BolnaClient, Depends(get_bolna_client)],
) -> CallService:
    return CallService(
        call_repo=call_repo,
        order_repo=order_repo,
        bolna=bolna,
        agent_id=settings.BOLNA_AGENT_ID,
        from_number=settings.BOLNA_FROM_NUMBER,
        demo_recipient=settings.DEMO_RECIPIENT_NUMBER,
    )
