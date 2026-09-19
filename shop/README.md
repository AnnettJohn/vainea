# VAINEA Shop

[![CI](https://github.com/AnnettJohn/vainea/actions/workflows/ci.yml/badge.svg)](https://github.com/AnnettJohn/vainea/actions/workflows/ci.yml)

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

Für Bestellbestätigungsmails lokal einen SMTP-Catcher starten (fängt Mails
ab, kein echter Versand nötig - Web-UI unter http://localhost:8025):

```bash
docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
```

Die Default-Werte in `.env.example` (`SMTP_HOST=localhost`, `SMTP_PORT=1025`,
kein Login/TLS) passen direkt zu Mailhog/Mailpit. Für Produktion durch einen
echten SMTP-Anbieter ersetzen.

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
Postgres-Instanz und einen echten lokalen SMTP-Server (kein laufender
Server/Docker nötig) und legt darin States/Produkte/Versandzonen wie im
Seed-Skript an. 56 Tests decken die zentralen Flows ab: Warenkorb, Checkout
(inkl. Versandzonen-Fallback, Bestandsreservierung mit Race-Condition-Fall,
Rabattcodes, Webhook-Idempotenz), Bestellbestätigungsmail (inkl. Ausfall-
sicherheit bei SMTP-Fehlern), Login/Registrierung/Wishlist,
SQLAdmin-Zugriffsschutz, Objektspeicher-Upload/URL-Migration (gegen einen
von `moto` gemockten S3-Bucket), Sitemap/Schema.org-Markup sowie der aus
dem Click-Dummy übernommene Homepage-Content.

Läuft bei jedem Push/PR automatisch über [GitHub Actions](../.github/workflows/ci.yml)
(Lint + Tests, siehe Badge oben).

## Deployment

Referenz-Setup für einen einzelnen Hetzner-Server (siehe Pflichtenheft,
Deployment & Hosting): FastAPI-App in Docker, dahinter Caddy als Reverse
Proxy mit automatischem Let's-Encrypt-TLS, Postgres läuft im selben
Compose-Stack mit ("mitlaufende Instanz").

```bash
cp .env.example .env   # echte Werte eintragen, insbesondere POSTGRES_PASSWORD/SECRET_KEY
# Domain(s) in Caddyfile anpassen (Default: vainea.de, www.vainea.de)
docker compose up -d --build
```

Migrationen laufen automatisch beim Container-Start (`docker-entrypoint.sh`).
Einmalig danach seeden bzw. einen Admin-Account anlegen:

```bash
docker compose exec app python -m scripts.seed
docker compose exec app python -c "..."   # siehe Admin-Snippet oben
```

Das Admin-Interface läuft vorerst unter `/admin` auf der Root-Domain (wie im
Pflichtenheft vorgesehen) und kann später auf eine eigene Subdomain
umziehen, ohne dass sich am Datenmodell etwas ändert - dafür ist im
`Caddyfile` bereits ein auskommentierter Beispielblock hinterlegt.

### Produktbilder in den Objektspeicher migrieren

Einmalig nach dem ersten Deployment (oder immer, wenn neue Bilder lokal
unter `app/static/images` liegen, die noch nicht migriert wurden):

1. Bucket im [Hetzner-Cloud-Console](https://console.hetzner.cloud/) anlegen,
   auf **öffentlich** stellen und einen Access-Key erzeugen.
2. `S3_*`-Variablen in `.env` eintragen (siehe `.env.example`).
3. Migration laufen lassen:

   ```bash
   docker compose exec app python -m scripts.upload_images_to_storage
   ```

   Lädt alle Dateien aus `app/static/images` in den Bucket hoch und biegt
   alle `State`/`ProductImage`-URLs, die noch auf `/static/images/...`
   zeigen, auf die neue öffentliche Objektspeicher-URL um. Mehrfach
   ausführbar (überschreibt Dateien, biegt nur noch lokale URLs um).

Für neue Bilder danach: Datei über die Hetzner-Console (oder `s3cmd`/`rclone`)
in den Bucket hochladen und die resultierende URL im Admin bei der
jeweiligen `ProductImage`/`State` eintragen - es gibt (bewusst, siehe
Pflichtenheft-Umfang von ~24 Produkten) kein eigenes Datei-Upload-Feld im
Admin-Formular.

**Ein beim Bauen dieser Config gefundener und behobener Fehler**: Ein naiver
`pip install .`-Schritt im Dockerfile hätte ein Wheel des eigenen Pakets
gebaut, das mangels `package_data`-Konfiguration keine Templates/Static-
Dateien enthält (setuptools bündelt standardmäßig nur `.py`-Dateien) - der
Container hätte ohne jede Fehlerseite einfach nur 500er ausgeliefert. Fix:
das eigene Paket nach der Dependency-Installation wieder deinstallieren und
stattdessen den echten Quellcode direkt kopieren (`PYTHONPATH=/app`). Gegen
eine originalgetreu nachgebaute Laufzeitumgebung (kein Docker in dieser
Sandbox verfügbar) sowie mit einem echten, validierten Caddy-Reverse-Proxy
verifiziert.

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
- **Bestellbestätigung per E-Mail**: Sobald der Webhook eine Zahlung als
  "paid" bestätigt, geht automatisch eine HTML+Text-Mail mit Bestellnummer,
  Positionen, Summen und Lieferadresse an `guest_email` raus (SMTP via
  Python-Standardbibliothek, kein zusätzlicher E-Mail-Dienstanbieter nötig).
  Schlägt der Versand fehl (SMTP nicht erreichbar), bleibt die Bestellung
  trotzdem korrekt als bezahlt markiert - nur die Mail fehlt dann und wird
  geloggt.

Rechtstexte sind als Platzhalterseiten unter `/legal/*` verlinkt (Footer).

**Objektspeicher für Produktbilder** (Hetzner Object Storage, S3-kompatibel):
`scripts/upload_images_to_storage.py` migriert bestehende lokale Bilder
einmalig in einen Bucket und schreibt die neuen URLs zurück in
State/ProductImage. Lokal ohne konfigurierten Objektspeicher bleibt alles
wie gehabt bei `app/static/images` - keine Pflicht für die Entwicklung.

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

**Homepage-Content aus dem Click-Dummy** (`index.html`) 1:1 nachgebaut,
serverseitig gerendert mit echten DB-Daten statt der dummy-eigenen
JS-Arrays: Hero mit State-Umschaltung (Klick auf einen State-Kreis wechselt
Bild/Text/CTA per Vanilla-JS, kein Server-Roundtrip), States-Grid mit
Hover-Reveal der Story, Brand-Line-Copy, "Most Wanted" (die vier Mono-Robes),
Detail-Kachelreihe, "Shop the Look" mit klickbaren Bild-Hotspots,
"Complete Your State"-Accessoires, der "Find your state"-Quiz (alle vier
Ergebnisse serverseitig vorgerendert, JS blendet nur um) sowie Instagram-
Teaser und Newsletter-Formular.

**Bewusst nicht angebunden**: Das Newsletter-Formular verhält sich wie im
Click-Dummy rein clientseitig (zeigt eine Erfolgsmeldung, speichert aber
nichts) - eine echte Anbindung (Datenbank-Tabelle oder Anbieter wie
Mailchimp/Brevo) ist im Pflichtenheft nicht vorgesehen und bräuchte vorher
eine Entscheidung, welcher Weg gewünscht ist. Instagram/Pinterest-Links
sind wie im Dummy Platzhalter (`href="#"`), da keine echten Profil-URLs
vorliegen.

Noch offen: ein echter SMTP-Anbieter für Produktion (aktuell auf
Mailhog/Mailpit-Defaults für lokale Entwicklung eingestellt), ein
Datei-Upload-Feld im Admin für neue Produktbilder (aktuell URL-Feld, Upload
erfolgt separat über Hetzner-Console/CLI), sowie die endgültigen Inhalte für
Rechtstexte und die finalen Versandzonen/-tarife (aktuell Platzhalter, siehe
oben).
