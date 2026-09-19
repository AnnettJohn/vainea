import email as email_lib

from sqlalchemy import select

from app.core.checkout import apply_payment_status, get_order_by_number
from app.models.product import Product, ProductSize

VALID_ADDRESS = {
    "email": "kundin@example.com",
    "shipping_name": "Erika Musterfrau",
    "shipping_street": "Hauptstr. 5",
    "shipping_zip": "10115",
    "shipping_city": "Berlin",
    "shipping_country": "DE",
}


def _decoded_body(raw_message: str) -> str:
    """MIMEText kodiert utf-8-Teile standardmäßig als base64 - für lesbare
    Assertions in Tests hier sauber mit dem email-Modul dekodieren statt
    naiv auf dem rohen (base64-)Text zu suchen."""
    message = email_lib.message_from_string(raw_message)
    parts = []
    for part in message.walk():
        if part.get_content_maintype() == "text":
            payload = part.get_payload(decode=True)
            if payload:
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    return "\n".join(parts)


async def _get_size(db_session, slug: str, size: str) -> ProductSize:
    product = (await db_session.execute(select(Product).where(Product.slug == slug))).scalar_one()
    return (
        await db_session.execute(
            select(ProductSize).where(ProductSize.product_id == product.id, ProductSize.size == size)
        )
    ).scalar_one()


async def _create_pending_order(client, db_session) -> str:
    size = await _get_size(db_session, "sun-mono-robe", "M")
    await client.post("/cart/items", data={"product_size_id": str(size.id), "quantity": "1"})
    response = await client.post("/checkout/address", data=VALID_ADDRESS, follow_redirects=False)
    return response.headers["location"].split("/checkout/payment/")[1]


async def test_order_confirmation_email_sent_on_payment(client, db_session, smtp_messages):
    order_number = await _create_pending_order(client, db_session)
    order = await get_order_by_number(db_session, order_number)

    await apply_payment_status(db_session, order, "paid")
    await db_session.commit()

    assert len(smtp_messages) == 1
    message = smtp_messages[0]
    assert message["mail_from"] == "no-reply@vainea.de"
    assert message["rcpt_tos"] == ["kundin@example.com"]
    assert order_number in message["content"]  # steht im Subject-Header (ASCII, unkodiert)

    body = _decoded_body(message["content"])
    assert "Sun Mono Robe" in body
    assert "189.00" in body
    assert "Erika Musterfrau" in body


async def test_no_email_sent_for_expired_payment(client, db_session, smtp_messages):
    order_number = await _create_pending_order(client, db_session)
    order = await get_order_by_number(db_session, order_number)

    await apply_payment_status(db_session, order, "expired")
    await db_session.commit()

    assert smtp_messages == []


async def test_payment_still_confirmed_if_email_delivery_fails(client, db_session, smtp_messages, monkeypatch):
    from app.core import email as email_module

    async def _broken_send(*args, **kwargs):
        raise RuntimeError("SMTP nicht erreichbar")

    monkeypatch.setattr(email_module, "send_email", _broken_send)

    order_number = await _create_pending_order(client, db_session)
    order = await get_order_by_number(db_session, order_number)

    await apply_payment_status(db_session, order, "paid")
    await db_session.commit()

    order = await get_order_by_number(db_session, order_number)
    assert order.status.value == "paid"
    assert smtp_messages == []
