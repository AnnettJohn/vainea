# syntax=docker/dockerfile:1

# ---- Builder: Dependencies in ein eigenständiges venv installieren -----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml ./
COPY app ./app

# Nur die Laufzeit-Abhängigkeiten (kein [dev] mit pytest/ruff/pgserver/aiosmtpd)
# installieren. `pip install .` baut dabei zwangsläufig auch ein Wheel des
# eigenen vainea-shop-Pakets - das enthält aber KEINE Templates/Static-Dateien
# (setuptools bündelt standardmäßig nur .py-Dateien, keine Nicht-Code-Daten
# ohne zusätzliche package_data/MANIFEST.in-Konfiguration). Direkt wieder
# deinstallieren, damit unten nicht versehentlich diese unvollständige Kopie
# statt des frisch kopierten echten Quellcodes verwendet wird - die
# Abhängigkeiten bleiben installiert.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip uninstall --yes vainea-shop

# ---- Runtime: schlankes Image, venv aus dem Builder übernehmen --------
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 vainea
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh && chown -R vainea:vainea /app

USER vainea
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
# --proxy-headers/--forwarded-allow-ips: Ohne das ignoriert uvicorn die
# X-Forwarded-*-Header von Caddy, weil die Anfrage aus dem Docker-Netz kommt
# und nicht von 127.0.0.1. Die App haelt jede Anfrage dann fuer http, und
# request.url_for() erzeugt http-URLs - also falsche Canonical-Angaben,
# Schema.org-URLs und Sitemap-Eintraege auf einer reinen HTTPS-Seite.
# "*" ist hier vertretbar: der Container ist nur ueber Caddy erreichbar
# (expose statt ports), niemand kann die Header direkt setzen.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
