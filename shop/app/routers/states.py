from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.catalog import sibling_map
from app.core.context import get_base_context
from app.core.seo import state_meta
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.state import State

router = APIRouter(prefix="/states")

# articlesForState()/piecesForState() des Click-Dummys: "The Edit" zeigt die
# Robes nach Schnitt-Variante, "State Pieces" die Accessoires in fester Folge.
VARIANT_ORDER = ["mono", "block", "stripe"]
PIECE_CATEGORY_ORDER = ["Towel", "Water Bottle", "Spa Bag"]


@router.get("/{slug}")
async def state_detail(
    slug: str, request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)
):
    result = await db.execute(select(State).where(State.slug == slug))
    state = result.scalar_one_or_none()
    if state is None:
        raise HTTPException(status_code=404, detail="State not found")

    products_result = await db.execute(
        select(Product)
        .options(selectinload(Product.state), selectinload(Product.images), selectinload(Product.sizes))
        .where(Product.state_id == state.id, Product.status == ProductStatus.ACTIVE)
        .order_by(Product.name)
    )
    products = products_result.scalars().all()

    articles = sorted(
        (p for p in products if p.variant),
        key=lambda p: VARIANT_ORDER.index(p.variant) if p.variant in VARIANT_ORDER else len(VARIANT_ORDER),
    )
    pieces = sorted(
        (p for p in products if p.category in PIECE_CATEGORY_ORDER),
        key=lambda p: PIECE_CATEGORY_ORDER.index(p.category),
    )

    page_title, page_description = state_meta(state)

    context = {
        **base_context,
        "state": state,
        "products": products,
        "articles": articles,
        "pieces": pieces,
        "siblings": await sibling_map(db, products),
        "page_title": page_title,
        "page_description": page_description,
        "canonical_url": str(request.url_for("state_detail", slug=state.slug)),
    }
    return templates.TemplateResponse(request, "state_detail.html", context)
