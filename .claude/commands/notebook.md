# /notebook — Scaffold All Notebooks

Create three Jupyter notebooks under `notebooks/`.

## notebooks/01_eda.ipynb

Cell 1 — Setup:
```python
import sys; sys.path.insert(0, '..')
from scripts.db import query, audit
import plotly.express as px
import pandas as pd
```

Cell 2 — Table audit:
```python
audit()
```

Cell 3 — Schema explorer: for each table, show `.dtypes` and `.head(3)` via DuckDB

Cell 4 — Date coverage: confirm all tables span 2024-01-01 → 2025-12-31

Cell 5 — Revenue overview: monthly ticket revenue bar chart

Cell 6 — Null heatmap: seaborn heatmap of null % per column per table

Cell 7 — Distribution plots: histograms for price, delay_min, precip_mm, combo_price

## notebooks/02_qa_sprint.ipynb

One section per question (Q1–Q10).
Each section has:
- A markdown cell with the question number and text
- A code cell with the DuckDB query
- A code cell rendering the plotly chart
- A markdown cell with the written answer (fill in after running)

Pre-populate the SQL stubs from the `/qa` command spec in CLAUDE.md.

## notebooks/03_insights.ipynb

Deep dive notebook — three cells to start:

Cell 1 — Campaign ROI analysis:
Compute conversions / budget_chf per campaign, rank them, chart it.

Cell 2 — Cohort spend by signup year:
Group passengers by YEAR(signup_date), compute their avg annual ticket spend.

Cell 3 — Weather sensitivity index:
For each route compute Pearson r between precip_mm and delay_min,
display as a ranked table with a bar chart.

Leave the rest of the notebook blank for analyst exploration.
