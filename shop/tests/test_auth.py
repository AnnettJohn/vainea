from sqlalchemy import select

from app.models.product import Product


async def test_register_logs_in_and_redirects_to_account(client):
    response = await client.post(
        "/account/register",
        data={"email": "neu@example.com", "password": "supersecret123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/account"
    assert client.cookies.get("vainea_auth") is not None


async def test_register_duplicate_email_shows_error(client):
    await client.post("/account/register", data={"email": "doppelt@example.com", "password": "supersecret123"})
    response = await client.post(
        "/account/register", data={"email": "doppelt@example.com", "password": "andereswort123"}
    )
    assert response.status_code == 400
    assert "existiert bereits" in response.text


async def test_login_with_wrong_password_shows_error(client):
    await client.post("/account/register", data={"email": "user@example.com", "password": "correct-password-1"})
    client.cookies.clear()

    response = await client.post(
        "/account/login", data={"email": "user@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 400
    assert "falsch" in response.text


async def test_login_with_correct_password_succeeds(client):
    await client.post("/account/register", data={"email": "user2@example.com", "password": "correct-password-1"})
    client.cookies.clear()

    response = await client.post(
        "/account/login",
        data={"email": "user2@example.com", "password": "correct-password-1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert client.cookies.get("vainea_auth") is not None


async def test_account_requires_login_and_redirects(client):
    response = await client.get("/account", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/account/login")


async def test_account_dashboard_shows_email_when_logged_in(client):
    await client.post("/account/register", data={"email": "dashboard@example.com", "password": "supersecret123"})
    response = await client.get("/account")
    assert response.status_code == 200
    assert "dashboard@example.com" in response.text


async def test_logout_clears_session(client):
    await client.post("/account/register", data={"email": "logout@example.com", "password": "supersecret123"})
    await client.post("/account/logout")

    response = await client.get("/account", follow_redirects=False)
    assert response.status_code == 303


async def test_wishlist_toggle_requires_login(client, db_session):
    product = (await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))).scalar_one()
    response = await client.post(f"/account/wishlist/{product.id}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/account/login")


async def test_wishlist_add_and_remove(client, db_session):
    await client.post("/account/register", data={"email": "wishlist@example.com", "password": "supersecret123"})
    product = (await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))).scalar_one()

    add_response = await client.post(f"/account/wishlist/{product.id}", follow_redirects=False)
    assert add_response.status_code == 303

    dashboard = await client.get("/account")
    assert "Sun Mono Robe" in dashboard.text

    remove_response = await client.post(f"/account/wishlist/{product.id}/remove", follow_redirects=False)
    assert remove_response.status_code == 303

    dashboard_after = await client.get("/account")
    assert "Noch nichts gemerkt" in dashboard_after.text
