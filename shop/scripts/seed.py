"""Überführt STATES und PRODUCTS aus dem Click-Dummy (index.html) in die DB.

Idempotent: vorhandene States/Products werden anhand ihres Slugs erkannt und
aktualisiert statt dupliziert. Ausführen mit:

    uv run python -m scripts.seed
"""

import asyncio
import re
import uuid

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.product import Product, ProductImage, ProductSize, ProductStatus
from app.models.shipping import ShippingRate, ShippingZone
from app.models.state import State


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


# 1:1 aus STATES in index.html (Zeilen 757-766), snake_case-Felder.
STATES = [
    {
        "slug": "sun",
        "num": "01",
        "name": "SUN",
        "hex_color": "#FF5B2E",
        "mood_text": "Energy · Warmth · Escape",
        "brand_line": "Feel the Sun.",
        "hero_image_url": "/static/images/hero-sun.jpg",
        "hero_image_position": "50% 8%",
        "circle_image_url": "/static/images/circle-sun.png",
        "story_text": (
            "Der erste Kaffee draußen, Sonnenlicht auf der Haut, ein Nachmittag am "
            "Pool — der Moment, wenn der Tag noch alles verspricht."
        ),
        "sort_order": 0,
    },
    {
        "slug": "sea",
        "num": "02",
        "name": "SEA",
        "hex_color": "#0780D5",
        "mood_text": "Freedom · Freshness · Clarity",
        "brand_line": "Dive into Blue.",
        "hero_image_url": "/static/images/hero-sea.jpg",
        "hero_image_position": "50% 18%",
        "circle_image_url": "/static/images/circle-sea.png",
        "story_text": (
            "Das erste Eintauchen ins Wasser, Salz auf der Haut, ein klarer Horizont "
            "— für einen Moment ganz woanders sein."
        ),
        "sort_order": 1,
    },
    {
        "slug": "dream",
        "num": "03",
        "name": "DREAM",
        "hex_color": "#CEC8F4",
        "mood_text": "Calm · Softness · Restore",
        "brand_line": "Stay Soft.",
        "hero_image_url": "/static/images/hero-dream.jpg",
        "hero_image_position": "50% 15%",
        "circle_image_url": "/static/images/circle-dream.png",
        "story_text": (
            "Warmer Dampf, weiche Handtücher, gedimmtes Licht — dieser Zustand "
            "zwischen Wachsein und Loslassen."
        ),
        "sort_order": 2,
    },
    {
        "slug": "light",
        "num": "04",
        "name": "LIGHT",
        "hex_color": "#DFFF35",
        "mood_text": "Joy · Optimism · Glow",
        "brand_line": "Choose the Light.",
        "hero_image_url": "/static/images/hero-light.jpg",
        "hero_image_position": "50% 15%",
        "circle_image_url": "/static/images/circle-light.png",
        "story_text": (
            "Morgenlicht, frische Luft, ein spontaner Plan — das Gefühl, dass heute "
            "ein guter Tag wird."
        ),
        "sort_order": 3,
    },
]

# 1:1 aus PRODUCTS in index.html (Zeilen 778-801). state ist der State-Slug,
# img (falls vorhanden) der Dateiname aus dem alten images/-Ordner.
PRODUCTS = [
    {"name": "Sun Mono Robe", "category": "Spa Robe", "state": "sun", "price": "189.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": True, "variant": "mono", "img": "robe_mono_front_sun.png"},
    {"name": "Sea Mono Robe", "category": "Spa Robe", "state": "sea", "price": "189.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": "mono", "img": None},
    {"name": "Dream Mono Robe", "category": "Spa Robe", "state": "dream", "price": "189.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "mono", "img": None},
    {"name": "Light Mono Robe", "category": "Spa Robe", "state": "light", "price": "189.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "mono", "img": None},
    {"name": "Horizon Spa Bag", "category": "Spa Bag", "state": "sea", "price": "69.00", "sizes": ["One Size"], "material": "Canvas", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bag_sea.png"},
    {"name": "Citrus Light Bottle", "category": "Water Bottle", "state": "light", "price": "45.00", "sizes": ["500ml"], "material": "Edelstahl", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bottle_light.png"},
    {"name": "Aperitivo Terry Towel", "category": "Towel", "state": "sun", "price": "49.00", "sizes": ["One Size"], "material": "Frottee", "is_new": False, "bestseller": True, "variant": None, "img": "piece_towel_sun.png"},
    {"name": "Sun Block Robe", "category": "Spa Robe", "state": "sun", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "block", "img": "robe_block_total_sun.png"},
    {"name": "Sun Stripe Robe", "category": "Spa Robe", "state": "sun", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": "stripe", "img": "robe_stripe_total_sun.png"},
    {"name": "Sea Block Robe", "category": "Spa Robe", "state": "sea", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "block", "img": None},
    {"name": "Sea Stripe Robe", "category": "Spa Robe", "state": "sea", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": "stripe", "img": None},
    {"name": "Dream Block Robe", "category": "Spa Robe", "state": "dream", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "block", "img": None},
    {"name": "Dream Stripe Robe", "category": "Spa Robe", "state": "dream", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": "stripe", "img": None},
    {"name": "Light Block Robe", "category": "Spa Robe", "state": "light", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": "block", "img": None},
    {"name": "Light Stripe Robe", "category": "Spa Robe", "state": "light", "price": "199.00", "sizes": ["XS", "S", "M", "L", "XL"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": "stripe", "img": None},
    {"name": "Horizon Terry Towel", "category": "Towel", "state": "sea", "price": "49.00", "sizes": ["One Size"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": None, "img": "piece_towel_sea.png"},
    {"name": "Lavender Dream Towel", "category": "Towel", "state": "dream", "price": "49.00", "sizes": ["One Size"], "material": "Frottee", "is_new": True, "bestseller": False, "variant": None, "img": "piece_towel_dream.png"},
    {"name": "Citrus Light Towel", "category": "Towel", "state": "light", "price": "49.00", "sizes": ["One Size"], "material": "Frottee", "is_new": False, "bestseller": False, "variant": None, "img": "piece_towel_light.png"},
    {"name": "Aperitivo Water Bottle", "category": "Water Bottle", "state": "sun", "price": "45.00", "sizes": ["500ml"], "material": "Edelstahl", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bottle_sun.png"},
    {"name": "Horizon Water Bottle", "category": "Water Bottle", "state": "sea", "price": "45.00", "sizes": ["500ml"], "material": "Edelstahl", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bottle_sea.png"},
    {"name": "Lavender Dream Bottle", "category": "Water Bottle", "state": "dream", "price": "45.00", "sizes": ["500ml"], "material": "Edelstahl", "is_new": True, "bestseller": False, "variant": None, "img": "piece_bottle_dream.png"},
    {"name": "Aperitivo Spa Bag", "category": "Spa Bag", "state": "sun", "price": "69.00", "sizes": ["One Size"], "material": "Canvas", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bag_sun.png"},
    {"name": "Lavender Dream Bag", "category": "Spa Bag", "state": "dream", "price": "69.00", "sizes": ["One Size"], "material": "Canvas", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bag_dream.png"},
    {"name": "Citrus Light Bag", "category": "Spa Bag", "state": "light", "price": "69.00", "sizes": ["One Size"], "material": "Canvas", "is_new": False, "bestseller": False, "variant": None, "img": "piece_bag_light.png"},
]

# Placeholder-Lagerbestand je Größe: im Dummy nicht vorhanden, muss später
# durch echte Bestandsdaten ersetzt werden.
DEFAULT_STOCK = 25


def product_group_id_for(product: dict) -> str:
    if product["variant"]:
        return f"robe-{product['variant']}"
    return slugify(product["category"])


async def seed_states(session) -> dict[str, State]:
    by_slug: dict[str, State] = {}
    for data in STATES:
        result = await session.execute(select(State).where(State.slug == data["slug"]))
        state = result.scalar_one_or_none()
        if state is None:
            state = State(**data)
            session.add(state)
        else:
            for key, value in data.items():
                setattr(state, key, value)
        by_slug[data["slug"]] = state
    await session.flush()
    return by_slug


async def seed_products(session, states_by_slug: dict[str, State]) -> None:
    for data in PRODUCTS:
        slug = slugify(data["name"])
        result = await session.execute(
            select(Product)
            .where(Product.slug == slug)
            .options()
        )
        product = result.scalar_one_or_none()

        values = {
            "name": data["name"],
            "slug": slug,
            "category": data["category"],
            "state_id": states_by_slug[data["state"]].id,
            "material": data["material"],
            "price": data["price"],
            "is_new": data["is_new"],
            "is_bestseller": data["bestseller"],
            "variant": data["variant"],
            "status": ProductStatus.ACTIVE,
            "product_group_id": product_group_id_for(data),
        }

        if product is None:
            product = Product(id=uuid.uuid4(), **values)
            session.add(product)
            await session.flush()
        else:
            for key, value in values.items():
                setattr(product, key, value)

        # ProductImage: nur, wenn der Dummy ein Bild für dieses Produkt hatte.
        if data["img"]:
            image_result = await session.execute(
                select(ProductImage).where(ProductImage.product_id == product.id)
            )
            existing_images = image_result.scalars().all()
            if not existing_images:
                session.add(
                    ProductImage(
                        product_id=product.id,
                        url=f"/static/images/{data['img']}",
                        sort_order=0,
                        alt_text=data["name"],
                    )
                )

        # ProductSize je Größe aus dem Dummy, mit Platzhalter-Bestand.
        size_result = await session.execute(
            select(ProductSize).where(ProductSize.product_id == product.id)
        )
        existing_sizes = {s.size: s for s in size_result.scalars().all()}
        for size in data["sizes"]:
            if size in existing_sizes:
                continue
            sku = f"{slug}-{slugify(size)}".upper()
            session.add(
                ProductSize(product_id=product.id, size=size, stock=DEFAULT_STOCK, sku=sku)
            )


# Platzhalter-Versandzonen/-tarife, wie im Pflichtenheft als Beispiel
# genannt (Deutschland/EU/Rest der Welt) - Werte sind Annahmen, bis
# konkrete Zonen/Tarife feststehen, und lassen sich im Admin unter
# /admin/shipping-zone jederzeit anpassen. Die Freigrenze für Deutschland
# übernimmt den bereits im Dummy kommunizierten Wert ("Free shipping on
# orders over €120").
EU_COUNTRY_CODES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
]

SHIPPING_ZONES = [
    {
        "name": "Deutschland",
        "country_codes": ["DE"],
        "free_shipping_threshold": "120.00",
        "rates": [{"method_name": "Standard", "price": "4.95"}],
    },
    {
        "name": "EU",
        "country_codes": EU_COUNTRY_CODES,
        "free_shipping_threshold": "150.00",
        "rates": [{"method_name": "Standard", "price": "9.95"}],
    },
    {
        "name": "Rest der Welt",
        "country_codes": [],  # leere Liste = Fallback-Zone, siehe app/core/checkout.py
        "free_shipping_threshold": None,
        "rates": [{"method_name": "Standard International", "price": "19.95"}],
    },
]


async def seed_shipping_zones(session) -> None:
    for data in SHIPPING_ZONES:
        result = await session.execute(select(ShippingZone).where(ShippingZone.name == data["name"]))
        zone = result.scalar_one_or_none()
        if zone is None:
            zone = ShippingZone(
                name=data["name"],
                country_codes=data["country_codes"],
                free_shipping_threshold=data["free_shipping_threshold"],
            )
            session.add(zone)
            await session.flush()
        else:
            zone.country_codes = data["country_codes"]
            zone.free_shipping_threshold = data["free_shipping_threshold"]

        rate_result = await session.execute(select(ShippingRate).where(ShippingRate.zone_id == zone.id))
        existing_rates = {r.method_name: r for r in rate_result.scalars().all()}
        for rate_data in data["rates"]:
            if rate_data["method_name"] in existing_rates:
                existing_rates[rate_data["method_name"]].price = rate_data["price"]
            else:
                session.add(
                    ShippingRate(
                        zone_id=zone.id, method_name=rate_data["method_name"], price=rate_data["price"]
                    )
                )


async def main() -> None:
    async with async_session_maker() as session:
        states_by_slug = await seed_states(session)
        await seed_products(session, states_by_slug)
        await seed_shipping_zones(session)
        await session.commit()
    print(
        f"Seed abgeschlossen: {len(STATES)} States, {len(PRODUCTS)} Produkte, "
        f"{len(SHIPPING_ZONES)} Versandzonen."
    )


if __name__ == "__main__":
    asyncio.run(main())
