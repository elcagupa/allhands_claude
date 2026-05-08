# /setup — Install Dependencies & Validate Project

Run this once when starting the project.

## Steps

1. Install all Python dependencies:
```bash
pip install -r requirements.txt
```

2. Verify DuckDB can read the parquet files by running `scripts/db.py` directly:
```bash
python scripts/db.py
```
If any tables show ✗, tell the user which files are missing from `./data/`.

3. Confirm the data date range spans 2024–2025:
```python
from scripts.db import query
print(query("SELECT MIN(date), MAX(date) FROM journeys"))
print(query("SELECT MIN(sale_date), MAX(sale_date) FROM tickets"))
```

4. Print a success summary:
```
✓ Dependencies installed
✓ N/8 parquet files found
✓ Date range: 2024-01-01 → 2025-12-31
Ready — run /audit next, then /qa, then /dashboard
```

If any step fails, explain exactly what the user needs to do to fix it.
