from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cart import cart_count, get_cart_if_exists
from app.core.nav import get_nav_states
from app.core.users import current_user_optional
from app.db.session import get_db
from app.models.user import User


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
    return {"nav_states": nav_states, "cart_count": cart_count(cart), "current_user": user}
