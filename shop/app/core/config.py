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

    # Objektspeicher für Produktbilder (Hetzner Object Storage, S3-kompatibel;
    # siehe Pflichtenheft "Produktbilder in Objektspeicher statt lokal auf
    # dem Server"). Leer lassen für lokale Entwicklung - Bilder bleiben dann
    # unter app/static/images (siehe scripts/upload_images_to_storage.py für
    # die einmalige Migration bei Produktions-Deployment).
    s3_endpoint_url: str = ""
    s3_region: str = "fsn1"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""

    # Eigener, NICHT öffentlicher Bucket für die Datenbank-Dumps aus
    # scripts/backup.sh. Bewusst getrennt vom Bilder-Bucket: der ist
    # absichtlich öffentlich lesbar, ein Dump dort wäre ein Datenleck mit
    # Namen, Adressen und Bestellhistorien. scripts/upload_backup.py
    # verweigert den Upload, wenn beide Werte gleich sind.
    s3_backup_bucket: str = ""

    # Aufbewahrung der Dumps im Objektspeicher. Bewusst laenger als die
    # lokale Frist in backup.sh: die Offsite-Kopie ist die, die im Ernstfall
    # noch da ist.
    backup_retention_days: int = 30

    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
