#!/bin/sh
# Container entrypoint: bring the database up to date, ensure the bootstrap
# organization and Super Admin exist, then hand off to the API server.
#
# Cloud Run has no separate migration step — the revision of the app that boots
# is the only thing that touches the database — so the schema is applied here,
# on startup, rather than from a developer's laptop.
set -e

# Migrations and seeding run under a Postgres advisory lock so that instances
# starting at the same moment cannot race each other -- see scripts/startup.py.
python -m scripts.startup

echo "[entrypoint] Starting API on port ${PORT:-8000}..."
# --no-proxy-headers: uvicorn would otherwise take the *leftmost*
# X-Forwarded-For entry, which the client writes itself, and every per-IP rate
# limit could be walked past by sending a fresh fake address each time. The real
# client address is read from the right-hand end instead, by
# app/core/client_ip.py, using the TRUSTED_PROXY_HOPS setting.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --no-proxy-headers
