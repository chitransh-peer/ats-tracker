#!/usr/bin/env bash
#
# Create the ATS Tracker schema and seed the first admin user.
#
# 01-create-database.sh creates an EMPTY database. This script fills it:
#   1. alembic upgrade head   -> creates every table
#   2. python -m scripts.seed -> roles, permissions, organization,
#                                pipeline stages, and the super-admin user
#
# Both steps are idempotent and safe to re-run.
#
# There is no startup hook that does this. Skip it and the app boots cleanly
# with no admin account and no pipeline stages — it will look broken with no
# error explaining why.
#
# Run this from the repository root on the application host, after backend/.env
# has a working DATABASE_URL.
#
# Usage:
#   ./deploy/aws/02-init-schema.sh
#   ./deploy/aws/02-init-schema.sh --dev     # use docker-compose.yml instead

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
SERVICE="api"

if [[ "${1:-}" == "--dev" ]]; then
  COMPOSE_FILE="docker-compose.yml"
  SERVICE="backend"
fi

info() { printf '\033[0;36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[0;32m  ok\033[0m %s\n' "$*"; }
die() {
  printf '\033[0;31mERROR\033[0m %s\n' "$*" >&2
  exit 1
}

[[ -f "$COMPOSE_FILE" ]] \
  || die "$COMPOSE_FILE not found. Run this from the repository root."
[[ -f backend/.env ]] \
  || die "backend/.env not found. Copy backend/.env.example and fill it in first."

grep -q '^DATABASE_URL=.\+' backend/.env \
  || die "DATABASE_URL is not set in backend/.env."

if grep -q '^DATABASE_URL=postgres://' backend/.env; then
  die "DATABASE_URL uses 'postgres://'. This app needs 'postgresql+psycopg://' (psycopg 3)."
fi

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

# ------------------------------------------------------- verify connectivity
info "Checking the database is reachable"
compose run --rm --no-deps "$SERVICE" python -c "
import sys
from sqlalchemy import text
from app.db.session import engine
try:
    with engine.connect() as c:
        v = c.execute(text('SHOW server_version')).scalar()
    print(f'  connected to PostgreSQL {v}')
except Exception as exc:
    print(f'  cannot connect: {exc}', file=sys.stderr)
    sys.exit(1)
" || die "Database unreachable. Check DATABASE_URL, the security group, and that RDS is available."
ok "Connection verified"

# --------------------------------------------------------------- migrations
info "Applying migrations (alembic upgrade head)"
compose run --rm --no-deps "$SERVICE" alembic upgrade head
ok "Schema is at the latest revision"

info "Current revision"
compose run --rm --no-deps "$SERVICE" alembic current

# --------------------------------------------------------------------- seed
info "Seeding roles, permissions, organization, stages, and the admin user"
compose run --rm --no-deps "$SERVICE" python -m scripts.seed
ok "Seed complete"

# ------------------------------------------------------------------- verify
info "Verifying the result"
compose run --rm --no-deps "$SERVICE" python -c "
from sqlalchemy import text
from app.db.session import engine

checks = {
    'tables':      \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'\",
    'roles':       'SELECT count(*) FROM roles',
    'permissions': 'SELECT count(*) FROM permissions',
    'users':       'SELECT count(*) FROM users',
    'orgs':        'SELECT count(*) FROM organizations',
    'stages':      'SELECT count(*) FROM stage_template_stages',
}
with engine.connect() as c:
    results = {k: c.execute(text(q)).scalar() for k, q in checks.items()}

for k, v in results.items():
    print(f'  {k:12} {v}')

missing = [k for k, v in results.items() if not v]
if missing:
    raise SystemExit(f'\nEMPTY: {missing} — seeding did not complete correctly.')
print('\n  all core tables populated')
"

cat <<'REPORT'

────────────────────────────────────────────────────────────────────────
 Database initialised
────────────────────────────────────────────────────────────────────────

 Next:
   1. docker compose -f docker-compose.prod.yml up -d
   2. Log in as DEFAULT_SUPER_ADMIN_EMAIL from backend/.env
   3. CHANGE THAT PASSWORD IMMEDIATELY — it is in a file on this host
   4. Settings -> Integrations should show email "Connected"

 On every future deploy, re-run:
   docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

 Re-run the seed when the dev team adds permissions. New entries reach the
 database only through seeding; a restart does not apply them.
────────────────────────────────────────────────────────────────────────

REPORT
