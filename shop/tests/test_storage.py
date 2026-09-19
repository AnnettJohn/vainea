import boto3
import pytest
from moto import mock_aws

from app.core import storage


@pytest.fixture
def s3_env(monkeypatch):
    """Objektspeicher-Settings auf eine von moto gemockte S3-Umgebung zeigen
    lassen - kein echter Hetzner-Bucket nötig, aber echter boto3-Client-Code
    (Request-Bau, ExtraArgs, Fehlerpfade) läuft tatsächlich."""
    monkeypatch.setattr(storage.settings, "s3_endpoint_url", "https://s3.amazonaws.com")
    monkeypatch.setattr(storage.settings, "s3_region", "us-east-1")
    monkeypatch.setattr(storage.settings, "s3_bucket", "vainea-test-bucket")
    monkeypatch.setattr(storage.settings, "s3_access_key_id", "test-key")
    monkeypatch.setattr(storage.settings, "s3_secret_access_key", "test-secret")
    monkeypatch.setattr(storage.settings, "s3_public_base_url", "https://vainea-test-bucket.s3.amazonaws.com")

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="vainea-test-bucket")
        yield


def test_storage_configured_false_when_unset():
    assert storage.storage_configured() is False


def test_storage_configured_true_when_set(s3_env):
    assert storage.storage_configured() is True


def test_public_url_for_strips_trailing_slash(s3_env):
    assert storage.public_url_for("images/foo.png") == "https://vainea-test-bucket.s3.amazonaws.com/images/foo.png"


def test_upload_file_puts_object_and_returns_public_url(s3_env, tmp_path):
    local_file = tmp_path / "test-image.png"
    local_file.write_bytes(b"not-a-real-png-but-good-enough")

    client = storage.get_s3_client()
    url = storage.upload_file(client, local_file, "images/test-image.png", content_type="image/png")

    assert url == "https://vainea-test-bucket.s3.amazonaws.com/images/test-image.png"

    obj = client.get_object(Bucket="vainea-test-bucket", Key="images/test-image.png")
    assert obj["Body"].read() == b"not-a-real-png-but-good-enough"
    assert obj["ContentType"] == "image/png"


async def test_upload_all_images_and_rewrite_urls(s3_env, db_session, monkeypatch, tmp_path):
    from sqlalchemy import select

    from app.models.product import Product, ProductImage
    from app.models.state import State
    from scripts import upload_images_to_storage as migrate

    # Kleine Fake-Bilderablage statt der echten app/static/images, damit der
    # Test nicht von den tatsächlich vorhandenen Dateien abhängt.
    fake_images_dir = tmp_path / "images"
    fake_images_dir.mkdir()
    (fake_images_dir / "sun-hero.jpg").write_bytes(b"fake-hero")
    monkeypatch.setattr(migrate, "IMAGES_DIR", fake_images_dir)

    url_by_filename = migrate.upload_all_images()
    assert url_by_filename == {
        "sun-hero.jpg": "https://vainea-test-bucket.s3.amazonaws.com/images/sun-hero.jpg"
    }

    state = (await db_session.execute(select(State).where(State.slug == "sun"))).scalar_one()
    old_hero = state.hero_image_url
    state.hero_image_url = "/static/images/sun-hero.jpg"
    await db_session.commit()

    product = (await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))).scalar_one()
    image = ProductImage(product_id=product.id, url="/static/images/sun-hero.jpg", sort_order=0)
    db_session.add(image)
    await db_session.commit()

    state_updates, image_updates = await migrate.rewrite_urls(url_by_filename)
    assert state_updates == 1
    assert image_updates == 1

    await db_session.refresh(state)
    await db_session.refresh(image)
    assert state.hero_image_url == "https://vainea-test-bucket.s3.amazonaws.com/images/sun-hero.jpg"
    assert image.url == "https://vainea-test-bucket.s3.amazonaws.com/images/sun-hero.jpg"

    # Aufräumen, damit andere Tests wieder den ursprünglichen Seed-Zustand sehen
    state.hero_image_url = old_hero
    await db_session.delete(image)
    await db_session.commit()
