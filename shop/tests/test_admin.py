from fastapi_users.password import PasswordHelper

from app.models.user import User

_password_helper = PasswordHelper()


async def _create_superuser(db_session, email: str, password: str) -> None:
    db_session.add(
        User(
            email=email,
            hashed_password=_password_helper.hash(password),
            is_active=True,
            is_superuser=True,
            is_verified=True,
        )
    )
    await db_session.commit()


async def test_admin_redirects_unauthenticated_users(client):
    response = await client.get("/admin/product/list", follow_redirects=False)
    assert response.status_code in (302, 303)


async def test_admin_login_and_product_list(client, db_session):
    await _create_superuser(db_session, "admin@example.com", "adminpass123")

    login = await client.post(
        "/admin/login", data={"username": "admin@example.com", "password": "adminpass123"}
    )
    assert login.status_code in (200, 302)

    # Mit 24 Produkten kann "Sun Mono Robe" bei UUID-Standardsortierung auf
    # einer beliebigen Pagination-Seite landen - gezielt über die Suche
    # abfragen statt Reihenfolge/Seitengröße vorauszusetzen.
    response = await client.get("/admin/product/list", params={"search": "Sun Mono Robe"})
    assert response.status_code == 200
    assert "Sun Mono Robe" in response.text


async def test_admin_login_rejects_non_superuser(client, db_session):
    db_session.add(
        User(
            email="normal@example.com",
            hashed_password=_password_helper.hash("somepassword1"),
            is_active=True,
            is_superuser=False,
            is_verified=True,
        )
    )
    await db_session.commit()

    await client.post("/admin/login", data={"username": "normal@example.com", "password": "somepassword1"})
    response = await client.get("/admin/product/list", follow_redirects=False)
    assert response.status_code in (302, 303)
