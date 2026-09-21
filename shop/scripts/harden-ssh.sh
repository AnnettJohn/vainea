#!/bin/sh
# SSH absichern: Root-Login und Passwort-Anmeldung abschalten.
#
#   sudo ./scripts/harden-ssh.sh
#
# Warum ein eigenes Skript und nicht schnell ein sed:
#
# 1. Ubuntu 24.04 startet SSH über ssh.socket, nicht über ssh.service. Ein
#    'systemctl restart ssh' verdrängt den Socket und hinterlässt einen
#    Server, auf dem niemand mehr auf Port 22 lauscht. Bei Socket-Aktivierung
#    liest jede neue Verbindung die Konfiguration ohnehin frisch ein - ein
#    Neustart ist gar nicht nötig.
# 2. Die Einstellungen gehören in eine Ablage unter sshd_config.d/. Die wird
#    per Include ganz oben eingebunden, und in sshd gilt der ERSTE Treffer.
#    Der Dateiname beginnt deshalb mit 10-, damit er vor eventuellen
#    Cloud-Init-Ablagen (meist 50-) gelesen wird.
# 3. Ein Zeitschalter nimmt die Änderung nach fünf Minuten automatisch
#    zurück. Wer sich aussperrt, wartet fünf Minuten statt zur Notfall-
#    konsole des Anbieters zu greifen.
set -eu

CONF=/etc/ssh/sshd_config.d/10-hardening.conf
REVERT_MINUTES="${REVERT_MINUTES:-5}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte mit sudo ausführen." >&2
    exit 1
fi

cat > "$CONF" <<'CONFEOF'
# Von scripts/harden-ssh.sh angelegt.
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
CONFEOF
chmod 644 "$CONF"

if ! sshd -t; then
    echo "Konfiguration ungültig - Änderung wird verworfen." >&2
    rm -f "$CONF"
    exit 1
fi

# Sicherheitsnetz: nimmt die Datei zurück, falls sie nicht rechtzeitig
# bestätigt wird. 'at' ist nicht überall da, deshalb ein abgesetzter Prozess.
( sleep "$((REVERT_MINUTES * 60))"
  if [ -f "$CONF.bestaetigt" ]; then
      rm -f "$CONF.bestaetigt"
  else
      rm -f "$CONF"
      logger -t harden-ssh "Härtung nach $REVERT_MINUTES Minuten ohne Bestätigung zurückgenommen"
  fi ) >/dev/null 2>&1 &

echo "Härtung aktiv. Effektiv geltende Werte:"
sshd -T | grep -E "^(permitrootlogin|passwordauthentication)"
cat <<TXT

WICHTIG: Teste JETZT in einem zweiten Fenster, dass du dich noch anmelden
kannst. Klappt es, bestätige innerhalb von $REVERT_MINUTES Minuten mit:

    sudo touch $CONF.bestaetigt

Ohne Bestätigung wird die Änderung automatisch zurückgenommen und alles ist
wie vorher.
TXT
