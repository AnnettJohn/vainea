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
    # Alle vier State-Varianten der Mono-Robe-Gruppe müssen als Swatches da sein.
    # Nur der Auswahlblock der PDP zählt - Cross-Sell-Karten bringen eigene mit.
    select_block = response.text.split('id="add-to-cart-form"', 1)[1].split("</form>", 1)[0]
    assert select_block.count("swatch-btn") == 4


async def test_product_detail_404_for_unknown_slug(client):
    response = await client.get("/products/does-not-exist")
    assert response.status_code == 404


async def test_legal_page_unpublished_shows_notice(client):
    """Entwuerfe mit Platzhaltern duerfen nicht oeffentlich erscheinen - die
    Seite existiert aber, damit der Footer-Link nicht ins Leere laeuft."""
    response = await client.get("/legal/impressum")
    assert response.status_code == 200
    assert "Impressum" in response.text
    assert "juristisch geprüft" in response.text
    # Kein Entwurfstext und keine Platzhalter nach aussen.
    assert "[Firmenname" not in response.text
    assert "RECHTLICH PRÜFEN" not in response.text


async def test_all_four_legal_pages_exist(client):
    for slug in ("impressum", "datenschutz", "agb", "widerruf"):
        response = await client.get(f"/legal/{slug}")
        assert response.status_code == 200, slug


async def test_legal_page_renders_body_when_published(client, db_session):
    """Veroeffentlichter Text wird als HTML ausgegeben, Markdown-Subset
    aufgeloest."""
    from sqlalchemy import select

    from app.models.legal import LegalPage

    seite = (await db_session.execute(select(LegalPage).where(LegalPage.slug == "agb"))).scalar_one()
    original_body, original_published = seite.body, seite.is_published
    seite.body = "## Paragraf 1\n\nEin **wichtiger** Absatz.\n\n- Erster Punkt\n- Zweiter Punkt"
    seite.is_published = True
    await db_session.commit()
    try:
        response = await client.get("/legal/agb")
        assert "<h2>Paragraf 1</h2>" in response.text
        assert "<strong>wichtiger</strong>" in response.text
        assert "<li>Erster Punkt</li>" in response.text
        assert "juristisch geprüft" not in response.text
    finally:
        seite.body, seite.is_published = original_body, original_published
        await db_session.commit()


async def test_legal_unknown_page_404(client):
    response = await client.get("/legal/nonexistent")
    assert response.status_code == 404
