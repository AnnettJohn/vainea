"""Einmalige Migration: alle Bilder aus app/static/images/ in den
konfigurierten Objektspeicher hochladen und die betroffenen
State/ProductImage-URLs in der DB darauf umbiegen.

Voraussetzung: S3_* Variablen in .env gesetzt (siehe .env.example).
Sicher mehrfach ausführbar - lädt Dateien erneut hoch (überschreibt) und
biegt nur URLs um, die noch auf /static/images/ zeigen.

    python -m scripts.upload_images_to_storage
"""

import asyncio
import mimetypes
from pathlib import Path

from sqlalchemy import select

from app.core.storage import get_s3_client, storage_configured, upload_file
from app.db.session import async_session_maker
from app.models.product import ProductImage
from app.models.state import State

IMAGES_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "images"
LOCAL_PREFIX = "/static/images/"


def upload_all_images() -> dict[str, str]:
    """Alle Dateien aus IMAGES_DIR hochladen, gibt {dateiname: neue_url} zurück."""
    client = get_s3_client()
    url_by_filename: dict[str, str] = {}

    for path in sorted(IMAGES_DIR.iterdir()):
        if not path.is_file():
            continue
        content_type = mimetypes.guess_type(path.name)[0]
        key = f"images/{path.name}"
        new_url = upload_file(client, path, key, content_type=content_type)
        url_by_filename[path.name] = new_url
        print(f"  hochgeladen: {path.name} -> {new_url}")

    return url_by_filename


async def rewrite_urls(url_by_filename: dict[str, str]) -> tuple[int, int]:
    state_updates = 0
    image_updates = 0

    async with async_session_maker() as session:
        states = (await session.execute(select(State))).scalars().all()
        for state in states:
            for field in ("hero_image_url", "circle_image_url"):
                current = getattr(state, field)
                if current and current.startswith(LOCAL_PREFIX):
                    filename = current.removeprefix(LOCAL_PREFIX)
                    if filename in url_by_filename:
                        setattr(state, field, url_by_filename[filename])
                        state_updates += 1

        images = (await session.execute(select(ProductImage))).scalars().all()
        for image in images:
            if image.url and image.url.startswith(LOCAL_PREFIX):
                filename = image.url.removeprefix(LOCAL_PREFIX)
                if filename in url_by_filename:
                    image.url = url_by_filename[filename]
                    image_updates += 1

        await session.commit()

    return state_updates, image_updates


async def main() -> None:
    if not storage_configured():
        raise SystemExit(
            "Objektspeicher nicht konfiguriert (S3_ENDPOINT_URL/S3_BUCKET/"
            "S3_ACCESS_KEY_ID in .env setzen) - Abbruch."
        )

    print(f"Lade Bilder aus {IMAGES_DIR} hoch ...")
    url_by_filename = upload_all_images()

    state_updates, image_updates = await rewrite_urls(url_by_filename)
    print(
        f"Fertig: {len(url_by_filename)} Dateien hochgeladen, "
        f"{state_updates} State-Felder und {image_updates} ProductImage-Zeilen umgebogen."
    )


if __name__ == "__main__":
    asyncio.run(main())
