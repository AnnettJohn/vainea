"""Verbindung und Anmeldung am Mailserver prüfen, ohne etwas zu verschicken.

    python -m scripts.check_smtp_login

Trennt die drei Stufen, die beim Einrichten schiefgehen können, damit die
Fehlermeldung in die richtige Richtung zeigt:

1. Erreichbarkeit von Host und Port
2. STARTTLS
3. Anmeldung mit Benutzer und Passwort

Ein "Anmeldung abgelehnt" bedeutet fast immer ein falsches Passwort oder
einen falschen Benutzernamen - nicht, dass die Verbindung nicht steht. Ohne
diese Trennung sucht man leicht an der falschen Stelle.
"""

import smtplib
import sys

from app.core.config import get_settings

settings = get_settings()


def main() -> int:
    print(f"  Server:   {settings.smtp_host}:{settings.smtp_port}")
    print(f"  Benutzer: {settings.smtp_user or '(keiner)'}")

    if not settings.smtp_user:
        print("  Kein Benutzer gesetzt - es wird ohne Anmeldung verschickt.")
        return 0

    try:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    except OSError as exc:
        print(f"  FEHLER: Server nicht erreichbar ({exc}).", file=sys.stderr)
        print("  Host und Port prüfen. Bei den meisten Anbietern ist es 587.", file=sys.stderr)
        return 1

    with client:
        client.ehlo()
        if settings.smtp_use_tls:
            try:
                client.starttls()
                client.ehlo()
            except smtplib.SMTPException as exc:
                print(f"  FEHLER: STARTTLS abgelehnt ({exc}).", file=sys.stderr)
                return 1

        try:
            client.login(settings.smtp_user, settings.smtp_password)
        except smtplib.SMTPAuthenticationError as exc:
            print(f"  FEHLER: Anmeldung abgelehnt ({exc.smtp_code}).", file=sys.stderr)
            print("  Benutzername ist bei den meisten Anbietern die volle", file=sys.stderr)
            print("  E-Mail-Adresse. Sonst das Passwort des POSTFACHS prüfen -", file=sys.stderr)
            print("  das ist ein anderes als das des Kundenkontos.", file=sys.stderr)
            return 1

    print("  Anmeldung erfolgreich.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
