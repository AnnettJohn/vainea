from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.checkout import apply_payment_status, get_order_by_number
from app.models.discount import DiscountCode, DiscountType
from app.models.order import OrderStatus
from app.models.product import Product, ProductSize


def approx(value):
    """Decimal-freundlicher Vergleichshelfer: Order-Felder sind
    decimal.Decimal, das rechts vom `==` steht braucht float für pytest.approx."""
    return pytest.approx(float(value), abs=0.01)


async def _get_size(db_session, slug: str, size: str) -> ProductSize:
    product = (await db_session.execute(select(Product).where(Product.slug == slug))).scalar_one()
    return (
        await db_session.execute(
            select(ProductSize).where(ProductSize.product_id == product.id, ProductSize.size == size)
        )
    ).scalar_one()


async def _add_to_cart(client, size_id: str, quantity: int = 1):
    return await client.post("/cart/items", data={"product_size_id": size_id, "quantity": str(quantity)})


VALID_ADDRESS = {
    "email": "kundin@example.com",
    "shipping_name": "Erika Musterfrau",
    "shipping_street": "Hauptstr. 5",
    "shipping_zip": "10115",
    "shipping_city": "Berlin",
    "shipping_country": "DE",
}


async def test_shipping_methods_fragment_for_germany(client):
    response = await client.get("/checkout/shipping-methods", params={"shipping_country": "DE"})
    assert response.status_code == 200
    assert "Standard" in response.text
    assert "4.95" in response.text


async def test_checkout_happy_path_reserves_stock_and_creates_order(client, db_session):
    size = await _get_size(db_session, "sun-mono-robe", "M")
    stock_before = size.stock
    await _add_to_cart(client, str(size.id), quantity=2)

    response = await client.post("/checkout/address", data=VALID_ADDRESS, follow_redirects=False)
    assert response.status_code == 303
    order_number = response.headers["location"].split("/checkout/payment/")[1]

    order = await get_order_by_number(db_session, order_number)
    assert order is not None
    assert order.status == OrderStatus.PENDING
    assert float(order.subtotal) == approx(378)  # 2 x 189.00
    assert float(order.shipping_cost) == approx(0)  # 378 >= 120 Freigrenze
    assert float(order.total) == approx(378)

    await db_session.refresh(size)
    assert size.stock == stock_before - 2  # sofort reserviert, nicht erst bei Zahlung

    # Warenkorb wurde geleert
    cart_page = await client.get("/cart")
    assert "Warenkorb ist leer" in cart_page.text

    # Ohne MOLLIE_API_KEY zeigt die Zahlungsseite den Konfigurationshinweis
    payment_page = await client.get(f"/checkout/payment/{order_number}")
    assert payment_page.status_code == 200
    assert "noch nicht konfiguriert" in payment_page.text


async def test_checkout_with_empty_cart_shows_error(client):
    response = await client.post("/checkout/address", data=VALID_ADDRESS)
    assert response.status_code == 400
    assert "Warenkorb ist leer" in response.text


async def test_checkout_rejects_country_outside_dach(client, db_session):
    """VAINEA liefert nur nach DE/AT/CH. Früher fing eine Zone mit leerer
    country_codes-Liste jedes andere Land ab - genau das darf nicht mehr
    passieren, sonst entstehen Bestellungen, die nicht erfüllbar sind."""
    size = await _get_size(db_session, "sun-mono-robe", "M")
    await _add_to_cart(client, str(size.id), quantity=1)

    data = {**VALID_ADDRESS, "shipping_country": "US"}
    response = await client.post("/checkout/address", data=data, follow_redirects=False)

    assert response.status_code == 400
    assert "nur nach Deutschland, Österreich und in die Schweiz" in response.text


async def test_checkout_to_switzerland_uses_own_zone(client, db_session):
    """Die Schweiz hat eine eigene Zone (Ausfuhr, kein EU-Zollgebiet) und
    deshalb weder die deutsche Freigrenze noch den österreichischen Tarif."""
    size = await _get_size(db_session, "sun-mono-robe", "M")
    await _add_to_cart(client, str(size.id), quantity=1)

    data = {**VALID_ADDRESS, "shipping_country": "CH"}
    response = await client.post("/checkout/address", data=data, follow_redirects=False)

    assert response.status_code == 303
    order_number = response.headers["location"].split("/checkout/payment/")[1]
    order = await get_order_by_number(db_session, order_number)
    assert order.shipping_country == "CH"
    assert float(order.shipping_cost) == approx(14.95)


async def test_checkout_shows_customs_notice_for_switzerland(client):
    """Pflichthinweis bei Ausfuhr: Zoll und Einfuhrsteuer sind nicht im Preis."""
    response = await client.get("/checkout/shipping-methods?shipping_country=CH")
    assert response.status_code == 200
    assert "Einfuhrumsatzsteuer" in response.text

    response = await client.get("/checkout/shipping-methods?shipping_country=DE")
    assert "Einfuhrumsatzsteuer" not in response.text


async def test_checkout_rejects_insufficient_stock(client, db_session):
    size = await _get_size(db_session, "sun-mono-robe", "L")
    size.stock = 1
    await db_session.commit()

    await _add_to_cart(client, str(size.id), quantity=1)
    # Zwischen Warenkorb-Befüllung und Checkout kauft "jemand anders" die letzte Einheit
    size.stock = 0
    await db_session.commit()

    response = await client.post("/checkout/address", data=VALID_ADDRESS)

    assert response.status_code == 400
    assert "nicht mehr in ausreichender Menge verfügbar" in response.text

    await db_session.refresh(size)
    assert size.stock == 0  # keine Doppel-Abbuchung, Reservierung wurde zurückgerollt


async def test_checkout_with_invalid_discount_code_shows_error(client, db_session):
    size = await _get_size(db_session, "sun-mono-robe", "M")
    await _add_to_cart(client, str(size.id), quantity=1)

    data = {**VALID_ADDRESS, "discount_code": "DOES-NOT-EXIST"}
    response = await client.post("/checkout/address", data=data)

    assert response.status_code == 400
    assert "Rabattcode nicht gefunden" in response.text


async def test_checkout_applies_valid_percentage_discount(client, db_session):
    db_session.add(
        DiscountCode(
            code="WELCOME10",
            type=DiscountType.PERCENTAGE,
            value="10.00",
            valid_from=datetime.now(timezone.utc) - timedelta(days=1),
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await db_session.commit()

    size = await _get_size(db_session, "sun-mono-robe", "M")
    await _add_to_cart(client, str(size.id), quantity=1)

    data = {**VALID_ADDRESS, "discount_code": "welcome10"}
    response = await client.post("/checkout/address", data=data, follow_redirects=False)
    assert response.status_code == 303

    order_number = response.headers["location"].split("/checkout/payment/")[1]
    order = await get_order_by_number(db_session, order_number)

    assert order.discount_code == "WELCOME10"
    assert float(order.discount_amount) == approx(18.90)  # 10% von 189.00
    # Freigrenze bezieht sich auf den Warenwert VOR Rabatt (189 >= 120)
    assert float(order.shipping_cost) == approx(0)
    assert float(order.total) == approx(189 - 18.90)


async def test_webhook_payment_status_paid_is_idempotent(client, db_session):
    size = await _get_size(db_session, "sun-mono-robe", "M")
    await _add_to_cart(client, str(size.id), quantity=1)
    response = await client.post("/checkout/address", data=VALID_ADDRESS, follow_redirects=False)
    order_number = response.headers["location"].split("/checkout/payment/")[1]

    order = await get_order_by_number(db_session, order_number)
    await apply_payment_status(db_session, order, "paid")
    await db_session.commit()

    order = await get_order_by_number(db_session, order_number)
    assert order.status == OrderStatus.PAID
    assert order.paid_at is not None

    # Zweiter Aufruf (Mollie kann denselben Webhook mehrfach zustellen) darf nichts mehr ändern
    paid_at_first = order.paid_at
    await apply_payment_status(db_session, order, "paid")
    await db_session.commit()
    order = await get_order_by_number(db_session, order_number)
    assert order.paid_at == paid_at_first


async def test_webhook_payment_status_expired_releases_stock(client, db_session):
    size = await _get_size(db_session, "sun-mono-robe", "M")
    stock_before = size.stock
    await _add_to_cart(client, str(size.id), quantity=2)
    response = await client.post("/checkout/address", data=VALID_ADDRESS, follow_redirects=False)
    order_number = response.headers["location"].split("/checkout/payment/")[1]

    await db_session.refresh(size)
    assert size.stock == stock_before - 2

    order = await get_order_by_number(db_session, order_number)
    await apply_payment_status(db_session, order, "expired")
    await db_session.commit()

    order = await get_order_by_number(db_session, order_number)
    assert order.status == OrderStatus.FAILED

    await db_session.refresh(size)
    assert size.stock == stock_before  # Reservierung wurde freigegeben
