"""Datenbank-Dump in den Objektspeicher kopieren (Offsite-Backup).

Wird von scripts/backup.sh aufgerufen, sobald S3_BACKUP_BUCKET gesetzt ist.
Ein Backup auf derselben Maschine schuetzt vor Fehlbedienung, nicht vor dem
Verlust des Servers - erst die Kopie an einem zweiten Ort tut das.

    python -m scripts.upload_backup backups/vainea-20260920-032000.dump

Der Bucket muss ein ANDERER sein als der fuer die Produktbilder: dieser ist
absichtlich oeffentlich lesbar, und ein Datenbank-Dump enthaelt Namen,
Adressen, E-Mail-Adressen und Bestellhistorien. Das Skript bricht ab, wenn
beide Werte uebereinstimmen.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.storage import get_s3_client

settings = get_settings()

BACKUP_PREFIX = "db/"


class BackupUploadError(RuntimeError):
    pass


def check_target() -> str:
    """Zielbucket pruefen. Liefert den Bucketnamen oder wirft."""
    bucket = settings.s3_backup_bucket
    if not bucket:
        raise BackupUploadError(
            "S3_BACKUP_BUCKET ist nicht gesetzt - kein Offsite-Backup konfiguriert."
        )
    if settings.s3_bucket and bucket == settings.s3_bucket:
        raise BackupUploadError(
            "S3_BACKUP_BUCKET zeigt auf denselben Bucket wie die Produktbilder. "
            "Der ist oeffentlich lesbar; ein Datenbank-Dump darf dort nicht liegen. "
            "Bitte einen eigenen, privaten Bucket anlegen."
        )
    if not settings.s3_endpoint_url or not settings.s3_access_key_id:
        raise BackupUploadError("Objektspeicher ist nicht vollstaendig konfiguriert (S3_*).")
    return bucket


def upload(client, bucket: str, dump: Path) -> str:
    """Dump hochladen und die Groesse gegenpruefen.

    Ein abgebrochener Upload hinterlaesst sonst ein Objekt, das wie ein
    Backup aussieht, aber unvollstaendig ist - und das faellt erst beim
    Zurueckspielen auf.
    """
    key = f"{BACKUP_PREFIX}{dump.name}"
    # Explizit privat: der Bucket sollte es ohnehin sein, aber die ACL hier
    # zu setzen macht die Absicht unmissverstaendlich und faengt einen
    # falsch konfigurierten Bucket ab.
    client.upload_file(str(dump), bucket, key, ExtraArgs={"ACL": "private"})

    remote_size = client.head_object(Bucket=bucket, Key=key)["ContentLength"]
    local_size = dump.stat().st_size
    if remote_size != local_size:
        raise BackupUploadError(
            f"Upload unvollstaendig: {remote_size} von {local_size} Bytes angekommen."
        )
    return key


def prune(client, bucket: str, retention_days: int) -> list[str]:
    """Alte Dumps im Bucket entfernen. Gibt die geloeschten Keys zurueck."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted: list[str] = []

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=BACKUP_PREFIX):
        for obj in page.get("Contents", []):
            if obj["LastModified"] < cutoff:
                client.delete_object(Bucket=bucket, Key=obj["Key"])
                deleted.append(obj["Key"])
    return deleted


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Aufruf: python -m scripts.upload_backup <dump-datei>", file=sys.stderr)
        return 1

    dump = Path(argv[1])
    if not dump.is_file():
        print(f"Dump nicht gefunden: {dump}", file=sys.stderr)
        return 1

    try:
        bucket = check_target()
    except BackupUploadError as exc:
        print(f"Offsite-Backup uebersprungen: {exc}", file=sys.stderr)
        return 2

    client = get_s3_client()
    try:
        key = upload(client, bucket, dump)
    except BackupUploadError as exc:
        print(f"Offsite-Backup fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    print(f"Offsite-Backup: s3://{bucket}/{key} ({dump.stat().st_size} Bytes)")

    if settings.backup_retention_days > 0:
        for removed in prune(client, bucket, settings.backup_retention_days):
            print(f"  entfernt: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
