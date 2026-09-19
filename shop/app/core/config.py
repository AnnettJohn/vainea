from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://vainea:vainea@localhost:5432/vainea"

    secret_key: str = "change-me"
    admin_session_secret: str = "change-me-too"

    mollie_api_key: str = ""
    mollie_webhook_url: str = ""

    # Defaults passen zu Mailhog/Mailpit (lokaler SMTP-Catcher ohne Login/TLS
    # auf Port 1025) - für Produktion einen echten SMTP-Anbieter eintragen.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from_email: str = "no-reply@vainea.de"
    smtp_from_name: str = "VAINEA"

    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
