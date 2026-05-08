# /dashboard — Build Executive Dashboard

Create `dashboard/app.py` — a single-page Streamlit executive dashboard.

## Purpose
Answer the CEO question: *"How healthy is AlpenRail this quarter? Where should I be paying attention?"*

## Layout (implement exactly this structure)

```
st.set_page_config(layout="wide", page_title="AlpenRail Executive Dashboard")

Sidebar:
  - Year selector (2024 / 2025 / Both)
  - Quarter selector (Q1 / Q2 / Q3 / Q4 / Full Year)

Row 1 — KPI Cards (use st.metric with delta):
  [Total Revenue CHF] [On-Time %] [Avg Ticket Price CHF] [Total Passengers]

Row 2 — two columns:
  Left:  Monthly ticket revenue line chart (plotly) — current vs prior year overlay
  Right: On-time % by route horizontal bar chart (red = <85%, amber = 85-93%, green = >93%)

Row 3 — two columns:
  Left:  Avg ticket price by channel — bar chart
  Right: Delay minutes vs precipitation scatter (all routes, coloured by route)

Row 4 — full width:
  Loyalty tier avg annual spend — grouped bar (GA / Halbtax / none) with annotation
  showing the CHF gap between top and bottom tier

Row 5 — two columns:
  Left:  Top 5 stations by boardings — horizontal bar
  Right: Partner bookings by type over time — stacked area chart
```

## Implementation Rules
- Import connection at top: `import sys; sys.path.insert(0, '..'); from scripts.db import query`
- Wrap every query in a function decorated with `@st.cache_data(ttl=3600)`
- All charts via `plotly express` — use `st.plotly_chart(fig, use_container_width=True)`
- Apply sidebar filters to every query using WHERE clauses, not post-hoc pandas filtering
- Use AlpenRail colour palette: primary `#1B3A6B` (navy), accent `#E63946` (red), neutral `#F4F1DE`
- Add a footer: `"AlpenRail Analytics Dashboard | Data: 2024–2025 | Built with Streamlit"`

## Launch command (print this at the end)
```bash
streamlit run dashboard/app.py
```
