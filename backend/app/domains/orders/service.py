"""Order business logic — list / create / fetch."""

from datetime import datetime, timezone

from app.core.exceptions import AppError
from app.domains.orders.mutator import apply_order_customer_patch, new_order_record
from app.domains.orders.repository import OrderRepository
from app.domains.orders.schemas import OrderCreate, OrderListResponse, OrderResponse, OrderUpdate


class OrderNotFound(AppError):
    def __init__(self, order_id: str):
        super().__init__(
            message=f"Order {order_id} not found",
            code="ORDER_NOT_FOUND",
            status_code=404,
        )


class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    async def create_order(self, payload: OrderCreate) -> OrderResponse:
        record = new_order_record(payload, now=datetime.now(timezone.utc))
        saved = await self._repo.insert(record)
        return OrderResponse.model_validate(saved)

    async def list_orders(self) -> OrderListResponse:
        records = await self._repo.list()
        records.sort(key=lambda r: r["created_at"], reverse=True)
        items = [OrderResponse.model_validate(r) for r in records]
        return OrderListResponse(items=items, total=len(items))

    async def get_order(self, order_id: str) -> OrderResponse:
        record = await self._repo.get(order_id)
        if record is None:
            raise OrderNotFound(order_id)
        return OrderResponse.model_validate(record)

    async def update_order(self, order_id: str, patch: OrderUpdate) -> OrderResponse:
        filtered = patch.model_dump(exclude_unset=True)
        if not filtered:
            raise AppError(
                message="At least one updatable field is required.",
                code="EMPTY_ORDER_PATCH",
                status_code=422,
            )
        existing = await self._repo.get(order_id)
        if existing is None:
            raise OrderNotFound(order_id)
        merged = apply_order_customer_patch(
            existing,
            patch=filtered,
            now=datetime.now(timezone.utc),
        )
        saved = await self._repo.replace(merged)
        return OrderResponse.model_validate(saved)

    async def delete_order(self, order_id: str) -> None:
        existing = await self._repo.get(order_id)
        if existing is None:
            raise OrderNotFound(order_id)
        await self._repo.delete(order_id)
