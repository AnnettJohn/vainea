from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://vainea:vainea@localhost:5432/vainea"

    secret_key: str = "change-me"
    admin_session_secret: str = "change-me-too"

    mollie_api_key: str = ""
    mollie_webhook_url: str = ""

    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
