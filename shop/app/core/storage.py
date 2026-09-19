"""S3-kompatibler Objektspeicher für Produktbilder (Hetzner Object Storage),
siehe Pflichtenheft "Produktbilder in Objektspeicher statt lokal auf dem
Server". Wird nur von scripts/upload_images_to_storage.py verwendet - die
laufende App selbst liest/schreibt keine Bilddaten, sondern speichert nur
die (dann auf den Objektspeicher zeigende) URL in ProductImage.url /
State.hero_image_url / State.circle_image_url.
"""

from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


def storage_configured() -> bool:
    return bool(settings.s3_bucket and settings.s3_endpoint_url and settings.s3_access_key_id)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(s3={"addressing_style": "virtual"}),
    )


def public_url_for(key: str) -> str:
    base = settings.s3_public_base_url.rstrip("/")
    return f"{base}/{key}"


def upload_file(client, local_path: Path, key: str, content_type: str | None = None) -> str:
    """Datei in den Objektspeicher hochladen (öffentlich lesbar) und die
    öffentliche URL zurückgeben. Zusätzlich zu ACL=public-read muss der
    Bucket im Hetzner-Cloud-Console i.d.R. auch selbst auf "öffentlich"
    gestellt werden, damit Objekte ohne Zugangsdaten abrufbar sind."""
    extra_args = {"ACL": "public-read"}
    if content_type:
        extra_args["ContentType"] = content_type
    client.upload_file(str(local_path), settings.s3_bucket, key, ExtraArgs=extra_args)
    return public_url_for(key)
