from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_base_context
from app.core.seo import product_json_ld, product_meta
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product
from app.models.wishlist import WishlistItem

router = APIRouter(prefix="/products")


@router.get("/{slug}")
async def product_detail(
    slug: str, request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)
):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.sizes), selectinload(Product.state))
        .where(Product.slug == slug)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    state_variants = []
    if product.product_group_id:
        siblings_result = await db.execute(
            select(Product)
            .options(selectinload(Product.state))
            .where(Product.product_group_id == product.product_group_id)
        )
        state_variants = siblings_result.scalars().all()

    is_wishlisted = False
    user = base_context["current_user"]
    if user is not None:
        wish_result = await db.execute(
            select(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product.id)
        )
        is_wishlisted = wish_result.scalar_one_or_none() is not None

    page_title, page_description = product_meta(product)

    context = {
        **base_context,
        "product": product,
        "state_variants": state_variants,
        "is_wishlisted": is_wishlisted,
        "page_title": page_title,
        "page_description": page_description,
        "product_json_ld": product_json_ld(product, request),
        "canonical_url": str(request.url_for("product_detail", slug=product.slug)),
    }
    return templates.TemplateResponse(request, "product_detail.html", context)
