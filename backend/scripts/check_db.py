"""Verify the configured database: connect, enable pgvector, create tables, list them.

Run from backend/:  python -m scripts.check_db
"""
import sys

from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine, init_db


def main() -> int:
    if not settings.is_postgres:
        print("DATABASE_URL is not a PostgreSQL URL (using SQLite). Paste your Neon string into backend/.env.")
        return 1
    print("Connecting to", engine.url.render_as_string(hide_password=True))
    try:
        with engine.connect() as conn:
            print("Server:", conn.execute(text("SELECT version()")).scalar().split(",")[0])
    except Exception as exc:  # show the driver's reason (bad password, host, SSL...)
        print("Connection FAILED:", getattr(exc, "orig", exc))
        return 1
    init_db()
    with engine.connect() as conn:
        vec = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")).scalar()
    print("pgvector:", vec or "NOT INSTALLED")
    tables = sorted(inspect(engine).get_table_names())
    print(f"{len(tables)} tables:", ", ".join(tables))
    return 0 if vec and len(tables) >= 12 else 1


if __name__ == "__main__":
    sys.exit(main())
