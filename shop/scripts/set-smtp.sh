#!/bin/sh
# SMTP-Zugangsdaten in die .env eintragen und den Versand testen.
#
#   ./scripts/set-smtp.sh
#
# Fragt interaktiv ab, damit das Passwort nicht in der Shell-History,
# nicht im Terminal-Protokoll und nicht in einem Chatverlauf landet.
set -eu

cd "$(dirname "$0")/.."

[ -f .env ] || { echo ".env nicht gefunden - erst aus .env.example anlegen." >&2; exit 1; }

frage() {
    # $1 Beschriftung, $2 Vorgabe
    if [ -n "${2:-}" ]; then
        printf '%s [%s]: ' "$1" "$2" > /dev/tty
    else
        printf '%s: ' "$1" > /dev/tty
    fi
    read -r antwort < /dev/tty
    [ -n "$antwort" ] || antwort="${2:-}"
    printf '%s' "$antwort"
}

aktuell() { grep "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- ; }

echo "SMTP-Zugangsdaten eintragen. Enter übernimmt den Wert in Klammern."
echo

HOST=$(frage "SMTP-Server" "$(aktuell SMTP_HOST)")
PORT=$(frage "Port (587 = STARTTLS)" "587")
USER=$(frage "Benutzer (meist die volle E-Mail-Adresse)" "$(aktuell SMTP_USER)")

# Passwort verdeckt einlesen.
stty -echo 2>/dev/null || true
printf 'Passwort: ' > /dev/tty
read -r PASS < /dev/tty
stty echo 2>/dev/null || true
printf '\n' > /dev/tty

FROM=$(frage "Absenderadresse" "$(aktuell SMTP_FROM_EMAIL)")

[ -n "$HOST" ] && [ -n "$USER" ] && [ -n "$PASS" ] || {
    echo "Abgebrochen: Server, Benutzer und Passwort sind Pflicht." >&2
    exit 1
}

setze() {
    # Schlüssel ersetzen oder anhängen. Der Wert wird über eine Datei
    # eingespielt, damit Sonderzeichen im Passwort nichts zerschießen.
    schluessel="$1"; wert="$2"
    if grep -q "^$schluessel=" .env; then
        grep -v "^$schluessel=" .env > .env.tmp
    else
        cp .env .env.tmp
    fi
    printf '%s=%s\n' "$schluessel" "$wert" >> .env.tmp
    mv .env.tmp .env
}

cp .env ".env.backup-$(date +%Y%m%d-%H%M%S)"
setze SMTP_HOST "$HOST"
setze SMTP_PORT "$PORT"
setze SMTP_USER "$USER"
setze SMTP_PASSWORD "$PASS"
setze SMTP_USE_TLS "true"
setze SMTP_FROM_EMAIL "$FROM"
chmod 600 .env

echo
echo "Eingetragen. Container neu starten, damit die Werte greifen ..."
docker compose up -d app > /dev/null 2>&1
sleep 12

echo
ZIEL=$(frage "Testmail senden an (leer = überspringen)" "")
if [ -n "$ZIEL" ]; then
    docker compose exec -T app python -m scripts.send_test_email "$ZIEL" < /dev/null
fi
