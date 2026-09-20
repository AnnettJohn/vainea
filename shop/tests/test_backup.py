"""Backup und Restore gegen eine echte Postgres-Instanz durchspielen.

Die Shell-Skripte selbst lassen sich hier nicht ausführen - sie rufen
`docker compose` auf, und auf der Entwicklungsmaschine läuft kein Docker.
Was sich aber prüfen lässt, ist der riskante Teil: die pg_dump- und
pg_restore-Parameter. Die Tests lesen sie deshalb direkt aus den Skripten
aus, statt sie zu wiederholen - ändert jemand die Skripte, prüft der Test
automatisch die neuen Parameter.
"""

import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile

import pgserver
import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"


def _args_from_script(filename: str, variable: str) -> list[str]:
    """Die als Konstante hinterlegte Parameterzeile aus einem Skript holen."""
    text = (SCRIPTS / filename).read_text()
    match = re.search(rf'^{variable}="([^"]+)"$', text, re.M)
    assert match, f"{variable} nicht in {filename} gefunden"
    return shlex.split(match.group(1))


@pytest.fixture(scope="module")
def pg_bin() -> pathlib.Path:
    """Verzeichnis mit pg_dump/pg_restore/psql aus der pgserver-Distribution."""
    return pathlib.Path(pgserver.__file__).parent / "pginstall" / "bin"


def test_backup_script_uses_custom_format():
    """custom-Format ist Voraussetzung dafür, dass restore.sh mit pg_restore
    und --single-transaction arbeiten kann."""
    args = _args_from_script("backup.sh", "PG_DUMP_ARGS")
    assert "--format=custom" in args
    assert "--no-owner" in args


def test_restore_script_is_transactional():
    """Ohne --single-transaction bliebe bei einem Fehler eine halb
    wiederhergestellte Datenbank zurück."""
    args = _args_from_script("restore.sh", "PG_RESTORE_ARGS")
    assert "--single-transaction" in args
    assert "--clean" in args
    assert "--if-exists" in args


def test_backup_restore_roundtrip(tmp_path, pg_bin):
    """Der eigentliche Test: Daten anlegen, dumpen, zerstören, zurückspielen
    - mit genau den Parametern, die in den Skripten stehen."""
    # Kurzes Temp-Verzeichnis statt tmp_path: der Postgres-Socket liegt im
    # Datenverzeichnis, und macOS begrenzt Unix-Socket-Pfade auf ~104 Zeichen
    # - die Pfade von pytest sind allein schon länger.
    datadir = tempfile.mkdtemp(prefix="vainea_bk_")
    srv = pgserver.get_server(datadir, cleanup_mode="delete")
    try:
        srv.psql("CREATE DATABASE backup_test;")
        socket_dir = datadir

        def psql(db: str, sql: str) -> str:
            return subprocess.run(
                [str(pg_bin / "psql"), "-h", socket_dir, "-U", "postgres", "-d", db, "-t", "-A", "-c", sql],
                capture_output=True, text=True, check=True,
            ).stdout.strip()

        psql("backup_test", "CREATE TABLE orders (id int primary key, total numeric);")
        psql("backup_test", "INSERT INTO orders VALUES (1, 189.00), (2, 49.00);")
        assert psql("backup_test", "SELECT count(*) FROM orders;") == "2"

        dump = tmp_path / "test.dump"
        dump_args = _args_from_script("backup.sh", "PG_DUMP_ARGS")
        with dump.open("wb") as fh:
            subprocess.run(
                [str(pg_bin / "pg_dump"), "-h", socket_dir, "-U", "postgres", *dump_args, "backup_test"],
                stdout=fh, check=True,
            )
        assert dump.stat().st_size > 0

        # Datenverlust simulieren.
        psql("backup_test", "DROP TABLE orders;")
        assert psql("backup_test", "SELECT count(*) FROM information_schema.tables WHERE table_name='orders';") == "0"

        restore_args = _args_from_script("restore.sh", "PG_RESTORE_ARGS")
        with dump.open("rb") as fh:
            result = subprocess.run(
                [str(pg_bin / "pg_restore"), "-h", socket_dir, "-U", "postgres",
                 "-d", "backup_test", *restore_args],
                stdin=fh, capture_output=True, text=True,
            )
        assert result.returncode == 0, result.stderr

        assert psql("backup_test", "SELECT count(*) FROM orders;") == "2"
        assert psql("backup_test", "SELECT total FROM orders WHERE id = 1;") == "189.00"
    finally:
        srv.cleanup()
        shutil.rmtree(datadir, ignore_errors=True)


def test_shell_scripts_have_valid_syntax():
    """Die Skripte laufen auf dem Server, nicht in CI - ein Syntaxfehler
    fiele sonst erst im Ernstfall auf, beim Restore."""
    for script in sorted(SCRIPTS.glob("*.sh")):
        result = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, f"{script.name}: {result.stderr}"


def test_restore_script_requires_confirmation():
    """Ein versehentliches restore.sh darf die Produktivdaten nicht
    kommentarlos überschreiben."""
    text = (SCRIPTS / "restore.sh").read_text()
    assert "read -r answer" in text
    assert 'answer" != "restore"' in text
