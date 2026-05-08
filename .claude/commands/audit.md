# /audit — Data Audit

Run a full audit of all parquet files in `./data/`.

## Steps

1. Import `scripts/db.py` and call `audit()` to confirm all 8 tables are registered
2. For each table print: row count, column count, column names and dtypes
3. For each table print: null counts per column (flag any column with >1% nulls)
4. For date columns: print min and max date to confirm the 2024–2025 range
5. For numeric columns: print min, mean, max to catch obvious data issues
6. Print a summary table at the end — one row per table

Output the audit as a clean printed report. Do not create any files.
Flag anything suspicious (unexpected nulls, out-of-range dates, negative prices, etc.)
