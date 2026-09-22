#!/bin/sh
# Mollie-Zugangsdaten eintragen und die Anbindung prüfen.
#
#   ./scripts/set-mollie.sh
#
# Fragt den API-Schlüssel interaktiv ab, damit er nicht in der
# Shell-History, im Terminal-Protokoll oder in einem Chatverlauf landet.
set -eu

cd "$(dirname "$0")/.."

[ -f .env ] || { echo ".env nicht gefunden." >&2; exit 1; }

aktuell() { grep "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- ; }

echo "Mollie einrichten. Den Schlüssel findest du im Mollie-Dashboard"
echo "unter Entwickler -> API-Keys."
echo
echo "Zum Ausprobieren den test_-Schlüssel nehmen: damit laufen Zahlungen"
echo "vollständig durch, ohne dass Geld bewegt wird."
echo

# Verdeckt und zweimal - ein Vertipper faellt sonst erst beim Bezahlen auf.
schluessel_lesen() {
    stty -echo 2>/dev/null || true
    printf '%s: ' "$1" > /dev/tty
    read -r eingabe < /dev/tty
    stty echo 2>/dev/null || true
    printf '\n' > /dev/tty
    printf '%s' "$eingabe"
}

while : ; do
    KEY=$(schluessel_lesen "API-Schlüssel")
    KEY2=$(schluessel_lesen "Schlüssel wiederholen")
    if [ "$KEY" != "$KEY2" ]; then
        echo "Die Eingaben stimmen nicht ueberein. Nochmal." > /dev/tty
        continue
    fi
    case "$KEY" in
        test_*|live_*) break ;;
        "") echo "Kein Schluessel eingegeben." > /dev/tty ;;
        *)  echo "Ein Mollie-Schluessel beginnt mit test_ oder live_." > /dev/tty ;;
    esac
done

case "$KEY" in
    live_*)
        echo > /dev/tty
        echo "ACHTUNG: Das ist ein LIVE-Schluessel. Zahlungen werden echt" > /dev/tty
        echo "abgebucht." > /dev/tty
        printf "Zum Fortfahren 'live' eingeben: " > /dev/tty
        read -r bestaetigung < /dev/tty
        [ "$bestaetigung" = "live" ] || { echo "Abgebrochen." >&2; exit 1; }
        ;;
esac

VORGABE=$(aktuell MOLLIE_WEBHOOK_URL)
[ -n "$VORGABE" ] || VORGABE="https://vainea.de/checkout/webhook"
printf 'Webhook-URL [%s]: ' "$VORGABE" > /dev/tty
read -r HOOK < /dev/tty
[ -n "$HOOK" ] || HOOK="$VORGABE"

setze() {
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
setze MOLLIE_API_KEY "$KEY"
setze MOLLIE_WEBHOOK_URL "$HOOK"
chmod 600 .env

echo
echo "Eingetragen. Container neu starten ..."
docker compose up -d app > /dev/null 2>&1
sleep 12

echo
echo "Pruefe die Anbindung ..."
docker compose exec -T app python -m scripts.check_mollie < /dev/null
