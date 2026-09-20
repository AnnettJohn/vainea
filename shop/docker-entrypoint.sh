#!/bin/sh
# Migrationen vor jedem Start anwenden - unkritisch bei einer einzelnen
# Instanz (wie im Pflichtenheft für den Hetzner-Server vorgesehen); bei
# mehreren parallelen Replicas müsste das stattdessen ein separater
# Deploy-Schritt sein, damit nicht mehrere Container gleichzeitig migrieren.
set -e

alembic upgrade head

# Stammdaten anlegen, damit ein frisch aufgesetzter Server nicht mit einem
# leeren Katalog startet. Der Seed legt nur an, was fehlt, und überschreibt
# nichts - im Admin gepflegte Preise, Texte und Versandtarife überleben also
# jedes Deployment. Mit SKIP_SEED=1 lässt er sich abschalten.
if [ "${SKIP_SEED:-0}" != "1" ]; then
    python -m scripts.seed
fi

exec "$@"
