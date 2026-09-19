from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.catalog import sibling_map
from app.core.context import get_base_context
from app.core.seo import product_json_ld, product_meta
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.wishlist import WishlistItem

router = APIRouter(prefix="/products")

# Accordion-Copy 1:1 aus DETAIL_COPY_BY_CATEGORY / CARE_COPY_BY_CATEGORY des
# Click-Dummys. Kategoriebezogen und daher hier als Konstante statt als
# Produktfeld - das Pflichtenheft sieht dafuer kein eigenes Feld vor.
DETAIL_COPY_BY_CATEGORY = {
    "Spa Robe": "Shawl collar, interior tie belt, two front pockets, embroidered VAINEA state tab at the cuff.",
    "Spa Bag": "Water-resistant lining, adjustable crossbody strap, interior zip pocket for valuables.",
    "Water Bottle": "Double-wall insulated — cold for 24h, hot for 12h. Leak-proof cap, wide mouth for ice.",
    "Towel": "500gsm combed cotton, ultra-absorbent weave, colorfast state-dye that holds after washing.",
}
CARE_COPY_BY_CATEGORY = {
    "Spa Robe": "Machine wash cold with like colors. Tumble dry low. Do not bleach or iron directly on print.",
    "Spa Bag": "Wipe clean with a damp cloth. Do not machine wash.",
    "Water Bottle": "Hand wash recommended. Lid is top-rack dishwasher safe.",
    "Towel": "Machine wash warm. Tumble dry low. Avoid fabric softener to preserve absorbency.",
}


def accordion_for(product: Product) -> list[tuple[str, str]]:
    """accordionContentFor() aus dem Click-Dummy; \"Details\" nutzt die im Admin
    gepflegte Produktbeschreibung, falls vorhanden."""
    detail = product.description or DETAIL_COPY_BY_CATEGORY.get(
        product.category, "Thoughtfully made, finished with the VAINEA state tab."
    )
    care = CARE_COPY_BY_CATEGORY.get(product.category, "See care label for full instructions.")
    return [
        ("Material", f"{product.material}, selected for comfort and everyday durability. Softens with every wash."),
        ("Fit", "True to size with a relaxed silhouette. Between sizes? We recommend sizing up for a looser drape."),
        ("Details", detail),
        ("Care", care),
        ("Shipping", "Free shipping on orders over €120. Dispatched within 1–2 business days from our EU warehouse."),
        ("Returns", "Free returns within 30 days. Items must be unworn with tags attached."),
    ]


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

    # pdpCrossSellHtml(): bis zu drei weitere Produkte desselben States.
    cross_result = await db.execute(
        select(Product)
        .options(selectinload(Product.state), selectinload(Product.images), selectinload(Product.sizes))
        .where(
            Product.state_id == product.state_id,
            Product.id != product.id,
            Product.status == ProductStatus.ACTIVE,
        )
        .order_by(Product.name)
        .limit(3)
    )
    cross_sell = cross_result.scalars().all()

    page_title, page_description = product_meta(product)

    context = {
        **base_context,
        "product": product,
        "state_variants": state_variants,
        "is_wishlisted": is_wishlisted,
        "cross_sell": cross_sell,
        "siblings": await sibling_map(db, cross_sell),
        "accordion": accordion_for(product),
        "page_title": page_title,
        "page_description": page_description,
        "product_json_ld": product_json_ld(product, request),
        "canonical_url": str(request.url_for("product_detail", slug=product.slug)),
    }
    return templates.TemplateResponse(request, "product_detail.html", context)
