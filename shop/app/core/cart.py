import uuid
from decimal import Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.product import Product

CART_COOKIE_NAME = "vainea_cart"
CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 30

_CART_OPTIONS = (
    selectinload(Cart.items).selectinload(CartItem.product).selectinload(Product.images),
    selectinload(Cart.items).selectinload(CartItem.product_size),
)


async def get_cart_if_exists(request: Request, db: AsyncSession) -> Cart | None:
    token = request.cookies.get(CART_COOKIE_NAME)
    if not token:
        return None
    result = await db.execute(select(Cart).options(*_CART_OPTIONS).where(Cart.session_token == token))
    return result.scalar_one_or_none()


async def get_cart_by_id(db: AsyncSession, cart_id: uuid.UUID) -> Cart:
    """Cart frisch aus der DB laden - `populate_existing` erzwingt das erneute
    Befüllen der eager-geladenen `items`-Collection, auch wenn dieses Cart-
    Objekt (z. B. aus get_or_create_cart) bereits mit einem älteren Stand in
    der Session-Identity-Map liegt (sonst bliebe ein gerade hinzugefügtes
    CartItem in `cart.items` unsichtbar, da es nicht über `cart.items.append`
    sondern per eigenem `db.add(CartItem(...))` angelegt wurde)."""
    result = await db.execute(
        select(Cart).options(*_CART_OPTIONS).where(Cart.id == cart_id).execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_or_create_cart(request: Request, db: AsyncSession) -> tuple[Cart, str | None]:
    """Gibt (Cart, neuer Cookie-Token oder None) zurück.

    Das Cookie wird bewusst nicht hier gesetzt: FastAPI verwirft Cookies auf
    einem separat injizierten Response-Objekt, sobald die Route selbst eine
    eigene Response (z. B. TemplateResponse) zurückgibt. Der Aufrufer muss
    das Token deshalb auf die tatsächlich zurückgegebene Response setzen.
    """
    cart = await get_cart_if_exists(request, db)
    if cart is not None:
        return cart, None

    token = uuid.uuid4().hex
    cart = Cart(session_token=token)
    db.add(cart)
    await db.flush()
    cart = await get_cart_by_id(db, cart.id)
    return cart, token


async def get_owned_cart_item(request: Request, db: AsyncSession, item_id: uuid.UUID) -> CartItem | None:
    """Cart-Item nur zurückgeben, wenn es zum Cart aus dem Cookie gehört
    (verhindert, dass fremde Cart-Items über die ID geraten/manipuliert werden)."""
    cart = await get_cart_if_exists(request, db)
    if cart is None:
        return None
    return next((item for item in cart.items if item.id == item_id), None)


def cart_count(cart: Cart | None) -> int:
    return sum(item.quantity for item in cart.items) if cart else 0


def cart_subtotal(cart: Cart | None) -> Decimal:
    if cart is None or not cart.items:
        return Decimal("0.00")
    return sum((item.product.price * item.quantity for item in cart.items), Decimal("0.00"))
