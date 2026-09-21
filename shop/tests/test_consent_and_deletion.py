"""Cookie-Einwilligung und Konto-Löschung (DSGVO-Punkte aus dem Pflichtenheft)."""

from sqlalchemy import select

from app.core.consent import COOKIE_NAME
from app.models.cart import Cart
from app.models.order import Order
from app.models.user import User
from app.models.wishlist import WishlistItem


class TestConsentBanner:
    async def test_banner_erscheint_ohne_entscheidung(self, client):
        response = await client.get("/")
        assert "consent-banner" in response.text
        assert "Nur notwendige" in response.text
        assert "Alle akzeptieren" in response.text

    async def test_banner_verschwindet_nach_entscheidung(self, client):
        await client.post("/consent", data={"choice": "essential", "next": "/"}, follow_redirects=False)
        response = await client.get("/")
        assert "consent-banner" not in response.text

    async def test_ablehnen_setzt_cookie_auf_essential(self, client):
        response = await client.post(
            "/consent", data={"choice": "essential", "next": "/"}, follow_redirects=False
        )
        assert response.status_code == 303
        assert response.cookies[COOKIE_NAME] == "essential"

    async def test_zustimmen_setzt_cookie_auf_all(self, client):
        response = await client.post("/consent", data={"choice": "all", "next": "/"}, follow_redirects=False)
        assert response.cookies[COOKIE_NAME] == "all"

    async def test_unbekannter_wert_faellt_auf_essential_zurueck(self, client):
        """Bei manipulierter Eingabe die datensparsame Variante wählen,
        nicht die weitreichende."""
        response = await client.post(
            "/consent", data={"choice": "alles-erlaubt", "next": "/"}, follow_redirects=False
        )
        assert response.cookies[COOKIE_NAME] == "essential"

    async def test_kein_open_redirect(self, client):
        """Der Banner steht auf jeder Seite - über `next` darf er nicht zu
        einer Weiterleitung auf fremde Domains werden."""
        for ziel in ("https://fremde.example/", "//fremde.example/"):
            response = await client.post(
                "/consent", data={"choice": "all", "next": ziel}, follow_redirects=False
            )
            assert response.headers["location"] == "/"

    async def test_rücksprung_auf_lokalen_pfad(self, client):
        response = await client.post(
            "/consent", data={"choice": "all", "next": "/shop"}, follow_redirects=False
        )
        assert response.headers["location"] == "/shop"

    async def test_warenkorb_funktioniert_ohne_einwilligung(self, client, db_session):
        """Essenzielle Cookies sind einwilligungsfrei. Der Warenkorb darf
        nicht davon abhängen, dass jemand den Banner wegklickt."""
        from app.models.product import Product, ProductSize

        produkt = (
            await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))
        ).scalar_one()
        groesse = (
            await db_session.execute(select(ProductSize).where(ProductSize.product_id == produkt.id))
        ).scalars().first()

        response = await client.post("/cart/items", data={"product_size_id": str(groesse.id), "quantity": 1})
        assert response.status_code == 200
        assert "Warenkorb gelegt" in response.text


class TestKontoLoeschung:
    async def _konto_anlegen(self, client, email: str = "loeschen@example.de"):
        await client.post(
            "/account/register",
            data={"email": email, "password": "einSicheresPasswort123"},
            follow_redirects=False,
        )
        await client.post(
            "/account/login",
            data={"email": email, "password": "einSicheresPasswort123"},
            follow_redirects=False,
        )

    async def test_loeschung_braucht_bestaetigung(self, client, db_session):
        await self._konto_anlegen(client, "bestaetigung@example.de")

        response = await client.post("/account/delete", data={"confirm": "ja"}, follow_redirects=False)
        assert response.status_code == 400

        noch_da = (
            await db_session.execute(select(User).where(User.email == "bestaetigung@example.de"))
        ).unique().scalar_one_or_none()
        assert noch_da is not None, "Konto darf ohne korrekte Bestätigung nicht gelöscht werden"

    async def test_loeschung_entfernt_konto_merkzettel_und_warenkorb(self, client, db_session):
        from app.models.product import Product

        await self._konto_anlegen(client, "vollstaendig@example.de")
        nutzer = (
            await db_session.execute(select(User).where(User.email == "vollstaendig@example.de"))
        ).unique().scalar_one()
        produkt = (
            await db_session.execute(select(Product).where(Product.slug == "sun-mono-robe"))
        ).scalar_one()

        db_session.add(WishlistItem(user_id=nutzer.id, product_id=produkt.id))
        db_session.add(Cart(user_id=nutzer.id, session_token="test-token-loeschung"))
        await db_session.commit()
        nutzer_id = nutzer.id

        response = await client.post("/account/delete", data={"confirm": "LÖSCHEN"}, follow_redirects=False)
        assert response.status_code == 303

        weg = (
            await db_session.execute(select(User).where(User.id == nutzer_id))
        ).unique().scalar_one_or_none()
        assert weg is None
        merkzettel = (
            await db_session.execute(select(WishlistItem).where(WishlistItem.user_id == nutzer_id))
        ).scalars().all()
        assert merkzettel == []
        warenkoerbe = (
            await db_session.execute(select(Cart).where(Cart.user_id == nutzer_id))
        ).scalars().all()
        assert warenkoerbe == []

    async def test_bestellungen_ueberleben_die_loeschung(self, client, db_session):
        """Der eigentliche Punkt: § 147 AO und § 257 HGB verlangen, dass
        Rechnungsdaten aufbewahrt werden. Art. 17 Abs. 3 lit. b DSGVO nimmt
        sie deshalb von der Löschpflicht aus. Die Bestellung bleibt, die
        Verknüpfung zum Konto fällt weg."""
        from decimal import Decimal

        await self._konto_anlegen(client, "bestellung@example.de")
        nutzer = (
            await db_session.execute(select(User).where(User.email == "bestellung@example.de"))
        ).unique().scalar_one()

        bestellung = Order(
            order_number="TEST-LOESCH-001",
            user_id=nutzer.id,
            shipping_name="Erika Mustermann",
            shipping_street="Musterweg 1",
            shipping_zip="12345",
            shipping_city="Musterstadt",
            shipping_country="DE",
            billing_name="Erika Mustermann",
            billing_street="Musterweg 1",
            billing_zip="12345",
            billing_city="Musterstadt",
            billing_country="DE",
            subtotal=Decimal("189.00"),
            total=Decimal("193.95"),
        )
        db_session.add(bestellung)
        await db_session.commit()

        await client.post("/account/delete", data={"confirm": "LÖSCHEN"}, follow_redirects=False)

        db_session.expire_all()
        nachher = (
            await db_session.execute(select(Order).where(Order.order_number == "TEST-LOESCH-001"))
        ).scalar_one_or_none()
        assert nachher is not None, "Bestellung darf nicht mitgelöscht werden"
        assert nachher.user_id is None, "Verknüpfung zum Konto muss aufgehoben sein"
        assert nachher.shipping_name == "Erika Mustermann", "Rechnungsdaten bleiben als Momentaufnahme"

    async def test_ohne_login_keine_loeschung(self, client):
        response = await client.post("/account/delete", data={"confirm": "LÖSCHEN"}, follow_redirects=False)
        assert response.status_code == 303
        assert "/account/login" in response.headers["location"]
