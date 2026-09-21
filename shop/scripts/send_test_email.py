"""Testmail über die konfigurierte SMTP-Verbindung verschicken.

    python -m scripts.send_test_email empfaenger@example.de

Prüft die Zugangsdaten aus der .env gegen den echten Mailserver. Bewusst ein
eigenes Skript und nicht nur ein Unit-Test: die Tests laufen gegen einen
lokalen SMTP-Server und sagen nichts darüber, ob Host, Port, Anmeldung und
Absenderadresse beim echten Anbieter stimmen.

Gibt bei Fehlern die häufigsten Ursachen mit aus - SMTP-Fehlermeldungen sind
notorisch wortkarg.
"""

import asyncio
import smtplib
import sys

from app.core.config import get_settings
from app.core.email import send_email

settings = get_settings()


def _konfiguration_zeigen() -> None:
    print("Konfiguration:")
    print(f"  Host:     {settings.smtp_host}:{settings.smtp_port}")
    print(f"  STARTTLS: {'ja' if settings.smtp_use_tls else 'nein'}")
    print(f"  Benutzer: {settings.smtp_user or '(keiner - ohne Anmeldung)'}")
    print(f"  Absender: {settings.smtp_from_name} <{settings.smtp_from_email}>")
    print()


async def main(empfaenger: str) -> int:
    _konfiguration_zeigen()
    print(f"Sende Testmail an {empfaenger} ...")

    try:
        await send_email(
            to=empfaenger,
            subject="VAINEA – SMTP-Test",
            html_body=(
                "<p>Diese Nachricht bestätigt, dass der Mailversand des VAINEA-Shops "
                "funktioniert.</p><p>Sie wurde von <code>scripts/send_test_email.py</code> "
                "verschickt.</p>"
            ),
            text_body=(
                "Diese Nachricht bestätigt, dass der Mailversand des VAINEA-Shops "
                "funktioniert.\n\nVerschickt von scripts/send_test_email.py."
            ),
        )
    except smtplib.SMTPAuthenticationError as exc:
        print(f"FEHLER: Anmeldung abgelehnt ({exc.smtp_code}).", file=sys.stderr)
        print("  Benutzername ist bei den meisten Anbietern die volle", file=sys.stderr)
        print("  E-Mail-Adresse, nicht nur der Teil vor dem @.", file=sys.stderr)
        return 1
    except smtplib.SMTPSenderRefused as exc:
        print(f"FEHLER: Absenderadresse abgelehnt ({exc.smtp_code}).", file=sys.stderr)
        print(f"  SMTP_FROM_EMAIL ist {settings.smtp_from_email}.", file=sys.stderr)
        print("  Viele Anbieter erlauben nur Adressen des angemeldeten Postfachs.", file=sys.stderr)
        return 1
    except (smtplib.SMTPConnectError, OSError) as exc:
        print(f"FEHLER: Keine Verbindung zu {settings.smtp_host}:{settings.smtp_port} ({exc}).", file=sys.stderr)
        print("  Port 587 mit STARTTLS ist der übliche Weg; 465 spricht direkt", file=sys.stderr)
        print("  TLS und funktioniert mit dieser Implementierung nicht.", file=sys.stderr)
        return 1
    except smtplib.SMTPException as exc:
        print(f"FEHLER: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("Versand erfolgreich. Bitte im Postfach nachsehen - auch im Spam-Ordner.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Aufruf: python -m scripts.send_test_email <empfaenger>", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
