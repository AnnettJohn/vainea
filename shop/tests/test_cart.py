from sqlalchemy import select

from app.models.product import Product, ProductSize


async def _get_size_id(db_session, slug: str, size: str) -> str:
    product = (await db_session.execute(select(Product).where(Product.slug == slug))).scalar_one()
    product_size = (
        await db_session.execute(
            select(ProductSize).where(ProductSize.product_id == product.id, ProductSize.size == size)
        )
    ).scalar_one()
    return str(product_size.id)


async def test_add_to_cart_sets_cookie_and_shows_toast(client, db_session):
    size_id = await _get_size_id(db_session, "sun-mono-robe", "M")

    response = await client.post("/cart/items", data={"product_size_id": size_id, "quantity": "2"})

    assert response.status_code == 200
    assert "in den Warenkorb gelegt" in response.text
    assert '<span class="cart-count">2</span>' in response.text  # OOB-Swap des Bag-Badges
    assert client.cookies.get("vainea_cart") is not None


async def test_view_cart_shows_added_item_and_subtotal(client, db_session):
    size_id = await _get_size_id(db_session, "sun-mono-robe", "M")
    await client.post("/cart/items", data={"product_size_id": size_id, "quantity": "2"})

    response = await client.get("/cart")

    assert response.status_code == 200
    assert "Sun Mono Robe" in response.text
    assert "378.00" in response.text  # 2 x 189.00


async def test_update_quantity_recomputes_subtotal(client, db_session):
    size_id = await _get_size_id(db_session, "sun-mono-robe", "M")
    await client.post("/cart/items", data={"product_size_id": size_id, "quantity": "1"})

    cart_page = await client.get("/cart")
    item_id = cart_page.text.split("cart/items/")[1].split("/quantity")[0]

    response = await client.post(f"/cart/items/{item_id}/quantity", data={"quantity": "3"})

    assert response.status_code == 200
    assert "567.00" in response.text  # 3 x 189.00


async def test_remove_item_empties_cart(client, db_session):
    size_id = await _get_size_id(db_session, "sun-mono-robe", "M")
    await client.post("/cart/items", data={"product_size_id": size_id, "quantity": "1"})

    cart_page = await client.get("/cart")
    item_id = cart_page.text.split("cart/items/")[1].split("/quantity")[0]

    response = await client.post(f"/cart/items/{item_id}/remove")

    assert response.status_code == 200
    assert "Warenkorb ist leer" in response.text


async def test_add_more_than_stock_is_clamped(client, db_session):
    size_id = await _get_size_id(db_session, "sun-mono-robe", "M")

    response = await client.post("/cart/items", data={"product_size_id": size_id, "quantity": "9999"})

    assert response.status_code == 200
    assert '<span class="cart-count">25</span>' in response.text  # Seed-Platzhalterbestand ist 25


async def test_add_unknown_size_is_rejected(client):
    response = await client.post("/cart/items", data={"product_size_id": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code == 400
