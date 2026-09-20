#!/bin/sh
# Datenbank-Backup für den Compose-Stack. Auf dem Server per Cron aufrufen,
# siehe README ("Backups").
#
#   ./scripts/backup.sh            # Dump nach ./backups, alte aufräumen
#   BACKUP_DIR=/mnt/x ./scripts/backup.sh
#
# pg_dump läuft bewusst IM postgres-Container: nur dort ist garantiert die
# zur Serverversion passende pg_dump-Binary vorhanden. Ein auf dem Host
# installiertes pg_dump einer älteren Hauptversion verweigert den Dump.
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-vainea}"
POSTGRES_DB="${POSTGRES_DB:-vainea}"

# --- Dump-Parameter (werden von tests/test_backup.py ausgelesen) ----------
# custom-Format statt reinem SQL: komprimiert bereits selbst und lässt sich
# mit pg_restore selektiv und transaktional zurückspielen.
# --no-owner/--no-privileges, damit der Dump auch in eine Datenbank mit
# anderem Rollennamen eingespielt werden kann (z. B. beim Umzug).
PG_DUMP_ARGS="--format=custom --no-owner --no-privileges"
# --- Ende Dump-Parameter -------------------------------------------------

cd "$(dirname "$0")/.."

mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/vainea-$(date +%Y%m%d-%H%M%S).dump"

# Erst in eine temporäre Datei schreiben und erst bei Erfolg umbenennen -
# sonst bleibt bei einem Abbruch ein halber Dump liegen, der wie ein
# gültiges Backup aussieht.
tmp="$target.partial"
# shellcheck disable=SC2086
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" $PG_DUMP_ARGS "$POSTGRES_DB" > "$tmp"

if [ ! -s "$tmp" ]; then
    rm -f "$tmp"
    echo "Backup fehlgeschlagen: Dump ist leer." >&2
    exit 1
fi

mv "$tmp" "$target"
echo "Backup geschrieben: $target ($(du -h "$target" | cut -f1))"

# Alte Dumps entfernen. Läuft nach dem erfolgreichen Dump, damit bei einem
# Fehlschlag nicht auch noch die vorhandenen Backups gelöscht werden.
deleted=$(find "$BACKUP_DIR" -name 'vainea-*.dump' -type f -mtime "+$RETENTION_DAYS" -print -delete | wc -l)
echo "Aufbewahrung: $RETENTION_DAYS Tage, $deleted alte Dump(s) entfernt."

# Offsite-Kopie in den Objektspeicher. Läuft im app-Container, weil dort
# boto3 und die S3-Zugangsdaten liegen; ./backups ist dort nach /backups
# gemountet (siehe docker-compose.yml). Ein fehlgeschlagener Upload soll das
# lokale Backup nicht entwerten, deshalb kein set -e an dieser Stelle.
if docker compose exec -T app python -m scripts.upload_backup "/backups/$(basename "$target")"; then
    :
else
    status=$?
    if [ "$status" -eq 2 ]; then
        echo
        echo "HINWEIS: Kein Offsite-Backup konfiguriert (S3_BACKUP_BUCKET)."
        echo "Dieses Backup liegt auf demselben Server wie die Datenbank und"
        echo "schützt damit nicht vor dem Verlust des Servers."
    else
        echo "WARNUNG: Offsite-Upload fehlgeschlagen (Exit $status)." >&2
        echo "         Das lokale Backup unter $target ist trotzdem gültig." >&2
    fi
fi
