# AlpenRail Analytics — Claude Code Project Instructions

## What This Project Is
You are a data analyst for AlpenRail, a fictional Swiss tourist rail operator.
Two years of operational data (2024–2025) lives in `./data/` as Parquet files.
Your job: answer 10 business questions and build an executive Streamlit dashboard.

---

## Project Structure
```
alpenrail/
├── CLAUDE.md                        ← you are here
├── requirements.txt
├── data/                            ← all 8 .parquet files (user-supplied)
│   ├── stations.parquet
│   ├── weather.parquet
│   ├── journeys.parquet
│   ├── passengers.parquet
│   ├── tickets.parquet
│   ├── onboard_sales.parquet
│   ├── partner_bookings.parquet
│   └── campaigns.parquet
├── scripts/
│   └── db.py                        ← DuckDB connection helper (always import this)
├── notebooks/
│   ├── 01_eda.ipynb                 ← data audit & profiling
│   ├── 02_qa_sprint.ipynb           ← answers to all 10 questions
│   └── 03_insights.ipynb            ← deep dives
├── dashboard/
│   └── app.py                       ← Streamlit executive dashboard
└── outputs/                         ← saved charts (.html) and tables (.csv)
```

---

## Tech Stack & Conventions

| Layer | Library | Notes |
|---|---|---|
| Query engine | **DuckDB** | Query `.parquet` files directly with SQL — always prefer this over pandas for joins |
| DataFrames | **pandas** | Use `.df()` to convert DuckDB results |
| Charts | **plotly express** | All charts must use plotly — consistent across notebooks and dashboard |
| Dashboard | **streamlit** | Single-file `dashboard/app.py` |
| Stats | **scipy / statsmodels** | For correlation and trend analysis |
| Maps | **folium** | For station geography |

### Coding rules
- **Always use `scripts/db.py`** for the DuckDB connection — never open raw files manually
- **Always save charts** to `outputs/<question_number>_<name>.html` using `fig.write_html()`
- All money is **CHF**, all times are **CET**, all dates are **YYYY-MM-DD**
- A train is **"on time"** if `actual_arrival <= scheduled_arrival + 3 minutes`
- All datetime columns are stored as **VARCHAR** — cast with `CAST(col AS TIMESTAMP)` before arithmetic
- `weather.date` has **mixed formats**: July 2024 rows are DD.MM.YYYY, everything else is YYYY-MM-DD — always use `COALESCE(TRY_STRPTIME(date,'%d.%m.%Y'), CAST(date AS DATE))` to normalise
- `tickets.price_chf` uses **comma as decimal separator** in some rows — always use `CAST(REPLACE(price_chf, ',', '.') AS DOUBLE)`
- `delay_minutes` has **mixed format**: bare integers (`'0'`, `'5'`) and `'N min'` strings — use `TRY_CAST(REPLACE(delay_minutes, ' min', '') AS INTEGER)`
- Answer format: **headline number → supporting chart → 1-paragraph explanation**

---

## Data Schema (join keys in bold)

### stations
| column | type | description |
|---|---|---|
| **station_code** | str | Primary key |
| station_name | str | |
| canton | str | e.g. GR, VS, BE |
| latitude | float | WGS84 |
| longitude | float | WGS84 |
| station_type | str | hub / junction / scenic / terminus |

### weather
| column | type | description |
|---|---|---|
| **date** | str (mixed) | July 2024 rows use DD.MM.YYYY; all other rows use YYYY-MM-DD — always normalise with `COALESCE(TRY_STRPTIME(date,'%d.%m.%Y'), CAST(date AS DATE))` |
| **canton** | str | FK → stations.canton |
| weather_code | str | Readable: clear / cloudy / foehn / fog / rain / snow / thunderstorm |
| temp_celsius | float | °C |
| precip_mm | float | |
| wind_kmh | float | |

### journeys
| column | type | description |
|---|---|---|
| **journey_id** | str | Primary key |
| route_id | str | GLX / BEX / GOL / GOT / ZUR / BAS / SKI / AND |
| train_number | int | |
| scheduled_departure | str (datetime) | Cast to TIMESTAMP before arithmetic |
| scheduled_arrival | str (datetime) | Cast to TIMESTAMP before arithmetic |
| actual_departure | str (datetime) | Cast to TIMESTAMP before arithmetic |
| actual_arrival | str (datetime) | Cast to TIMESTAMP before arithmetic |
| delay_minutes | str | Format: `'24 min'` — use `CAST(REPLACE(delay_minutes,' min','') AS INTEGER)` |
| delay_reason | str | weather / operational / passenger flow / NULL |
| weather_code | str | Denormalised from weather table |
| capacity | int | Seat capacity of train |

**Route ID legend:** GLX = Glacier Express, BEX = Bernina Express, GOL = GoldenPass, GOT = Gotthard Panorama, ZUR = Intercity Zurich-Bern, BAS = Intercity Zurich-Geneva, SKI = Ski Shuttle Verbier, AND = Ski Shuttle Andermatt

**Note:** journeys has no origin_station / dest_station / canton columns — join with weather via `CAST(scheduled_departure AS DATE)` and route lookup.

### passengers
| column | type | description |
|---|---|---|
| **passenger_id** | str | Primary key |
| first_name | str | |
| last_name | str | |
| home_canton | str | |
| age_band | str | 18-25 / 26-35 / 36-50 / 51-65 / 65+ |
| loyalty_tier | str | GA / Halbtax / none |
| signup_date | str | Cast to DATE |

### tickets
| column | type | description |
|---|---|---|
| ticket_id | str | Primary key |
| **journey_id** | str | FK → journeys |
| **passenger_id** | str | FK → passengers |
| price_chf | str | Cast to DOUBLE for aggregation |
| fare_class | str | 1st / 1st_flex / 2nd / 2nd_flex / saver |
| channel | str | app / agency / counter / partner / sbb_app |
| booking_date | str | Cast to DATE |
| booking_lead_days | int | Days between booking and travel |

### onboard_sales
| column | type | description |
|---|---|---|
| sale_id | str | Primary key |
| **journey_id** | str | FK → journeys |
| sku_name | str | e.g. Raclette Toastie, Lindt Chocolate Bar |
| category | str | bakery / beverage / cheese / chocolate / hot food / snack / wine |
| quantity | int | |
| unit_price_chf | float | CHF |
| unit_cost_chf | float | CHF |
| was_stockout | bool | |
| sale_timestamp | str | Cast to TIMESTAMP |

### partner_bookings
| column | type | description |
|---|---|---|
| booking_id | str | Primary key |
| **journey_id** | str | FK → journeys |
| **passenger_id** | str | FK → passengers |
| **partner_id** | str | |
| partner_name | str | e.g. Verbier Ski Resort |
| partner_type | str | ski / cheese / chocolate |
| price_chf | float | CHF |
| cost_chf | float | CHF |
| is_cancelled | bool | |
| booking_timestamp | str | Cast to TIMESTAMP |

### campaigns
| column | type | description |
|---|---|---|
| campaign_id | str | Primary key |
| name | str | Campaign name |
| theme | str | loyalty / partner / scenic / ski |
| start_date / end_date | str | Cast to DATE |
| budget_chf | int | CHF |
| channels | str | Comma-separated channel list |

---

## The 10 Business Questions

| # | Question | Key tables | Key metric |
|---|---|---|---|
| Q1 | Total ticket revenue 2025 vs 2024 — YoY % change | tickets | SUM(CAST(price_chf AS DOUBLE)) GROUP BY YEAR(CAST(booking_date AS DATE)) |
| Q2 | Worst on-time route (on time = arrival within 3 min) | journeys | % on-time GROUP BY route_id |
| Q3 | Highest average ticket price by booking channel | tickets | AVG(CAST(price_chf AS DOUBLE)) GROUP BY channel |
| Q4 | Weather vs delays — does it differ by route? | journeys | corr(CAST(REPLACE(delay_minutes,' min','') AS INT), weather_code) by route_id |
| Q5 | Busiest day of week across the network | journeys | COUNT by DAYOFWEEK(CAST(scheduled_departure AS TIMESTAMP)) |
| Q6 | Single biggest onboard revenue SKU | onboard_sales | SUM(quantity * unit_price_chf) GROUP BY sku_name |
| Q7 | Loyalty tier with highest avg annual spend | tickets + passengers | AVG annual spend per passenger GROUP BY loyalty_tier |
| Q8 | Top 5 routes by journey count (no station-level boarding data) | journeys | COUNT(journey_id) GROUP BY route_id |
| Q9 | Punctuality improved or worsened 2024 → 2025? | journeys | % on-time GROUP BY YEAR(CAST(scheduled_departure AS DATE)) |
| Q10 | Open — find one surprising insight | any | your call |

---

## Dashboard Requirements

File: `dashboard/app.py`
Command: `streamlit run dashboard/app.py`

Structure the page in three sections:

```
┌─────────────────────────────────────────────────────┐
│  KPI ROW: Revenue │ On-Time % │ Avg Ticket │ Pax     │
├──────────────────────────┬──────────────────────────┤
│  REVENUE PANEL           │  OPERATIONS PANEL        │
│  Monthly trend + channel │  On-time % by route      │
│  breakdown               │  Delay heatmap (weather) │
├──────────────────────────┴──────────────────────────┤
│  GROWTH PANEL                                        │
│  Loyalty tier spend │ Partner bookings trend         │
└─────────────────────────────────────────────────────┘
```

Use `st.metric()` for KPI cards, `st.plotly_chart()` for all charts,
and a sidebar quarter/year filter that re-runs all queries.

---

## Standard DuckDB Query Pattern

```python
# Always start cells this way
import sys; sys.path.insert(0, '..')
from scripts.db import query

df = query("""
    SELECT
        YEAR(CAST(booking_date AS DATE))      AS year,
        SUM(CAST(price_chf AS DOUBLE))        AS revenue
    FROM tickets
    GROUP BY 1
    ORDER BY 1
""")
```

### On-time calculation pattern
```python
df = query("""
    SELECT
        route_id,
        COUNT(*) AS total,
        SUM(CASE
            WHEN CAST(actual_arrival AS TIMESTAMP)
                 <= CAST(scheduled_arrival AS TIMESTAMP) + INTERVAL 3 MINUTES
            THEN 1 ELSE 0
        END) * 100.0 / COUNT(*) AS pct_on_time
    FROM journeys
    GROUP BY route_id
    ORDER BY pct_on_time
""")
```
