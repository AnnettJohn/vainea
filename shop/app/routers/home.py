from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import get_base_context
from app.core.templates import templates
from app.db.session import get_db
from app.models.product import Product, ProductStatus

router = APIRouter()

# 1:1 aus dem Click-Dummy (index.html) übernommene Kuratierung/Copy für die
# Homepage-Sektionen - keine im Datenmodell hinterlegten Auswahllisten,
# daher hier als Konstanten statt eines Admin-Feldes.

# featuredProductsHtml(): FEATURED_IDS = die vier Mono-Robes, eine je State.
FEATURED_PRODUCT_GROUP = "robe-mono"

# accessoriesHtml(): ACCESSORY_IDS = Spa Bag/Water Bottle/Towel, eine State-Auswahl.
ACCESSORY_SLUGS = ["horizon-spa-bag", "citrus-light-bottle", "aperitivo-terry-towel"]

# shopTheLookHtml() + HOTSPOTS: Produkt-Slug -> (x%, y%) Position auf shopthelook.png.
LOOK_HOTSPOTS = [
    ("aperitivo-spa-bag", 24, 60),
    ("aperitivo-terry-towel", 19, 83),
    ("aperitivo-water-bottle", 80, 64),
]

# detailStoryHtml(): DETAILS = (Label, State-Slug) für die Deko-Kachelreihe.
DETAIL_TILES = [
    ("Frottee", "sun"),
    ("Zipper", "sea"),
    ("Kordeln", "dream"),
    ("Ösen", "light"),
    ("Bordüre", "sea"),
    ("Logo", "sun"),
    ("Kapuzenfutter", "dream"),
    ("Stoffstruktur", "light"),
]

# findYourStateHtml(): MOODS = Label -> State-Slug für den Quiz.
QUIZ_MOODS = [
    ("ENERGETIC", "sun"),
    ("FREE", "sea"),
    ("CALM", "dream"),
    ("BRIGHT", "light"),
]

_PRODUCT_OPTIONS = (selectinload(Product.images), selectinload(Product.state))


async def _products_by_slugs(db: AsyncSession, slugs: list[str]) -> dict[str, Product]:
    result = await db.execute(select(Product).options(*_PRODUCT_OPTIONS).where(Product.slug.in_(slugs)))
    return {p.slug: p for p in result.scalars().all()}


@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db), base_context: dict = Depends(get_base_context)):
    states = base_context["nav_states"]

    featured_result = await db.execute(
        select(Product)
        .options(*_PRODUCT_OPTIONS)
        .where(Product.product_group_id == FEATURED_PRODUCT_GROUP, Product.status == ProductStatus.ACTIVE)
        .order_by(Product.state_id)
    )
    featured_products = featured_result.scalars().all()

    accessory_by_slug = await _products_by_slugs(db, ACCESSORY_SLUGS)
    accessory_products = [accessory_by_slug[s] for s in ACCESSORY_SLUGS if s in accessory_by_slug]

    look_by_slug = await _products_by_slugs(db, [slug for slug, _, _ in LOOK_HOTSPOTS])
    look_hotspots = [
        {"product": look_by_slug[slug], "x": x, "y": y}
        for slug, x, y in LOOK_HOTSPOTS
        if slug in look_by_slug
    ]

    quiz_products_by_state: dict[str, list[Product]] = {}
    for state in states:
        result = await db.execute(
            select(Product)
            .options(*_PRODUCT_OPTIONS)
            .where(Product.state_id == state.id, Product.status == ProductStatus.ACTIVE)
            .order_by(Product.is_bestseller.desc(), Product.name)
            .limit(3)
        )
        quiz_products_by_state[state.slug] = result.scalars().all()

    states_by_slug = {s.slug: s for s in states}

    context = {
        **base_context,
        "states": states,
        "nav_states": states,  # bereits geladen, keine zweite Abfrage nötig
        "states_by_slug": states_by_slug,
        "featured_products": featured_products,
        "accessory_products": accessory_products,
        "look_hotspots": look_hotspots,
        "detail_tiles": DETAIL_TILES,
        "quiz_moods": QUIZ_MOODS,
        "quiz_products_by_state": quiz_products_by_state,
        "page_title": "VAINEA — Wear Your State of Mind",
    }
    return templates.TemplateResponse(request, "home.html", context)
