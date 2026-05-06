from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import register_exception_handlers
from app.core.settings import settings
from app.domains.calls.router import orders_action_router, webhook_router
from app.domains.health.router import router as health_router
from app.domains.orders.router import router as orders_router
from app.lifespan import lifespan


def _split_origins(value: str) -> list[str]:
    return [o.strip() for o in value.split(",") if o.strip()]


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_split_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(orders_router)
app.include_router(orders_action_router)
app.include_router(webhook_router)
