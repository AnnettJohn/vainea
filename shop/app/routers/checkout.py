from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cart import cart_subtotal, get_cart_if_exists
from app.core.checkout import (
    NON_EU_COUNTRIES,
    apply_discount_code,
    apply_payment_status,
    generate_order_number,
    get_order_by_number,
    get_shipping_zone,
    reserve_stock,
    resolve_shipping_choice,
    shipping_cost_for,
    shipping_countries,
)
from app.core.config import get_settings
from app.core.context import get_base_context
from app.core.mollie import create_mollie_payment, get_mollie_client, get_mollie_payment, mollie_configured
from app.core.templates import templates
from app.core.users import current_user_optional
from app.db.session import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User

settings = get_settings()

router = APIRouter(prefix="/checkout")

# Ablauf gemäß Pflichtenheft-Diagramm: Checkout bestätigt -> Order (pending)
# -> Mollie-Payment erstellen -> Redirect zu Mollie -> Webhook setzt "paid".
# Die Adress-Stufe legt die Order bereits an (inkl. fixierter Versand-/
# Rabattbeträge, Lagerbestand reserviert); die Zahlungs-Stufe erstellt erst
# dort das Mollie-Payment.


@router.get("/address")
async def checkout_address(
    request: Request,
    db: AsyncSession = Depends(get_db),
    base_context: dict = Depends(get_base_context),
    user: User | None = Depends(current_user_optional),
):
    cart = await get_cart_if_exists(request, db)
    subtotal = cart_subtotal(cart)
    default_country = "DE"
    zone = await get_shipping_zone(db, default_country)

    context = {
        **base_context,
        "cart": cart,
        "subtotal": subtotal,
        "zone": zone,
        "shipping_cost_for": shipping_cost_for,
        "shipping_countries": await shipping_countries(db),
        "is_non_eu": default_country in NON_EU_COUNTRIES,
        "form_data": {"shipping_country": default_country, "email": user.email if user else ""},
        "error": None,
        "page_title": "Checkout — Adresse",
    }
    return templates.TemplateResponse(request, "checkout_address.html", context)


@router.get("/shipping-methods")
async def shipping_methods_fragment(
    request: Request, db: AsyncSession = Depends(get_db), shipping_country: str = ""
):
    """HTMX-Fragment: Versandmethoden für das gerade eingegebene Land, live
    aktualisiert beim Tippen/Ändern auf dem Adressformular."""
    cart = await get_cart_if_exists(request, db)
    subtotal = cart_subtotal(cart)
    zone = await get_shipping_zone(db, shipping_country) if shipping_country else None
    context = {
        "zone": zone,
        "subtotal": subtotal,
        "shipping_cost_for": shipping_cost_for,
        "is_non_eu": shipping_country.upper() in NON_EU_COUNTRIES,
    }
    return templates.TemplateResponse(request, "partials/shipping_methods_options.html", context)


@router.post("/address")
async def submit_checkout_address(
    request: Request,
    db: AsyncSession = Depends(get_db),
    base_context: dict = Depends(get_base_context),
    user: User | None = Depends(current_user_optional),
    email: str = Form(...),
    shipping_name: str = Form(...),
    shipping_street: str = Form(...),
    shipping_zip: str = Form(...),
    shipping_city: str = Form(...),
    shipping_country: str = Form(...),
    shipping_rate_id: str = Form(""),
    billing_name: str = Form(""),
    billing_street: str = Form(""),
    billing_zip: str = Form(""),
    billing_city: str = Form(""),
    billing_country: str = Form(""),
    discount_code: str = Form(""),
):
    cart = await get_cart_if_exists(request, db)
    form_data = {
        "email": email,
        "shipping_name": shipping_name,
        "shipping_street": shipping_street,
        "shipping_zip": shipping_zip,
        "shipping_city": shipping_city,
        "shipping_country": shipping_country,
        "billing_name": billing_name,
        "billing_street": billing_street,
        "billing_zip": billing_zip,
        "billing_city": billing_city,
        "billing_country": billing_country,
        "discount_code": discount_code,
    }

    async def render_error(message: str, zone=None):
        context = {
            **base_context,
            "cart": cart,
            "subtotal": cart_subtotal(cart),
            "zone": zone,
            "shipping_cost_for": shipping_cost_for,
            "shipping_countries": await shipping_countries(db),
            "is_non_eu": shipping_country.upper() in NON_EU_COUNTRIES,
            "form_data": form_data,
            "error": message,
            "page_title": "Checkout — Adresse",
        }
        return templates.TemplateResponse(request, "checkout_address.html", context, status_code=400)

    if cart is None or not cart.items:
        return await render_error("Dein Warenkorb ist leer.")

    subtotal = cart_subtotal(cart)

    shipping_match = await resolve_shipping_choice(db, shipping_country, shipping_rate_id, subtotal)
    if shipping_match is None:
        return await render_error(
            "Wir versenden aktuell nur nach Deutschland, Österreich und in die Schweiz. "
            "Für andere Länder melde dich gern direkt bei uns."
        )
    zone, rate, shipping_cost = shipping_match

    discount = None
    discount_amount = Decimal("0.00")
    if discount_code.strip():
        discount, discount_amount, discount_error = await apply_discount_code(db, discount_code, subtotal)
        if discount_error:
            return await render_error(discount_error, zone=zone)

    total = subtotal - discount_amount + shipping_cost

    reservation_error = await reserve_stock(db, cart)
    if reservation_error:
        # reserve_stock rollt bei Fehlschlag nur seine eigene SAVEPOINT-
        # Transaktion zurück (siehe dort) - cart bleibt hier unverändert
        # nutzbar, kein erneutes Laden nötig.
        return await render_error(reservation_error, zone=zone)

    use_billing = billing_name.strip() and billing_street.strip() and billing_zip.strip() and billing_city.strip()

    order = Order(
        order_number=generate_order_number(),
        status=OrderStatus.PENDING,
        user_id=user.id if user is not None else None,
        guest_email=email,
        shipping_name=shipping_name,
        shipping_street=shipping_street,
        shipping_zip=shipping_zip,
        shipping_city=shipping_city,
        shipping_country=shipping_country.upper(),
        billing_name=billing_name if use_billing else shipping_name,
        billing_street=billing_street if use_billing else shipping_street,
        billing_zip=billing_zip if use_billing else shipping_zip,
        billing_city=billing_city if use_billing else shipping_city,
        billing_country=(billing_country.upper() if use_billing and billing_country else shipping_country.upper()),
        shipping_method_name=rate.method_name,
        shipping_cost=shipping_cost,
        discount_code=discount.code if discount else None,
        discount_amount=discount_amount,
        subtotal=subtotal,
        total=total,
        currency="EUR",
    )
    db.add(order)
    await db.flush()

    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                size=item.product_size.size,
                sku=item.product_size.sku,
                unit_price=item.product.price,
                quantity=item.quantity,
                line_total=item.product.price * item.quantity,
            )
        )
        await db.delete(item)

    await db.commit()

    return RedirectResponse(url=f"/checkout/payment/{order.order_number}", status_code=303)


@router.get("/payment/{order_number}")
async def checkout_payment(
    order_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    base_context: dict = Depends(get_base_context),
):
    order = await get_order_by_number(db, order_number)
    if order is None:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden.")

    if order.status != OrderStatus.PENDING:
        return RedirectResponse(url=f"/checkout/confirm?order={order.order_number}", status_code=303)

    if not mollie_configured():
        # Kein Mollie-API-Key hinterlegt (siehe .env) - Zahlungsanbindung ist
        # noch nicht konfiguriert. Bestellung bleibt "pending" (Lagerbestand
        # bleibt reserviert, bis der Server konfiguriert und bezahlt/storniert
        # wird - siehe README für diese bewusste Einschränkung im Dev-Modus).
        context = {**base_context, "order": order, "page_title": "Checkout — Zahlung"}
        return templates.TemplateResponse(request, "checkout_payment_pending.html", context)

    client = get_mollie_client()
    payment = await create_mollie_payment(
        client,
        {
            "amount": {"currency": order.currency, "value": f"{order.total:.2f}"},
            "description": f"VAINEA Bestellung {order.order_number}",
            "redirectUrl": str(request.url_for("checkout_confirm")) + f"?order={order.order_number}",
            "webhookUrl": settings.mollie_webhook_url,
            "metadata": {"order_number": order.order_number},
        },
    )
    order.mollie_payment_id = payment.id
    await db.commit()

    return RedirectResponse(url=payment.checkout_url, status_code=303)


@router.get("/confirm")
async def checkout_confirm(
    order: str, request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)
):
    order_obj = await get_order_by_number(db, order)
    if order_obj is None:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden.")

    context = {**base_context, "order": order_obj, "page_title": "Bestellbestätigung"}
    return templates.TemplateResponse(request, "checkout_confirm.html", context)


@router.post("/webhook")
async def mollie_webhook(id: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Mollie ruft diese Route nach jeder Statusänderung eines Payments auf.
    Nur der Webhook - nicht der Redirect nach /checkout/confirm - setzt den
    Bestellstatus verbindlich, da nur er eine tatsächlich abgeschlossene
    Zahlung belegt (siehe Pflichtenheft)."""
    if not mollie_configured():
        raise HTTPException(status_code=503, detail="Mollie ist nicht konfiguriert.")

    result = await db.execute(select(Order).options(selectinload(Order.items)).where(Order.mollie_payment_id == id))
    order = result.scalar_one_or_none()
    if order is None:
        return {"status": "ignored"}

    client = get_mollie_client()
    payment = await get_mollie_payment(client, id)

    await apply_payment_status(db, order, payment.status)
    await db.commit()

    return {"status": "ok"}
