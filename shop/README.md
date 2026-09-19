# VAINEA Shop

FastAPI/Jinja2/HTMX/SQLAlchemy/SQLAdmin/FastAPI-Users/Mollie-Umsetzung des
VAINEA-Onlineshops gemäß [`../PFLICHTENHEFT.md`](../PFLICHTENHEFT.md).

## Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env  # Werte anpassen (DATABASE_URL, SECRET_KEY, MOLLIE_API_KEY, ...)
```

Postgres-Datenbank anlegen und Migrationen anwenden:

```bash
alembic upgrade head
```

States und Produkte aus dem alten Click-Dummy einspielen (idempotent):

```bash
python -m scripts.seed
```

Einen Admin-Account anlegen (SQLAdmin läuft unter `/admin`, geschützt durch
Login gegen `users.is_superuser = true`):

```bash
python -c "
import asyncio
from app.db.session import async_session_maker
from app.models.user import User
from fastapi_users.password import PasswordHelper

async def main():
    ph = PasswordHelper()
    async with async_session_maker() as s:
        s.add(User(email='admin@vainea.de', hashed_password=ph.hash('CHANGE-ME'),
                    is_active=True, is_superuser=True, is_verified=True))
        await s.commit()

asyncio.run(main())
"
```

Dev-Server starten:

```bash
uvicorn app.main:app --reload
```

- Shop: http://localhost:8000/
- Admin: http://localhost:8000/admin

## Tests

```bash
python -m pytest
```

Startet für die Dauer des Testlaufs automatisch eine eigene, ephemere
Postgres-Instanz (kein laufender Server nötig) und legt darin States/
Produkte/Versandzonen wie im Seed-Skript an. 41 Tests decken die zentralen
Flows ab: Warenkorb, Checkout (inkl. Versandzonen-Fallback, Bestands-
reservierung mit Race-Condition-Fall, Rabattcodes, Webhook-Idempotenz),
Login/Registrierung/Wishlist, SQLAdmin-Zugriffsschutz sowie Sitemap/
Schema.org-Markup.

## Stand

Umgesetzt: Projektgrundgerüst, alle SQLAlchemy-Modelle (inkl. `WishlistItem`)
mit Alembic-Migrationen, SQLAdmin für Product/ProductImage/ProductSize/
State/Order/DiscountCode/ShippingZone/ShippingRate, Seed-Skript
(States/Produkte aus dem Click-Dummy plus Platzhalter-Versandzonen
DE/EU/Rest der Welt), serverseitig gerenderte Seiten für Home/State/Shop
(mit HTMX-Filter)/PDP anhand echter DB-Daten, ein funktionierender
Gast-Warenkorb (Cookie-basiert, HTMX ohne Full-Page-Reload) sowie ein
vollständiger Checkout-Flow:

- **Adressformular** mit live per HTMX nachgeladenen **Versandmethoden**
  je Land (mehrere Methoden pro Zone im Admin pflegbar) und Rabattcode.
- **Bestandsreservierung**: Der Lagerbestand wird bereits beim Anlegen der
  Order abgebucht (mit `SELECT ... FOR UPDATE` gegen Race Conditions
  zwischen gleichzeitigen Checkouts), nicht erst bei Zahlungseingang. Bei
  endgültig gescheiterter/abgelaufener Zahlung gibt der Webhook die
  Reservierung wieder frei.
- **Mollie-Payment** → Redirect → **Webhook** setzt den Bestellstatus
  verbindlich auf "paid" (nicht der Redirect).
- **Konto/Login**: E-Mail/Passwort-Registrierung und -Login (Cookie-Session,
  FastAPI-Users), Konto-Dashboard mit Bestellübersicht, Wishlist
  (Herz-Button auf der PDP) und den zuletzt verwendeten Adressen aus
  vergangenen Bestellungen. Wird beim Checkout eingeloggt bestellt, landet
  die Order über `user_id` im Konto.

Rechtstexte sind als Platzhalterseiten unter `/legal/*` verlinkt (Footer).

**SEO** (Pflichtenheft, nicht-funktionale Anforderungen): `/sitemap.xml`
(States, aktive Produkte, statische Seiten, mit `lastmod`) und `/robots.txt`,
Schema.org-`Product`-Markup (JSON-LD) auf jeder PDP, `<link rel="canonical">`
auf PDP/State-Seiten, sowie redigierbare Meta-Title/-Description je Produkt
und State (Fallback auf generierten Titel, wenn im Admin leer gelassen).

**Mollie-Hinweis**: Ist kein `MOLLIE_API_KEY` in `.env` gesetzt, bleibt die
Bestellung nach der Adresseingabe auf "pending" stehen und `/checkout/payment/{order}`
zeigt einen Hinweis statt zur echten Mollie-Zahlungsseite weiterzuleiten -
so lässt sich der gesamte Flow bis auf den eigentlichen Zahlungsanbieter
bereits jetzt durchspielen. In diesem Fall bleibt der Lagerbestand für diese
Order reserviert, bis sie manuell storniert oder Mollie konfiguriert wird.

Bewusste Vereinfachungen dieser Phase: kein Merge eines Gast-Warenkorbs in
ein Kundenkonto beim Login (der Warenkorb bleibt für eingeloggte wie für
Gast-Nutzer cookie-basiert), kein eigenes Adressbuch-Modell (die
Konto-Adressen sind read-only aus vergangenen Bestellungen abgeleitet, da
das Pflichtenheft-Datenmodell keine eigene Address-Entität vorsieht).

Noch offen: Bestellbestätigung per E-Mail (die Confirm-Seite kündigt sie an,
verschickt aber noch keine - braucht einen SMTP-Anbieter), Homepage-Content
aus dem Dummy (Hero-Slider, Quiz, Instagram-Teaser, Newsletter-Formular),
sowie die endgültigen Inhalte für Rechtstexte und die finalen
Versandzonen/-tarife (aktuell Platzhalter, siehe oben).
