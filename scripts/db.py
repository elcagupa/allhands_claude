"""
scripts/db.py
─────────────
Central DuckDB connection for AlpenRail Analytics.
Registers all parquet files as views so every notebook and the dashboard
can query them with plain SQL via the `query()` helper.

Usage
-----
    from scripts.db import query, con

    df = query("SELECT COUNT(*) FROM tickets")
"""

import duckdb
import pandas as pd
from pathlib import Path

# Resolve data directory relative to this file
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TABLES = [
    "stations",
    "weather",
    "journeys",
    "passengers",
    "tickets",
    "onboard_sales",
    "partner_bookings",
    "campaigns",
]


def _build_connection() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    missing = []
    for tbl in TABLES:
        p = DATA_DIR / f"{tbl}.parquet"
        if p.exists():
            c.execute(f"CREATE VIEW {tbl} AS SELECT * FROM read_parquet('{p}')")
        else:
            missing.append(tbl)
    if missing:
        print(f"⚠️  Missing parquet files in {DATA_DIR}: {missing}")
        print("   Place your .parquet files in ./data/ and re-import this module.")
    return c


# Module-level singleton — imported once per Python session
con = _build_connection()


def query(sql: str) -> pd.DataFrame:
    """Execute SQL and return a pandas DataFrame."""
    return con.execute(sql).df()


def audit() -> pd.DataFrame:
    """Return a DataFrame with row counts for every registered table."""
    rows = []
    for tbl in TABLES:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            cols = con.execute(f"DESCRIBE {tbl}").df().shape[0]
            rows.append({"table": tbl, "rows": n, "columns": cols, "status": "✓"})
        except Exception as e:
            rows.append({"table": tbl, "rows": None, "columns": None, "status": f"✗ {e}"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(audit().to_string(index=False))
