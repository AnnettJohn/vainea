import json
import xml.etree.ElementTree as ET

from sqlalchemy import select

from app.models.product import Product


async def test_sitemap_is_valid_xml_with_expected_urls(client):
    response = await client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")

    root = ET.fromstring(response.text)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [el.find("s:loc", ns).text for el in root.findall("s:url", ns)]

    # 3 statische Seiten + 4 States + 24 Produkte
    assert len(urls) == 31
    assert any(u.endswith("/states/sun") for u in urls)
    assert any(u.endswith("/products/sun-mono-robe") for u in urls)


async def test_robots_txt_points_to_sitemap(client):
    response = await client.get("/robots.txt")
    assert response.status_code == 200
    assert "Sitemap:" in response.text
    assert response.text.endswith("/sitemap.xml\n")


async def test_product_page_has_valid_json_ld(client):
    response = await client.get("/products/sun-mono-robe")
    assert response.status_code == 200

    start = response.text.index('<script type="application/ld+json">') + len(
        '<script type="application/ld+json">'
    )
    end = response.text.index("</script>", start)
    data = json.loads(response.text[start:end])

    assert data["@type"] == "Product"
    assert data["name"] == "Sun Mono Robe"
    assert data["offers"]["price"] == "189.00"
    assert data["offers"]["availability"] == "https://schema.org/InStock"


async def test_product_meta_override_takes_precedence(client, db_session):
    product = (await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))).scalar_one()
    product.meta_title = "Individueller SEO-Titel"
    product.meta_description = "Individuelle Beschreibung."
    await db_session.commit()

    response = await client.get("/products/sun-mono-robe")

    assert "<title>Individueller SEO-Titel</title>" in response.text
    assert 'content="Individuelle Beschreibung."' in response.text

    product.meta_title = None
    product.meta_description = None
    await db_session.commit()


async def test_product_page_has_canonical_link(client):
    response = await client.get("/products/sun-mono-robe")
    assert 'rel="canonical"' in response.text
    assert "/products/sun-mono-robe" in response.text
