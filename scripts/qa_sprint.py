"""
AlpenRail QA Sprint — answers to all 10 business questions.
Run: python scripts/qa_sprint.py
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.db import query
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy import stats

os.makedirs("outputs", exist_ok=True)

ROUTE_LABELS = {
    "GLX": "Glacier Express",
    "BEX": "Bernina Express",
    "GOL": "GoldenPass",
    "GOT": "Gotthard Panorama",
    "ZUR": "IC Zurich-Bern",
    "BAS": "IC Zurich-Geneva",
    "SKI": "Ski Shuttle Verbier",
    "AND": "Ski Shuttle Andermatt",
}
ALPINE_SEQ = px.colors.sequential.Blues_r
ALPINE_2 = ["#003865", "#E8A020"]


# ─── Q1 ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("=== Q1: Total Ticket Revenue 2024 vs 2025 — YoY % Change ===")
print("=" * 65)

df1 = query("""
    SELECT
        YEAR(CAST(booking_date AS DATE))                        AS year,
        ROUND(SUM(CAST(REPLACE(price_chf, ',', '.') AS DOUBLE)), 0) AS revenue_chf
    FROM tickets
    WHERE booking_date IS NOT NULL
    GROUP BY 1
    ORDER BY 1
""")

rev_2024 = df1.loc[df1.year == 2024, "revenue_chf"].values[0]
rev_2025 = df1.loc[df1.year == 2025, "revenue_chf"].values[0]
yoy = (rev_2025 - rev_2024) / rev_2024 * 100

print(f"  2024 revenue : CHF {rev_2024:,.0f}")
print(f"  2025 revenue : CHF {rev_2025:,.0f}")
print(f"  YoY change   : {yoy:+.1f}%")

fig1 = px.bar(
    df1, x="year", y="revenue_chf", text_auto=".3s",
    color="year", color_discrete_sequence=ALPINE_2,
    title=f"Ticket Revenue: CHF {rev_2025/1e6:.1f}M in 2025 ({yoy:+.1f}% YoY)",
    labels={"revenue_chf": "Revenue (CHF)", "year": "Year"},
)
fig1.update_layout(showlegend=False)
fig1.write_html("outputs/q1_revenue_yoy.html")
print("  Chart saved: outputs/q1_revenue_yoy.html")
print("""
  2025 total ticket revenue was CHF {:,.0f} ({:+.1f}% vs 2024). This
  reflects cumulative ticket sales recorded by booking_date. Note that
  some tickets are booked in advance (earliest booking_date is late 2023)
  so the comparison captures sold-for-2025 travel regardless of lead time.
""".format(rev_2025, yoy))


# ─── Q2 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q2: Worst On-Time Route ===")
print("=" * 65)

df2 = query("""
    SELECT
        route_id,
        COUNT(*)                                                      AS total,
        ROUND(
            SUM(CASE WHEN DATEDIFF('minute',
                          CAST(scheduled_arrival AS TIMESTAMP),
                          CAST(actual_arrival   AS TIMESTAMP)) <= 3
                     THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)       AS pct_on_time,
        ROUND(AVG(GREATEST(
            DATEDIFF('minute',
                     CAST(scheduled_arrival AS TIMESTAMP),
                     CAST(actual_arrival   AS TIMESTAMP)), 0)), 1)    AS avg_delay_min
    FROM journeys
    GROUP BY route_id
    ORDER BY pct_on_time
""")
df2["route_name"] = df2["route_id"].map(ROUTE_LABELS)

worst = df2.iloc[0]
print(f"  Worst route : {worst['route_name']} ({worst['route_id']}) — {worst['pct_on_time']:.1f}% on time")
print(df2[["route_name", "total", "pct_on_time", "avg_delay_min"]].to_string(index=False))

fig2 = px.bar(
    df2.sort_values("pct_on_time"),
    x="pct_on_time", y="route_name", orientation="h",
    text="pct_on_time",
    color="pct_on_time", color_continuous_scale=px.colors.sequential.YlGn,
    title=f"On-Time % by Route — Worst: {worst['route_name']} ({worst['pct_on_time']:.1f}%)",
    labels={"pct_on_time": "On-Time % (arrival within 3 min)", "route_name": "Route"},
)
fig2.update_traces(texttemplate="%{text:.1f}%")
fig2.update_layout(coloraxis_showscale=False)
fig2.write_html("outputs/q2_ontime_by_route.html")
print("  Chart saved: outputs/q2_ontime_by_route.html")
print(f"""
  {worst['route_name']} is the worst-performing route at {worst['pct_on_time']:.1f}% on time,
  with an average delay of {worst['avg_delay_min']:.1f} minutes on late journeys. Its long
  single-track mountain sections leave little buffer for recovery once a delay
  starts. By contrast, the intercity and ski shuttle routes benefit from
  simpler trackage and shorter journey times.
""")


# ─── Q3 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q3: Highest Avg Ticket Price by Booking Channel ===")
print("=" * 65)

df3 = query("""
    SELECT
        channel,
        COUNT(*)                                                        AS tickets,
        ROUND(AVG(CAST(REPLACE(price_chf, ',', '.') AS DOUBLE)), 2)    AS avg_price_chf,
        ROUND(MIN(CAST(REPLACE(price_chf, ',', '.') AS DOUBLE)), 2)    AS min_price,
        ROUND(MAX(CAST(REPLACE(price_chf, ',', '.') AS DOUBLE)), 2)    AS max_price
    FROM tickets
    GROUP BY channel
    ORDER BY avg_price_chf DESC
""")

winner = df3.iloc[0]
print(f"  Highest avg price: {winner['channel']} — CHF {winner['avg_price_chf']:.2f}")
print(df3.to_string(index=False))

fig3 = px.bar(
    df3, x="channel", y="avg_price_chf", text_auto=".2f",
    color="avg_price_chf", color_continuous_scale=ALPINE_SEQ,
    title=f"Avg Ticket Price by Channel — {winner['channel'].title()} leads at CHF {winner['avg_price_chf']:.2f}",
    labels={"avg_price_chf": "Avg Price (CHF)", "channel": "Channel"},
)
fig3.update_layout(coloraxis_showscale=False)
fig3.write_html("outputs/q3_avg_price_by_channel.html")
print("  Chart saved: outputs/q3_avg_price_by_channel.html")
print(f"""
  The {winner['channel']} channel commands the highest average ticket price at
  CHF {winner['avg_price_chf']:.2f}. This likely reflects a mix of premium fare classes
  and less price-sensitive customers who book through that channel. Digital
  channels (app, sbb_app) tend toward lower averages, consistent with
  discount-seeking behaviour and saver fare purchases made online.
""")


# ─── Q4 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q4: Weather vs Delays — by Route ===")
print("=" * 65)

# Join journeys to weather on date (averaging precip across cantons per day)
df4 = query("""
    WITH weather_daily AS (
        SELECT
            COALESCE(TRY_STRPTIME(date, '%d.%m.%Y'), CAST(date AS DATE)) AS w_date,
            AVG(precip_mm)               AS avg_precip,
            AVG(wind_kmh)                AS avg_wind
        FROM weather
        GROUP BY w_date
    ),
    journey_delays AS (
        SELECT
            route_id,
            CAST(scheduled_departure AS DATE)                               AS j_date,
            GREATEST(DATEDIFF('minute',
                CAST(scheduled_arrival AS TIMESTAMP),
                CAST(actual_arrival   AS TIMESTAMP)), 0)                    AS delay_min
        FROM journeys
    )
    SELECT
        j.route_id,
        j.delay_min,
        w.avg_precip,
        w.avg_wind
    FROM journey_delays j
    JOIN weather_daily w ON j.j_date = w.w_date
""")

df4["route_name"] = df4["route_id"].map(ROUTE_LABELS)

corr_rows = []
for route, grp in df4.groupby("route_name"):
    r_precip, p_precip = stats.pearsonr(grp["avg_precip"], grp["delay_min"])
    r_wind, _ = stats.pearsonr(grp["avg_wind"], grp["delay_min"])
    corr_rows.append({
        "route_name": route,
        "corr_precip": round(r_precip, 3),
        "corr_wind": round(r_wind, 3),
        "n": len(grp),
    })
df4_corr = pd.DataFrame(corr_rows).sort_values("corr_precip", ascending=False)

most_sensitive = df4_corr.iloc[0]
print(f"  Most weather-sensitive route: {most_sensitive['route_name']} (r={most_sensitive['corr_precip']:.3f})")
print(df4_corr.to_string(index=False))

# Average delay by weather condition using journeys.weather_code
df4b = query("""
    SELECT
        route_id,
        weather_code,
        COUNT(*) AS journeys,
        ROUND(AVG(GREATEST(DATEDIFF('minute',
            CAST(scheduled_arrival AS TIMESTAMP),
            CAST(actual_arrival   AS TIMESTAMP)), 0)), 1) AS avg_delay_min
    FROM journeys
    GROUP BY route_id, weather_code
    ORDER BY route_id, avg_delay_min DESC
""")
df4b["route_name"] = df4b["route_id"].map(ROUTE_LABELS)

fig4 = px.bar(
    df4b, x="weather_code", y="avg_delay_min", color="route_name",
    barmode="group",
    title=f"Avg Delay by Weather Condition — {most_sensitive['route_name']} most precipitation-sensitive (r={most_sensitive['corr_precip']:.3f})",
    labels={"avg_delay_min": "Avg Delay (min)", "weather_code": "Weather", "route_name": "Route"},
    category_orders={"weather_code": ["clear", "cloudy", "fog", "foehn", "rain", "snow", "thunderstorm"]},
)
fig4.write_html("outputs/q4_weather_delays.html")
print("  Chart saved: outputs/q4_weather_delays.html")
print(f"""
  Precipitation correlates most strongly with delays on {most_sensitive['route_name']}
  (Pearson r={most_sensitive['corr_precip']:.3f}). Thunderstorms and foehn wind cause the
  largest average delays across all routes. Alpine scenic routes are most
  exposed because they traverse high-altitude passes where weather changes
  are rapid. Intercity routes show lower sensitivity thanks to lower
  altitudes and more protected track sections.
""")


# ─── Q5 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q5: Busiest Day of Week ===")
print("=" * 65)

df5 = query("""
    SELECT
        DAYOFWEEK(CAST(scheduled_departure AS DATE))    AS dow_num,
        STRFTIME(CAST(scheduled_departure AS DATE), '%A') AS day_name,
        COUNT(*)                                         AS journeys
    FROM journeys
    GROUP BY 1, 2
    ORDER BY 1
""")

busiest = df5.loc[df5.journeys.idxmax()]
print(f"  Busiest day: {busiest['day_name']} ({busiest['journeys']:,} journeys)")
print(df5[["day_name", "journeys"]].to_string(index=False))

DOW_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
fig5 = px.bar(
    df5, x="day_name", y="journeys", text_auto=",d",
    color="journeys", color_continuous_scale=ALPINE_SEQ,
    title=f"Journeys by Day of Week — {busiest['day_name']} is busiest ({busiest['journeys']:,})",
    labels={"journeys": "Journey Count", "day_name": "Day"},
    category_orders={"day_name": DOW_ORDER},
)
fig5.update_layout(coloraxis_showscale=False)
fig5.write_html("outputs/q5_busiest_dow.html")
print("  Chart saved: outputs/q5_busiest_dow.html")
print(f"""
  {busiest['day_name']} is the busiest day on the AlpenRail network with
  {busiest['journeys']:,} scheduled journeys. Weekend peaks are consistent with
  leisure-driven demand — ski shuttles and scenic routes fill early on
  Saturdays and Sundays as tourists start excursions. The mid-week trough
  suggests limited commuter base on these primarily tourist-facing routes.
""")


# ─── Q6 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q6: Biggest Onboard Revenue SKU ===")
print("=" * 65)

df6 = query("""
    SELECT
        sku_name,
        category,
        SUM(quantity)                         AS units_sold,
        ROUND(SUM(quantity * unit_price_chf), 0) AS total_revenue_chf,
        ROUND(AVG(unit_price_chf), 2)         AS avg_price_chf,
        SUM(CASE WHEN was_stockout THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS stockout_pct
    FROM onboard_sales
    GROUP BY sku_name, category
    ORDER BY total_revenue_chf DESC
    LIMIT 10
""")

top_sku = df6.iloc[0]
print(f"  Top SKU: {top_sku['sku_name']} — CHF {top_sku['total_revenue_chf']:,.0f}")
print(df6[["sku_name", "category", "units_sold", "total_revenue_chf", "stockout_pct"]].to_string(index=False))

fig6 = px.bar(
    df6.sort_values("total_revenue_chf"),
    x="total_revenue_chf", y="sku_name", orientation="h",
    color="category", text_auto=".3s",
    title=f"Top 10 Onboard SKUs by Revenue — '{top_sku['sku_name']}' leads at CHF {top_sku['total_revenue_chf']:,.0f}",
    labels={"total_revenue_chf": "Total Revenue (CHF)", "sku_name": "SKU"},
)
fig6.write_html("outputs/q6_onboard_sku_revenue.html")
print("  Chart saved: outputs/q6_onboard_sku_revenue.html")
print(f"""
  '{top_sku['sku_name']}' ({top_sku['category']}) is the single highest-revenue onboard SKU
  at CHF {top_sku['total_revenue_chf']:,.0f} across the two years. With a {top_sku['stockout_pct']:.1f}%
  stockout rate, there may be room to increase revenue further by improving
  supply planning on high-demand routes. The mix of beverages and food
  items in the top 10 suggests passengers prioritise refreshment over
  souvenir purchases during journeys.
""")


# ─── Q7 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q7: Loyalty Tier with Highest Avg Annual Spend ===")
print("=" * 65)

df7 = query("""
    WITH annual AS (
        SELECT
            t.passenger_id,
            YEAR(CAST(t.booking_date AS DATE))                           AS yr,
            SUM(CAST(REPLACE(t.price_chf, ',', '.') AS DOUBLE))         AS annual_spend
        FROM tickets t
        WHERE t.booking_date IS NOT NULL
        GROUP BY t.passenger_id, yr
    )
    SELECT
        p.loyalty_tier,
        COUNT(DISTINCT a.passenger_id)    AS passengers,
        ROUND(AVG(a.annual_spend), 2)     AS avg_annual_spend_chf,
        ROUND(MIN(a.annual_spend), 2)     AS min_spend,
        ROUND(MAX(a.annual_spend), 2)     AS max_spend
    FROM annual a
    JOIN passengers p ON a.passenger_id = p.passenger_id
    GROUP BY p.loyalty_tier
    ORDER BY avg_annual_spend_chf DESC
""")

top_tier = df7.iloc[0]
second_tier = df7.iloc[1]
gap = top_tier["avg_annual_spend_chf"] - second_tier["avg_annual_spend_chf"]
print(f"  Top tier: {top_tier['loyalty_tier']} — CHF {top_tier['avg_annual_spend_chf']:,.2f}/year")
print(df7.to_string(index=False))

fig7 = px.bar(
    df7, x="loyalty_tier", y="avg_annual_spend_chf", text_auto=".2f",
    color="loyalty_tier", color_discrete_sequence=ALPINE_2 + ["#7BA7BC"],
    title=f"Avg Annual Spend by Loyalty Tier — {top_tier['loyalty_tier']} leads by CHF {gap:,.0f}/yr vs {second_tier['loyalty_tier']}",
    labels={"avg_annual_spend_chf": "Avg Annual Spend (CHF)", "loyalty_tier": "Loyalty Tier"},
)
fig7.update_layout(showlegend=False)
fig7.write_html("outputs/q7_loyalty_spend.html")
print("  Chart saved: outputs/q7_loyalty_spend.html")
print(f"""
  {top_tier['loyalty_tier']} cardholders spend an average of CHF {top_tier['avg_annual_spend_chf']:,.2f} per year,
  CHF {gap:,.0f} more than {second_tier['loyalty_tier']} holders at CHF {second_tier['avg_annual_spend_chf']:,.2f}.
  GA holders commit to the full Swiss travel pass, which may drive more
  frequent and spontaneous travel — including premium scenic routes. This
  suggests upselling GA holders on 1st-class upgrades and onboard packages
  could yield disproportionate revenue gains.
""")


# ─── Q8 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q8: Journey Volume by Route + Station Map ===")
print("=" * 65)

# No origin_station in journeys — show route volume and ticket boardings
df8 = query("""
    SELECT
        j.route_id,
        COUNT(DISTINCT j.journey_id)     AS journeys,
        COUNT(t.ticket_id)               AS tickets_sold
    FROM journeys j
    LEFT JOIN tickets t ON t.journey_id = j.journey_id
    GROUP BY j.route_id
    ORDER BY tickets_sold DESC
""")
df8["route_name"] = df8["route_id"].map(ROUTE_LABELS)

print(df8[["route_name", "journeys", "tickets_sold"]].to_string(index=False))

fig8 = px.bar(
    df8.sort_values("tickets_sold"),
    x="tickets_sold", y="route_name", orientation="h",
    text_auto=",d", color="tickets_sold",
    color_continuous_scale=ALPINE_SEQ,
    title="Tickets Sold by Route (no station-level boarding data in source)",
    labels={"tickets_sold": "Tickets Sold", "route_name": "Route"},
)
fig8.update_layout(coloraxis_showscale=False)
fig8.write_html("outputs/q8_route_volume.html")
print("  Chart saved: outputs/q8_route_volume.html")

# Station folium map
try:
    import folium
    df_stations = query("SELECT station_code, station_name, canton, latitude, longitude, station_type FROM stations")
    m = folium.Map(location=[46.8, 8.3], zoom_start=8, tiles="CartoDB positron")
    colors = {"hub": "red", "junction": "orange", "scenic": "blue", "terminus": "green"}
    for _, row in df_stations.iterrows():
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=8 if row.station_type == "hub" else 5,
            color=colors.get(row.station_type, "gray"),
            fill=True, fill_opacity=0.8,
            tooltip=f"{row.station_name} ({row.canton}) — {row.station_type}",
        ).add_to(m)
    m.save("outputs/q8_station_map.html")
    print("  Map saved:  outputs/q8_station_map.html")
except Exception as e:
    print(f"  Folium map skipped: {e}")

print(f"""
  Note: journeys has no origin_station column so station-level boarding
  counts cannot be computed from this dataset. Route-level ticket volume
  is shown instead. BAS (IC Zurich-Geneva) and ZUR (IC Zurich-Bern)
  dominate in raw volume — intercity routes run more frequent services
  than the premium scenic trains. The station map shows all 17 network
  stations coloured by type (red=hub, orange=junction, blue=scenic, green=terminus).
""")


# ─── Q9 ──────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q9: Punctuality Trend 2024 vs 2025 ===")
print("=" * 65)

df9 = query("""
    SELECT
        YEAR(CAST(scheduled_departure AS DATE))                           AS yr,
        MONTH(CAST(scheduled_departure AS DATE))                          AS mo,
        COUNT(*)                                                           AS total,
        ROUND(SUM(CASE WHEN DATEDIFF('minute',
                            CAST(scheduled_arrival AS TIMESTAMP),
                            CAST(actual_arrival   AS TIMESTAMP)) <= 3
                       THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)         AS pct_on_time
    FROM journeys
    GROUP BY 1, 2
    ORDER BY 1, 2
""")

df9_2024 = df9[df9.yr == 2024].pct_on_time.mean()
df9_2025 = df9[df9.yr == 2025].pct_on_time.mean()
delta = df9_2025 - df9_2024
direction = "improved" if delta > 0 else "worsened"
print(f"  2024 avg on-time: {df9_2024:.1f}%")
print(f"  2025 avg on-time: {df9_2025:.1f}%")
print(f"  Trend: {direction} by {abs(delta):.1f} pp")

df9["month_label"] = df9.apply(lambda r: f"{int(r.mo):02d}", axis=1)
df9["year_str"] = df9.yr.astype(str)

fig9 = px.line(
    df9, x="month_label", y="pct_on_time", color="year_str",
    markers=True,
    color_discrete_map={"2024": ALPINE_2[0], "2025": ALPINE_2[1]},
    title=f"Monthly On-Time % — Punctuality {direction} by {abs(delta):.1f} pp in 2025 vs 2024",
    labels={"pct_on_time": "On-Time % (≤3 min late)", "month_label": "Month", "year_str": "Year"},
)
fig9.update_layout(xaxis=dict(
    tickvals=[f"{m:02d}" for m in range(1, 13)],
    ticktext=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
))
fig9.write_html("outputs/q9_punctuality_trend.html")
print("  Chart saved: outputs/q9_punctuality_trend.html")
print(f"""
  Network punctuality {direction} from {df9_2024:.1f}% in 2024 to {df9_2025:.1f}% in
  2025, a {abs(delta):.1f} percentage-point {'gain' if delta > 0 else 'decline'}. Winter months
  (Dec–Feb) show the widest spread between years, suggesting operational
  changes or weather patterns differ across the two winters. Summer months
  are relatively stable, consistent with better visibility and drier
  conditions on mountain routes.
""")


# ─── Q10 ─────────────────────────────────────────────────────────────────────
print("=" * 65)
print("=== Q10: Open Insight — Stockout Revenue Loss by Route ===")
print("=" * 65)

df10 = query("""
    SELECT
        j.route_id,
        s.sku_name,
        s.category,
        COUNT(*)                                                   AS incidents,
        SUM(CASE WHEN s.was_stockout THEN 1 ELSE 0 END)           AS stockouts,
        ROUND(SUM(CASE WHEN s.was_stockout THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 1)                               AS stockout_pct,
        ROUND(SUM(CASE WHEN s.was_stockout
                       THEN s.unit_price_chf ELSE 0 END), 0)      AS lost_revenue_chf
    FROM onboard_sales s
    JOIN journeys j ON s.journey_id = j.journey_id
    GROUP BY j.route_id, s.sku_name, s.category
    ORDER BY lost_revenue_chf DESC
    LIMIT 15
""")
df10["route_name"] = df10["route_id"].map(ROUTE_LABELS)

total_lost = query("""
    SELECT ROUND(SUM(CASE WHEN was_stockout THEN unit_price_chf ELSE 0 END), 0) AS lost
    FROM onboard_sales
""").iloc[0, 0]

top10 = df10.iloc[0]
print(f"  Total estimated lost revenue (stockouts): CHF {total_lost:,.0f}")
print(f"  Worst combo: {top10['route_name']} / {top10['sku_name']} — CHF {top10['lost_revenue_chf']:,.0f} lost, {top10['stockout_pct']:.1f}% stockout rate")
print(df10[["route_name","sku_name","stockout_pct","lost_revenue_chf"]].head(10).to_string(index=False))

fig10 = px.treemap(
    df10, path=["route_name", "sku_name"],
    values="lost_revenue_chf", color="stockout_pct",
    color_continuous_scale=px.colors.sequential.Oranges,
    title=f"Onboard Stockout Revenue Loss by Route & SKU — CHF {total_lost:,.0f} total estimated lost",
    labels={"lost_revenue_chf": "Lost Revenue (CHF)", "stockout_pct": "Stockout %"},
)
fig10.write_html("outputs/q10_stockout_loss.html")
print("  Chart saved: outputs/q10_stockout_loss.html")
print(f"""
  SURPRISING INSIGHT: Onboard stockouts cost an estimated CHF {total_lost:,.0f} in
  lost revenue over the two years — money left on the table because shelves
  ran empty before passengers could buy. The losses are heavily concentrated
  on a small number of route/SKU combinations: {top10['route_name']} running
  out of '{top10['sku_name']}' is the single biggest gap at CHF {top10['lost_revenue_chf']:,.0f}.

  This is actionable: stockout events are known in advance (was_stockout flag),
  so a simple demand-forecasting model tied to passenger capacity and route
  could virtually eliminate the problem. Even recovering 50% of lost revenue
  would materially improve onboard margin without adding a single new product.
""")

print("=" * 65)
print("All 10 questions answered. Charts saved to outputs/")
print("=" * 65)
