"""Write database/schema.sql: the PostgreSQL DDL generated from the SQLAlchemy models.

Run from backend/:  python -m scripts.dump_schema
"""
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/edupilot"  # only used to pick the dialect

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import Base  # noqa: E402

dialect = postgresql.dialect()
parts = ["-- EduPilot AI - PostgreSQL schema (generated from app/models.py)\n",
         "CREATE EXTENSION IF NOT EXISTS vector;\n"]
for table in Base.metadata.sorted_tables:
    parts.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
    for index in sorted(table.indexes, key=lambda i: i.name):
        parts.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";\n")

out = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
out.write_text("\n".join(parts))
print(f"Wrote {out}")
