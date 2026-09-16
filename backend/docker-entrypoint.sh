#!/bin/sh
# Container entrypoint: bring the database up to date, ensure the bootstrap
# organization and Super Admin exist, then hand off to the API server.
#
# Cloud Run has no separate migration step — the revision of the app that boots
# is the only thing that touches the database — so the schema is applied here,
# on startup, rather than from a developer's laptop.
set -e

echo "[entrypoint] Applying database migrations..."
alembic upgrade head

# Idempotent: scripts/seed.py creates the organization and the Super Admin only
# when they are missing, so this is a no-op on every boot after the first.
# Deliberately non-fatal — a seeding problem should be visible in the logs, not
# a crash-loop that takes the whole API down.
echo "[entrypoint] Seeding baseline data..."
if ! python -m scripts.seed; then
    echo "[entrypoint] WARNING: seeding failed; continuing startup." >&2
fi

echo "[entrypoint] Starting API on port ${PORT:-8000}..."
# --proxy-headers: behind Cloud Run's front end, the client address only
# survives on X-Forwarded-For. Without it every request looks like it came from
# the proxy and the per-IP login rate limit is shared by all users at once.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
