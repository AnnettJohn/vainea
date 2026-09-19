"""Deckt den aus dem Click-Dummy (index.html) übernommenen Homepage-Content
ab: Hero, States-Grid, Most-Wanted, Details, Shop-the-Look, Accessoires,
Quiz und Instagram-/Newsletter-Sektionen."""


async def test_home_hero_shows_all_states(client):
    response = await client.get("/")
    assert response.status_code == 200
    for name in ("SUN", "SEA", "DREAM", "LIGHT"):
        assert name in response.text
    assert "Wear your" in response.text
    assert 'data-hero-select="sun"' in response.text


async def test_home_shows_most_wanted_mono_robes(client):
    response = await client.get("/")
    assert "MOST WANTED" in response.text  # Überschriften sind im Dummy versal
    for name in ("Sun Mono Robe", "Sea Mono Robe", "Dream Mono Robe", "Light Mono Robe"):
        assert name in response.text


async def test_home_shows_detail_tiles(client):
    response = await client.get("/")
    for label in ("Frottee", "Zipper", "Kordeln", "Ösen"):
        assert label in response.text


async def test_home_shows_shop_the_look_hotspots(client):
    response = await client.get("/")
    assert "SHOP THE LOOK" in response.text
    assert "Aperitivo Spa Bag" in response.text
    assert "Aperitivo Terry Towel" in response.text
    assert "Aperitivo Water Bottle" in response.text


async def test_home_shows_accessories(client):
    response = await client.get("/")
    assert "COMPLETE YOUR STATE." in response.text
    assert "Horizon Spa Bag" in response.text
    assert "Citrus Light Bottle" in response.text
    assert "Aperitivo Terry Towel" in response.text


async def test_home_shows_quiz_with_all_moods(client):
    response = await client.get("/")
    assert "How do you want to feel today?" in response.text
    for label in ("ENERGETIC", "FREE", "CALM", "BRIGHT"):
        assert label in response.text


async def test_home_shows_instagram_and_newsletter_sections(client):
    response = await client.get("/")
    assert "Folge unserem State" in response.text
    assert "Newsletter" in response.text
