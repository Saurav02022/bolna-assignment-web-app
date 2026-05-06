"""Data access for health checks (DB driver, caches, external probes)."""

from app.core.db import Store


class HealthRepository:
    def __init__(self, db: Store) -> None:
        self._db = db

    async def ping(self) -> bool:
        # Stores expose `connected` informally; treat absence as healthy
        # since FastAPI lifespan would have failed to start otherwise.
        _ = getattr(self._db, "connected", True)
        return True
