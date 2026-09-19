from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cart import cart_count, get_cart_if_exists
from app.core.nav import get_nav_states
from app.core.users import current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.models.wishlist import WishlistItem


async def get_base_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(current_user_optional),
) -> dict:
    """Kontext, den jede Seite für Header/Navigation braucht (States-Nav,
    Warenkorb-Badge, Login-Status). Als FastAPI-Dependency verwendbar:

        base_context: dict = Depends(get_base_context)

    Erzeugt dabei keinen Cart, falls noch keiner existiert, und erzwingt
    keinen Login (current_user ist None für Gäste)."""
    nav_states = await get_nav_states(db)
    cart = await get_cart_if_exists(request, db)

    # Herz-Button auf jeder Produktkarte (wish-btn im Click-Dummy) braucht den
    # aktuellen Merkzettel; für Gäste bleibt er leer statt einer zweiten Abfrage.
    wishlist_ids: set = set()
    if user is not None:
        result = await db.execute(select(WishlistItem.product_id).where(WishlistItem.user_id == user.id))
        wishlist_ids = set(result.scalars().all())

    return {
        "nav_states": nav_states,
        "cart_count": cart_count(cart),
        "current_user": user,
        "wishlist_ids": wishlist_ids,
    }
