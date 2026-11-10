"""
Migration: add state + error_message columns to the sources table.
Run once: python scripts/migrate_add_source_state.py
Idempotent: safe to run multiple times.
"""
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from backend.database import engine  # reads DATABASE_URL from .env – never printed

MIGRATIONS = [
    (
        "sources.state",
        "SELECT 1 FROM information_schema.columns WHERE table_name='sources' AND column_name='state'",
        "ALTER TABLE sources ADD COLUMN state VARCHAR(50) NOT NULL DEFAULT 'ready'",
    ),
    (
        "sources.error_message",
        "SELECT 1 FROM information_schema.columns WHERE table_name='sources' AND column_name='error_message'",
        "ALTER TABLE sources ADD COLUMN error_message TEXT",
    ),
]

with engine.connect() as conn:
    for col_desc, check_sql, alter_sql in MIGRATIONS:
        exists = conn.execute(text(check_sql)).fetchone()
        if exists:
            print(f"  SKIP   {col_desc} – already exists")
        else:
            conn.execute(text(alter_sql))
            conn.commit()
            print(f"  ADDED  {col_desc}")

    # Verify
    rows = conn.execute(text(
        "SELECT column_name, data_type, column_default "
        "FROM information_schema.columns "
        "WHERE table_name='sources' AND column_name IN ('state','error_message') "
        "ORDER BY column_name"
    )).fetchall()
    print("\nVerification:")
    for r in rows:
        print(f"  col={r[0]}  type={r[1]}  default={r[2]}")
    if len(rows) == 2:
        print("\nSUCCESS: migration complete — both columns present.")
    else:
        print(f"\nWARNING: only {len(rows)} of 2 columns found.")
        sys.exit(1)
