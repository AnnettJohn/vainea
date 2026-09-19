from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_base_context
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.state import State

router = APIRouter(prefix="/shop")


@router.get("")
async def shop_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    base_context: dict = Depends(get_base_context),
    category: str | None = None,
    state: str | None = None,
    material: str | None = None,
):
    """Produktkatalog mit Filterung per Query-Parameter (category/state/material).

    Rendert bei normalem Aufruf die volle Seite; ein per HTMX ausgelöster
    Filterwechsel kann dieselbe Route mit HX-Request-Header nutzen und
    zukünftig nur das Produktraster-Partial zurückliefern.
    """
    query = (
        select(Product)
        .options(selectinload(Product.state), selectinload(Product.images))
        .where(Product.status == ProductStatus.ACTIVE)
    )
    if category:
        query = query.where(Product.category == category)
    if material:
        query = query.where(Product.material == material)
    if state:
        state_result = await db.execute(select(State.id).where(State.slug == state))
        state_id = state_result.scalar_one_or_none()
        query = query.where(Product.state_id == state_id)

    result = await db.execute(query.order_by(Product.name))
    products = result.scalars().all()

    context = {
        **base_context,
        "products": products,
        "active_category": category,
        "active_state": state,
        "active_material": material,
        "page_title": "Shop — VAINEA",
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/product_grid.html", context)
    return templates.TemplateResponse(request, "shop.html", context)
