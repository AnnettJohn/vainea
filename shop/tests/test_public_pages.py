async def test_home_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "VAINEA" in response.text


async def test_shop_page_lists_products(client):
    response = await client.get("/shop")
    assert response.status_code == 200
    assert "Sun Mono Robe" in response.text


async def test_shop_filter_by_state(client):
    response = await client.get("/shop", params={"state": "sun"})
    assert response.status_code == 200
    assert "Sun Mono Robe" in response.text
    assert "Sea Mono Robe" not in response.text


async def test_state_detail_page(client):
    response = await client.get("/states/sun")
    assert response.status_code == 200
    assert "SUN" in response.text


async def test_state_detail_404_for_unknown_slug(client):
    response = await client.get("/states/does-not-exist")
    assert response.status_code == 404


async def test_product_detail_page(client):
    response = await client.get("/products/sun-mono-robe")
    assert response.status_code == 200
    assert "Sun Mono Robe" in response.text
    # Alle vier State-Varianten der Mono-Robe-Gruppe müssen als Swatches da sein
    assert response.text.count("swatch-btn") == 4


async def test_product_detail_404_for_unknown_slug(client):
    response = await client.get("/products/does-not-exist")
    assert response.status_code == 404


async def test_legal_placeholder_pages(client):
    response = await client.get("/legal/impressum")
    assert response.status_code == 200
    assert "Impressum" in response.text


async def test_legal_unknown_page_404(client):
    response = await client.get("/legal/nonexistent")
    assert response.status_code == 404
