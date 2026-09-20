"""Der Seed läuft bei jedem Containerstart (docker-entrypoint.sh). Er darf
deshalb keine im Admin gepflegten Daten überschreiben - sonst setzt jedes
Deployment Preise, Texte und Versandtarife auf die Dummy-Werte zurück.

States, Produkte und Versandzonen werden einmal pro Testlauf angelegt und von
allen Tests geteilt (siehe conftest). Diese Tests verändern sie bewusst und
stellen sie darum am Ende über den --force-Pfad wieder her.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.product import Product
from app.models.shipping import ShippingRate, ShippingZone
from app.models.state import State
from scripts.seed import seed_products, seed_shipping_zones, seed_states


@pytest.fixture
async def restore_seed_data(db_session):
    """Nach dem Test die Dummy-Werte zurückschreiben, damit die Änderungen
    nicht in andere Tests lecken."""
    yield
    states = await seed_states(db_session, overwrite=True)
    await seed_products(db_session, states, overwrite=True)
    await seed_shipping_zones(db_session, overwrite=True)
    await db_session.commit()


async def test_seed_does_not_overwrite_edited_product(db_session, restore_seed_data):
    result = await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))
    product = result.scalar_one()
    product.price = Decimal("249.00")
    product.name = "Sun Mono Robe (Limited)"
    await db_session.commit()

    states = await seed_states(db_session)
    await seed_products(db_session, states)
    await db_session.commit()

    await db_session.refresh(product)
    assert product.price == Decimal("249.00")
    assert product.name == "Sun Mono Robe (Limited)"


async def test_seed_does_not_overwrite_edited_shipping_rate(db_session, restore_seed_data):
    """Die echten Versandtarife werden laut Absprache im Admin gepflegt -
    genau die Werte, die der Seed früher bei jedem Lauf zurückgesetzt hat."""
    zone_result = await db_session.execute(select(ShippingZone).where(ShippingZone.name == "Deutschland"))
    zone = zone_result.scalar_one()
    zone.free_shipping_threshold = Decimal("75.00")

    rate_result = await db_session.execute(select(ShippingRate).where(ShippingRate.zone_id == zone.id))
    rate = rate_result.scalars().first()
    rate.price = Decimal("6.90")
    await db_session.commit()

    await seed_shipping_zones(db_session)
    await db_session.commit()

    await db_session.refresh(zone)
    await db_session.refresh(rate)
    assert zone.free_shipping_threshold == Decimal("75.00")
    assert rate.price == Decimal("6.90")


async def test_seed_with_force_restores_dummy_values(db_session, restore_seed_data):
    """--force ist der bewusste Ausweg für die Entwicklung."""
    result = await db_session.execute(select(State).where(State.slug == "sun"))
    state = result.scalar_one()
    state.brand_line = "Etwas ganz anderes."
    await db_session.commit()

    await seed_states(db_session, overwrite=True)
    await db_session.commit()

    await db_session.refresh(state)
    assert state.brand_line == "Feel the Sun."
