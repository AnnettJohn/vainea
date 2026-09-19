import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.email import send_order_confirmation_email
from app.models.cart import Cart
from app.models.discount import DiscountCode, DiscountType
from app.models.order import Order, OrderStatus
from app.models.product import ProductSize
from app.models.shipping import ShippingRate, ShippingZone

logger = logging.getLogger(__name__)


def generate_order_number() -> str:
    return f"VA-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


async def get_shipping_zone(db: AsyncSession, country_code: str) -> ShippingZone | None:
    """Zone für ein Länderkürzel ermitteln. Eine Zone mit leerer
    country_codes-Liste dient als Fallback ("Rest der Welt")."""
    if not country_code:
        return None
    country_code = country_code.upper()

    result = await db.execute(
        select(ShippingZone)
        .options(selectinload(ShippingZone.rates))
        .where(ShippingZone.country_codes.any(country_code))
    )
    zone = result.scalars().first()

    if zone is None:
        fallback_result = await db.execute(
            select(ShippingZone).options(selectinload(ShippingZone.rates)).where(ShippingZone.country_codes == [])
        )
        zone = fallback_result.scalars().first()

    return zone


def shipping_cost_for(zone: ShippingZone, rate: ShippingRate, subtotal: Decimal) -> Decimal:
    """Freigrenze anwenden - bezieht sich laut Pflichtenheft auf den
    Warenwert vor Rabatt."""
    if zone.free_shipping_threshold is not None and subtotal >= zone.free_shipping_threshold:
        return Decimal("0.00")
    return rate.price


async def resolve_shipping_choice(
    db: AsyncSession, country_code: str, rate_id: str | None, subtotal: Decimal
) -> tuple[ShippingZone, ShippingRate, Decimal] | None:
    """Versandzone + vom Kunden gewählte Methode auflösen (siehe
    GET /checkout/shipping-methods für die Auswahl-UI). Fällt auf die
    günstigste Methode der Zone zurück, wenn keine/eine ungültige Rate
    übergeben wurde (z. B. ohne JavaScript, oder Preismanipulationsversuch)."""
    zone = await get_shipping_zone(db, country_code)
    if zone is None or not zone.rates:
        return None

    rate = None
    if rate_id:
        rate = next((r for r in zone.rates if str(r.id) == str(rate_id)), None)
    if rate is None:
        rate = min(zone.rates, key=lambda r: r.price)

    return zone, rate, shipping_cost_for(zone, rate, subtotal)


async def apply_discount_code(
    db: AsyncSession, code: str, subtotal: Decimal
) -> tuple[DiscountCode | None, Decimal, str | None]:
    """Rabattcode validieren und den Rabattbetrag auf den Warenwert vor
    Versand berechnen. Gibt (Code oder None, Betrag, Fehlermeldung oder None)
    zurück."""
    normalized = code.strip().upper()
    result = await db.execute(select(DiscountCode).where(DiscountCode.code == normalized))
    discount = result.scalar_one_or_none()

    if discount is None:
        return None, Decimal("0.00"), "Rabattcode nicht gefunden."

    now = datetime.now(timezone.utc)
    if not discount.is_active or not (discount.valid_from <= now <= discount.valid_until):
        return None, Decimal("0.00"), "Rabattcode ist abgelaufen oder noch nicht gültig."

    if discount.min_order_value is not None and subtotal < discount.min_order_value:
        return None, Decimal("0.00"), f"Mindestbestellwert für diesen Code: €{discount.min_order_value:.2f}."

    if discount.usage_limit_total is not None and discount.usage_count >= discount.usage_limit_total:
        return None, Decimal("0.00"), "Rabattcode wurde bereits zu oft eingelöst."

    if discount.type == DiscountType.PERCENTAGE:
        amount = (subtotal * discount.value / Decimal("100")).quantize(Decimal("0.01"))
    else:
        amount = min(discount.value, subtotal)

    return discount, amount, None


class _InsufficientStock(Exception):
    def __init__(self, message: str):
        self.message = message


async def reserve_stock(db: AsyncSession, cart: Cart) -> str | None:
    """Lagerbestand für alle Cart-Positionen sperren (SELECT ... FOR UPDATE)
    und sofort abbuchen, sobald aus dem Warenkorb eine Order wird - nicht
    erst bei bestätigter Zahlung. So verkaufen sich zwei gleichzeitige
    Checkouts nicht dieselbe letzte Einheit. Gibt bei unzureichendem Bestand
    eine Fehlermeldung zurück, sonst None.

    Läuft in einer SAVEPOINT-Transaktion (begin_nested): schlägt die
    Reservierung fehl, rollt nur dieser Teil zurück. Ein session-weites
    db.rollback() würde stattdessen ALLE bereits in dieser Session geladenen
    Objekte "expiren" (z. B. die für den Seiten-Header schon geladenen
    States) und beim anschließenden Rendern der Fehlerseite zu einem
    Async-Lazy-Load-Fehler führen.

    Wird die Zahlung nicht abgeschlossen (failed/expired/canceled), gibt
    `release_stock` die Reservierung wieder frei (siehe apply_payment_status).
    """
    try:
        async with db.begin_nested():
            for item in cart.items:
                result = await db.execute(
                    select(ProductSize).where(ProductSize.id == item.product_size_id).with_for_update()
                )
                size = result.scalar_one()
                if item.quantity > size.stock:
                    raise _InsufficientStock(
                        f"„{item.product.name}“ ({size.size}) ist nicht mehr in ausreichender Menge verfügbar."
                    )
                size.stock -= item.quantity
    except _InsufficientStock as exc:
        return exc.message
    return None


async def release_stock(db: AsyncSession, order: Order) -> None:
    """Gegenstück zu reserve_stock: bei endgültig gescheiterter/abgebrochener
    Zahlung die zuvor reservierte Menge wieder freigeben."""
    for item in order.items:
        if item.product_id is None:
            continue
        size_result = await db.execute(
            select(ProductSize)
            .where(ProductSize.product_id == item.product_id, ProductSize.sku == item.sku)
            .with_for_update()
        )
        size = size_result.scalar_one_or_none()
        if size is not None:
            size.stock += item.quantity


async def get_order_by_number(db: AsyncSession, order_number: str) -> Order | None:
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.order_number == order_number)
    )
    return result.scalar_one_or_none()


async def apply_payment_status(db: AsyncSession, order: Order, mollie_status: str) -> None:
    """Reine Statuslogik, getrennt vom Mollie-API-Aufruf, damit sie ohne
    Netzwerkzugriff getestet werden kann. `mollie_status` ist payment.status
    aus der Mollie-API ("paid", "failed", "canceled", "expired", "open", ...).

    Der Lagerbestand wurde bereits bei Order-Anlage reserviert/abgebucht
    (siehe reserve_stock); bei "paid" ist daher nichts mehr zu tun, bei
    endgültigem Scheitern wird er wieder freigegeben.
    """
    if order.status != OrderStatus.PENDING:
        return  # bereits final, Webhook kann mehrfach zugestellt werden

    if mollie_status == "paid":
        order.status = OrderStatus.PAID
        order.paid_at = datetime.now(timezone.utc)

        if order.discount_code:
            discount_result = await db.execute(select(DiscountCode).where(DiscountCode.code == order.discount_code))
            discount = discount_result.scalar_one_or_none()
            if discount is not None:
                discount.usage_count += 1

        try:
            await send_order_confirmation_email(order)
        except Exception:
            # Der Zahlungsstatus ist die verbindliche Wahrheit und muss auch
            # committet werden, wenn der Mailversand (z. B. SMTP down)
            # fehlschlägt - dann fehlt nur die Bestätigungsmail, nicht die
            # bezahlte Bestellung selbst.
            logger.exception("Bestellbestätigung für %s konnte nicht versendet werden", order.order_number)

    elif mollie_status in ("failed", "expired"):
        order.status = OrderStatus.FAILED
        await release_stock(db, order)
    elif mollie_status == "canceled":
        order.status = OrderStatus.CANCELED
        await release_stock(db, order)
