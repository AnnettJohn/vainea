#!/bin/sh
# Frischen Ubuntu-24.04-Server für den VAINEA-Shop vorbereiten.
# Als root auf der noch leeren Maschine ausführen:
#
#   curl -fsSL <raw-url>/scripts/provision-server.sh | sh -s -- --user vainea
#
# oder nach dem Klonen des Repos:
#
#   sudo ./scripts/provision-server.sh --user vainea
#
# Mehrfach ausführbar: jeder Schritt prüft erst, ob er schon erledigt ist.
#
# Das Skript richtet BEWUSST nichts ein, was Zugangsdaten braucht - keine
# .env, kein Mollie-Key, kein Admin-Account. Das bleibt manuell, siehe README.
set -eu

DEPLOY_USER="vainea"
while [ $# -gt 0 ]; do
    case "$1" in
        --user) DEPLOY_USER="$2"; shift 2 ;;
        *) echo "Unbekannte Option: $1" >&2; exit 1 ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte als root ausführen (oder mit sudo)." >&2
    exit 1
fi

say() { printf '\n== %s\n' "$1"; }

say "Systempakete aktualisieren"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq ca-certificates curl ufw unattended-upgrades

say "Automatische Sicherheitsupdates aktivieren"
dpkg-reconfigure -f noninteractive unattended-upgrades

say "Deploy-Benutzer '$DEPLOY_USER'"
if id "$DEPLOY_USER" >/dev/null 2>&1; then
    echo "existiert bereits"
else
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
    usermod -aG sudo "$DEPLOY_USER"
fi

# SSH-Schlüssel von root übernehmen, damit der Login sofort funktioniert -
# ohne das sperrt der nächste Schritt den Zugang aus.
if [ -f /root/.ssh/authorized_keys ]; then
    install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
    install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" \
        /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
    echo "SSH-Schlüssel nach /home/$DEPLOY_USER/.ssh übernommen"
else
    echo "WARNUNG: /root/.ssh/authorized_keys fehlt - vor dem SSH-Härten" >&2
    echo "         unbedingt einen Schlüssel für $DEPLOY_USER hinterlegen!" >&2
fi

say "Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ufw status

say "Docker"
if command -v docker >/dev/null 2>&1; then
    echo "bereits installiert: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh
fi
usermod -aG docker "$DEPLOY_USER"

say "Nächtliches Backup einrichten"
# 03:20 statt einer vollen Stunde: verteilt die Last und kollidiert nicht mit
# den zahlreichen Cronjobs, die üblicherweise auf :00 stehen.
cron_line="20 3 * * * cd /home/$DEPLOY_USER/vainea/shop && ./scripts/backup.sh >> /var/log/vainea-backup.log 2>&1"
if crontab -u "$DEPLOY_USER" -l 2>/dev/null | grep -qF "scripts/backup.sh"; then
    echo "Cronjob existiert bereits"
else
    (crontab -u "$DEPLOY_USER" -l 2>/dev/null || true; echo "$cron_line") | crontab -u "$DEPLOY_USER" -
    echo "Cronjob angelegt: täglich 03:20"
fi
touch /var/log/vainea-backup.log
chown "$DEPLOY_USER" /var/log/vainea-backup.log

cat <<TXT

== Fertig. Was jetzt noch manuell zu tun ist:

1. SSH härten: in /etc/ssh/sshd_config
       PermitRootLogin no
       PasswordAuthentication no
   danach 'systemctl restart ssh'.
   VORHER in einer zweiten Sitzung testen, dass der Login als
   '$DEPLOY_USER' funktioniert - sonst sperrst du dich aus.

2. Als '$DEPLOY_USER' neu anmelden (die Docker-Gruppe greift erst dann):
       git clone <repo-url> ~/vainea
       cd ~/vainea/shop
       cp .env.example .env    # Werte eintragen, siehe README
       # Domain(s) im Caddyfile anpassen
       docker compose up -d --build

3. DNS auf diese Maschine zeigen lassen, sonst bekommt Caddy kein
   Zertifikat.

4. Backups an einen zweiten Ort kopieren. Der Cronjob legt sie unter
   ~/vainea/shop/backups ab - auf derselben Platte wie die Datenbank.
   Das schützt vor Fehlbedienung, nicht vor Serververlust.

TXT
