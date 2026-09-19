from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductStatus


async def sibling_map(db: AsyncSession, products: Iterable[Product]) -> dict[str, dict[str, str]]:
    """Serverseitige Entsprechung zu `productInState()` aus dem Click-Dummy.

    Liefert {product_group_id: {state_slug: product_slug}}, damit die
    Swatch-Reihe einer Produktkarte auf die Farbvariante desselben Designs im
    jeweiligen State verlinken kann. States ohne Variante bleiben im Template
    als abgeblendeter Punkt stehen - genau wie im Dummy.
    """
    group_ids = {p.product_group_id for p in products if p.product_group_id}
    if not group_ids:
        return {}

    result = await db.execute(
        select(Product)
        .options(selectinload(Product.state))
        .where(Product.product_group_id.in_(group_ids), Product.status == ProductStatus.ACTIVE)
    )
    siblings: dict[str, dict[str, str]] = {}
    for product in result.scalars().all():
        siblings.setdefault(product.product_group_id, {})[product.state.slug] = product.slug
    return siblings
