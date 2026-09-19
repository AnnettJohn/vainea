import json

from fastapi import Request

from app.models.product import Product
from app.models.state import State

SITE_NAME = "VAINEA"


def product_meta(product: Product) -> tuple[str, str]:
    """Redigierbares Meta-Title/-Description-Paar für eine PDP, mit
    generiertem Fallback, falls im Admin nichts hinterlegt ist."""
    title = product.meta_title or f"{product.name} — {SITE_NAME}"
    description = product.meta_description or (
        product.description or f"{product.name} aus {product.material}, State {product.state.name}."
    )[:160]
    return title, description


def state_meta(state: State) -> tuple[str, str]:
    title = state.meta_title or f"{state.name} — {SITE_NAME}"
    description = state.meta_description or state.mood_text
    return title, description


def product_json_ld(product: Product, request: Request) -> str:
    """Schema.org Product-Markup für die PDP (Pflichtenheft, SEO-Anforderung).

    Als fertig serialisierter JSON-String zurückgegeben (nicht als dict),
    damit die Route keinen eigenen `tojson`-Jinja-Filter braucht; `</` wird
    escaped, damit das eingebettete <script>-Tag nicht vorzeitig schließt.
    """
    base_url = str(request.base_url).rstrip("/")
    product_url = f"{base_url}/products/{product.slug}"
    in_stock = any(size.stock > 0 for size in product.sizes)

    data = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.name,
        "description": (product.description or product.name),
        "sku": product.slug,
        "material": product.material,
        "url": product_url,
        "image": [f"{base_url}{img.url}" for img in product.images],
        "offers": {
            "@type": "Offer",
            "url": product_url,
            "priceCurrency": "EUR",
            "price": f"{product.price:.2f}",
            "availability": "https://schema.org/InStock" if in_stock else "https://schema.org/OutOfStock",
        },
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
