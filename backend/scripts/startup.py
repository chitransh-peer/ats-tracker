"""Bring the database up to date and bootstrap baseline data, once.

Run from the container entrypoint, so it executes on *every* instance start.
On a managed runtime that autoscales, several instances can boot at the same
moment -- most likely right after a deploy, which is exactly when there is a
pending migration to apply. Two concurrent `alembic upgrade head` runs against
one database race: one wins, the other fails on an object that now already
exists, and that instance never becomes healthy.

A Postgres advisory lock serialises them. The first instance migrates while the
others wait, and they then find the schema already at head and continue. The
lock lives on its own connection held open for the duration, and is released
when that connection closes -- including if the process is killed.

Usage: python -m scripts.startup
"""

import sys

from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.db.session import engine

# Any stable 64-bit value; it just has to be one no other advisory lock in this
# database uses. Derived from the application name rather than a magic number.
_LOCK_KEY = 8_014_552_310_771_004


def run() -> None:
    with engine.connect() as connection:
        print("[startup] Waiting for the migration lock...", flush=True)
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _LOCK_KEY})
        connection.commit()
        try:
            print("[startup] Applying database migrations...", flush=True)
            config = Config("alembic.ini")
            command.upgrade(config, "head")

            print("[startup] Seeding baseline data...", flush=True)
            # Imported here, after migrations: the seed touches ORM models whose
            # tables may not exist yet on a first-ever boot.
            from scripts.seed import run as seed

            try:
                seed()
            except Exception:
                # A seeding problem should be visible in the logs, not a
                # crash-loop that takes the whole API down with it.
                import traceback

                traceback.print_exc()
                print("[startup] WARNING: seeding failed; continuing startup.", file=sys.stderr, flush=True)
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
            connection.commit()


if __name__ == "__main__":
    run()
