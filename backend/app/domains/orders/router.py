from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import get_order_service
from app.domains.orders.schemas import OrderCreate, OrderListResponse, OrderResponse
from app.domains.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order pending verification",
)
async def create_order(
    payload: OrderCreate,
    svc: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    return await svc.create_order(payload)


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List all orders (newest first)",
)
async def list_orders(
    svc: Annotated[OrderService, Depends(get_order_service)],
) -> OrderListResponse:
    return await svc.list_orders()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get a single order with the latest call outcome",
)
async def get_order(
    order_id: str,
    svc: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    return await svc.get_order(order_id)
