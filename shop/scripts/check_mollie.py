"""Mollie-Anbindung prüfen, ohne eine Zahlung auszulösen.

    python -m scripts.check_mollie

Ruft die hinterlegten Zahlungsmethoden ab. Das ist der einfachste Aufruf,
der einen ungültigen Schlüssel sofort auffliegen lässt, und er kostet nichts.

Warnt ausdrücklich, wenn ein Live-Schlüssel eingetragen ist: mit dem werden
Zahlungen echt abgebucht, auch wenn man nur testen wollte.
"""

import sys

from mollie.api.error import Error as MollieError

from app.core.config import get_settings
from app.core.mollie import get_mollie_client, mollie_configured

settings = get_settings()


def main() -> int:
    if not mollie_configured():
        print("  Kein MOLLIE_API_KEY gesetzt - Zahlung ist nicht eingerichtet.", file=sys.stderr)
        return 1

    schluessel = settings.mollie_api_key
    art = "Test" if schluessel.startswith("test_") else "LIVE" if schluessel.startswith("live_") else "unbekannt"
    print(f"  Schlüssel: {schluessel[:8]}… ({art})")
    print(f"  Webhook:   {settings.mollie_webhook_url or '(nicht gesetzt)'}")

    if art == "LIVE":
        print()
        print("  ACHTUNG: Das ist ein Live-Schlüssel. Zahlungen werden echt")
        print("  abgebucht. Zum Ausprobieren gehört ein test_-Schlüssel.")

    if not settings.mollie_webhook_url:
        print()
        print("  WARNUNG: Ohne Webhook-URL erfährt der Shop nie, dass bezahlt", file=sys.stderr)
        print("  wurde. Bestellungen blieben dauerhaft auf 'pending' stehen", file=sys.stderr)
        print("  und der reservierte Lagerbestand würde nicht freigegeben.", file=sys.stderr)

    try:
        client = get_mollie_client()
        methoden = list(client.methods.list())
    except MollieError as exc:
        print(f"  FEHLER: Mollie lehnt den Schlüssel ab ({exc}).", file=sys.stderr)
        print("  Schlüssel im Mollie-Dashboard unter Entwickler → API-Keys prüfen.", file=sys.stderr)
        return 1
    except Exception as exc:  # Netzwerk, DNS, TLS
        print(f"  FEHLER: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if not methoden:
        print()
        print("  Schlüssel gültig, aber keine Zahlungsmethode aktiv.", file=sys.stderr)
        print("  Im Mollie-Dashboard unter Einstellungen → Zahlungsmethoden", file=sys.stderr)
        print("  mindestens eine freischalten, sonst bricht der Checkout ab.", file=sys.stderr)
        return 1

    print()
    print(f"  Verbindung in Ordnung. {len(methoden)} Zahlungsmethode(n) aktiv:")
    for m in methoden:
        print(f"    - {m.description}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
