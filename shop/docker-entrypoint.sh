#!/bin/sh
# Migrationen vor jedem Start anwenden - unkritisch bei einer einzelnen
# Instanz (wie im Pflichtenheft für den Hetzner-Server vorgesehen); bei
# mehreren parallelen Replicas müsste das stattdessen ein separater
# Deploy-Schritt sein, damit nicht mehrere Container gleichzeitig migrieren.
set -e

alembic upgrade head

exec "$@"
