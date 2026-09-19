"""Test-Setup: startet eine echte, ephemere Postgres-Instanz (pgserver) statt
gegen SQLite zu testen, da das Projekt Postgres-spezifische Typen (UUID,
ARRAY, native ENUM) nutzt. Die DATABASE_URL wird auf Modulebene gesetzt,
BEVOR irgendein app.*-Modul importiert wird, damit app.core.config.Settings
sie beim ersten get_settings()-Aufruf einliest.
"""

import os
import tempfile

import pgserver

_pgdata = tempfile.mkdtemp(prefix="vainea_test_pg_")
_srv = pgserver.get_server(_pgdata, cleanup_mode="delete")
_srv.psql("CREATE DATABASE vainea_test;")

os.environ["DATABASE_URL"] = f"postgresql+asyncpg://postgres@/vainea_test?host={_pgdata}"
os.environ["ENVIRONMENT"] = "testing"
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-bytes-long-for-hs256")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-admin-secret")
os.environ.setdefault("MOLLIE_API_KEY", "")  # bewusst leer: Zahlungsanbindung wird gemockt/übersprungen
# Eigener Port statt des Mailhog/Mailpit-Standards 1025, damit die Tests auch
# neben einer lokal laufenden echten Instanz funktionieren.
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1125")

# Ab hier dürfen App-Module importiert werden - sie lesen die obigen Env-Vars.
import atexit  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from aiosmtpd.controller import Controller  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import async_session_maker, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Cart,
    CartItem,
    OAuthAccount,
    Order,
    OrderItem,
    User,
    WishlistItem,
)
from scripts.seed import seed_products, seed_shipping_zones, seed_states  # noqa: E402

atexit.register(_srv.cleanup)


class _CapturingSMTPHandler:
    """Nimmt echte SMTP-Zustellungen entgegen (statt smtplib zu mocken) und
    hält sie zur Inspektion in den Tests vor."""

    def __init__(self):
        self.messages: list[dict] = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(
            {
                "mail_from": envelope.mail_from,
                "rcpt_tos": envelope.rcpt_tos,
                "content": envelope.content.decode("utf-8", errors="replace"),
            }
        )
        return "250 Message accepted for delivery"


_smtp_handler = _CapturingSMTPHandler()
_smtp_controller = Controller(_smtp_handler, hostname="localhost", port=int(os.environ["SMTP_PORT"]))
_smtp_controller.start()
atexit.register(_smtp_controller.stop)


@pytest.fixture(autouse=True)
def _clear_smtp_messages():
    _smtp_handler.messages.clear()
    yield


@pytest.fixture
def smtp_messages() -> list[dict]:
    return _smtp_handler.messages


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema_and_catalog():
    """Einmal pro Testlauf: Tabellen anlegen und den Produktkatalog (States/
    Produkte/Versandzonen) aus dem Seed-Skript einspielen - dieselben Daten,
    mit denen auch lokal manuell getestet wird."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        states = await seed_states(session)
        await seed_products(session, states)
        await seed_shipping_zones(session)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_transactional_data():
    """Nach jedem Test: Bestellungen/Warenkörbe/Nutzer/Wishlist zurücksetzen,
    damit Tests sich nicht gegenseitig beeinflussen. Katalogdaten (States,
    Produkte, Versandzonen) bleiben über die ganze Session bestehen."""
    yield
    async with async_session_maker() as session:
        for model in (OrderItem, Order, CartItem, Cart, WishlistItem, OAuthAccount, User):
            await session.execute(delete(model))
        await session.commit()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
