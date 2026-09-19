from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.product import Product, ProductStatus
from app.models.state import State

router = APIRouter()

STATIC_PAGES = ["/", "/shop", "/story"]


@router.get("/sitemap.xml")
async def sitemap(request: Request, db: AsyncSession = Depends(get_db)):
    base_url = str(request.base_url).rstrip("/")
    urls: list[tuple[str, str | None]] = [(f"{base_url}{path}", None) for path in STATIC_PAGES]

    states_result = await db.execute(select(State))
    for state in states_result.scalars().all():
        urls.append((f"{base_url}/states/{state.slug}", state.updated_at.isoformat()))

    products_result = await db.execute(select(Product).where(Product.status == ProductStatus.ACTIVE))
    for product in products_result.scalars().all():
        urls.append((f"{base_url}/products/{product.slug}", product.updated_at.isoformat()))

    entries = []
    for loc, lastmod in urls:
        lastmod_tag = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        entries.append(f"<url><loc>{escape(loc)}</loc>{lastmod_tag}</url>")

    header = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml = header + "".join(entries) + "</urlset>"

    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots(request: Request):
    base_url = str(request.base_url).rstrip("/")
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /account\nSitemap: {base_url}/sitemap.xml\n"
    return PlainTextResponse(body)
