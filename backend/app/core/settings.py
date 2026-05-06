from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    ENV: str = "development"
    APP_NAME: str = "Bolna Backend"

    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    DATABASE_URL: str | None = None
    JWT_SECRET: str | None = None

    BOLNA_API_KEY: str | None = None
    BOLNA_AGENT_ID: str | None = None
    BOLNA_API_BASE_URL: str = "https://api.bolna.ai"
    BOLNA_FROM_NUMBER: str | None = None

    DEMO_RECIPIENT_NUMBER: str | None = None

    BOLNA_WEBHOOK_SHARED_SECRET: str | None = None

    # Storage backend selection. "memory" (default, used in tests & local dev)
    # or "firestore" (Cloud Run prod). Firestore uses Application Default
    # Credentials — no key file needed when running on Cloud Run.
    STORE_BACKEND: str = "memory"
    GCP_PROJECT_ID: str | None = None

    @property
    def is_demo_override_active(self) -> bool:
        return bool(self.DEMO_RECIPIENT_NUMBER)


settings = Settings()
