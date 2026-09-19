from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.catalog import sibling_map
from app.core.context import get_base_context
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.state import State

router = APIRouter(prefix="/shop")

# Headlines 1:1 aus CATEGORY_MAP des Click-Dummys, pro Kategorie des
# Datenmodells statt pro Navigationslabel.
CATEGORY_HEADLINES = {
    "Spa Robe": "ROBES MADE FOR MOMENTS IN BETWEEN.",
    "Spa Bag": "CARRY YOUR STATE WITH YOU.",
    "Towel": "WRAPPED IN YOUR STATE.",
    "Water Bottle": "SMALL PIECES, FULL STATE.",
}
ALL_PRODUCTS_HEADLINE = "THE FULL VAINEA WARDROBE."


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
    Filterwechsel liefert nur das Produktraster-Partial zurück.
    """
    query = (
        select(Product)
        .options(selectinload(Product.state), selectinload(Product.images), selectinload(Product.sizes))
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

    materials_result = await db.execute(
        select(Product.material).where(Product.status == ProductStatus.ACTIVE).distinct().order_by(Product.material)
    )
    materials = list(materials_result.scalars().all())

    # Bannerbild wie im Dummy: das Hero des States, zu dem das erste Produkt
    # der Auswahl gehört; ohne Treffer der erste State der Navigation.
    banner_state = products[0].state if products else base_context["nav_states"][0]

    context = {
        **base_context,
        "products": products,
        "siblings": await sibling_map(db, products),
        "materials": materials,
        "category_label": category or "All Products",
        "category_headline": CATEGORY_HEADLINES.get(category, ALL_PRODUCTS_HEADLINE),
        "banner_image_url": banner_state.hero_image_url,
        "active_category": category,
        "active_state": state,
        "active_material": material,
        "page_title": f"{category or 'Shop'} — VAINEA",
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/product_grid.html", context)
    return templates.TemplateResponse(request, "shop.html", context)
