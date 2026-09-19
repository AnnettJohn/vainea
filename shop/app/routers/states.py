from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_base_context
from app.core.seo import state_meta
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.state import State

router = APIRouter(prefix="/states")


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
        .options(selectinload(Product.state), selectinload(Product.images))
        .where(Product.state_id == state.id, Product.status == ProductStatus.ACTIVE)
        .order_by(Product.category)
    )
    products = products_result.scalars().all()

    page_title, page_description = state_meta(state)

    context = {
        **base_context,
        "state": state,
        "products": products,
        "page_title": page_title,
        "page_description": page_description,
        "canonical_url": str(request.url_for("state_detail", slug=state.slug)),
    }
    return templates.TemplateResponse(request, "state_detail.html", context)
