#!/bin/sh
# Datenbank aus einem Dump wiederherstellen.
#
#   ./scripts/restore.sh backups/vainea-20260920-030000.dump
#
# ACHTUNG: Das überschreibt den aktuellen Datenbestand. Bestellungen, Konten
# und Admin-Inhalte, die nach dem Dump entstanden sind, gehen verloren.
set -eu

POSTGRES_USER="${POSTGRES_USER:-vainea}"
POSTGRES_DB="${POSTGRES_DB:-vainea}"

# --- Restore-Parameter (werden von tests/test_backup.py ausgelesen) ------
# --clean --if-exists: bestehende Objekte vorher entfernen, ohne an einer
# fehlenden Tabelle zu scheitern.
# --single-transaction: entweder läuft der komplette Restore durch oder gar
# nichts - keine halb wiederhergestellte Datenbank.
PG_RESTORE_ARGS="--clean --if-exists --no-owner --no-privileges --single-transaction"
# --- Ende Restore-Parameter ----------------------------------------------

dump="${1:-}"
if [ -z "$dump" ]; then
    echo "Aufruf: $0 <dump-datei>" >&2
    exit 1
fi
if [ ! -f "$dump" ]; then
    echo "Dump nicht gefunden: $dump" >&2
    exit 1
fi

cd "$(dirname "$0")/.."

echo "Dump:      $dump"
echo "Zieldatenbank: $POSTGRES_DB (im laufenden postgres-Container)"
echo
echo "Der aktuelle Datenbestand wird dabei ÜBERSCHRIEBEN."
printf "Zum Fortfahren 'restore' eingeben: "
read -r answer
if [ "$answer" != "restore" ]; then
    echo "Abgebrochen."
    exit 1
fi

# Die App währenddessen anhalten, sonst schreibt sie in eine Datenbank, die
# gerade unter ihr weggezogen wird.
docker compose stop app

# shellcheck disable=SC2086
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" $PG_RESTORE_ARGS < "$dump"

docker compose start app

echo "Restore abgeschlossen. Migrationsstand prüfen:"
echo "  docker compose exec app alembic current"
