# /qa — Answer All 10 Business Questions

Answer every question in `CLAUDE.md` using DuckDB SQL via `scripts/db.py`.

## Rules
- Use `from scripts.db import query` at the top of every code block
- Each answer = headline number + plotly chart saved to `outputs/` + 1-paragraph explanation
- Save charts as `outputs/q<N>_<slug>.html` using `fig.write_html()`
- All SQL in one clean query per question — no chained pandas after DuckDB
- Print the answer clearly labelled: `=== Q1: ... ===`

## Answer each question exactly as follows

### Q1 — Ticket Revenue 2024 vs 2025
SQL: `SELECT YEAR(sale_date), SUM(price) FROM tickets GROUP BY 1`
Chart: grouped bar, year on x-axis
Headline: total 2025 revenue and YoY % change

### Q2 — Worst On-Time Route
SQL: compute delay_min = `date_diff('minute', sched_arrival, actual_arrival)`,
flag on_time = delay_min <= 3, then `GROUP BY route_name`
Chart: horizontal bar sorted by on-time %
Headline: route name + its on-time %

### Q3 — Highest Avg Ticket Price by Channel
SQL: `SELECT channel, AVG(price) FROM tickets GROUP BY channel`
Chart: bar chart
Headline: winning channel + CHF amount

### Q4 — Weather vs Delays by Route
SQL: join journeys → weather on (canton, date), compute delay_min,
then Pearson correlation of precip_mm vs delay_min per route
Chart: scatter with trendline per route (facet or colour)
Headline: which route is most weather-sensitive

### Q5 — Busiest Day of Week
SQL: `SELECT dayofweek(sale_date), COUNT(*) FROM tickets GROUP BY 1`
Chart: bar chart Mon–Sun
Headline: day name + ticket count

### Q6 — Top Onboard SKU by Revenue
SQL: `SELECT sku_name, SUM(quantity * unit_price) FROM onboard_sales GROUP BY sku_name ORDER BY 2 DESC`
Chart: horizontal bar top 10
Headline: SKU name + total CHF revenue

### Q7 — Loyalty Tier Avg Annual Spend
SQL: join tickets → passengers on passenger_id,
compute annual spend per passenger, then AVG by loyalty_tier
Chart: bar chart
Headline: winning tier + CHF/year difference vs next

### Q8 — Top 5 Stations by Boardings
SQL: join journeys → stations on origin_station = station_code,
`SELECT station_name, COUNT(*) GROUP BY station_name ORDER BY 2 DESC LIMIT 5`
Chart: horizontal bar
Also render a folium map saved to `outputs/q8_station_map.html`

### Q9 — Punctuality Trend 2024 → 2025
SQL: same on-time logic as Q2, `GROUP BY YEAR(date)`
Chart: line chart monthly on-time % for both years
Headline: improved or worsened, by how many percentage points

### Q10 — Open Insight
Explore freely. Good places to look:
- Stockout rates by route or SKU
- Lead-time distribution anomalies
- Campaign ROI (conversions / budget_chf)
- Channel mix shift between 2024 and 2025
- Age band vs loyalty tier spend interaction
Write a short narrative: what you found, why it's surprising, what action it implies.
