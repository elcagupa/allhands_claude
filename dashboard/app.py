"""
AlpenRail Executive Dashboard — all 10 business questions
Run: streamlit run dashboard/app.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from scripts.db import query

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="AlpenRail Executive Dashboard",
    page_icon="🚞",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
NAVY  = "#1B3A6B"
RED   = "#E63946"
CREAM = "#F4F1DE"
AMBER = "#E9A100"
GREEN = "#2DC653"

ROUTE_LABELS = {
    "GLX": "Glacier Express",    "BEX": "Bernina Express",
    "GOL": "GoldenPass",         "GOT": "Gotthard Panorama",
    "ZUR": "IC Zurich-Bern",     "BAS": "IC Zurich-Geneva",
    "SKI": "Ski Shuttle Verbier","AND": "Ski Shuttle Andermatt",
}
ROUTE_COLORS = dict(zip(
    ROUTE_LABELS.values(),
    ["#1B3A6B","#E63946","#2DC653","#E9A100","#7B4F9E","#0081A7","#F07167","#00AFB9"],
))
MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
WEATHER_ORDER = ["clear","cloudy","fog","foehn","rain","snow","thunderstorm"]

# ── Filter helpers ────────────────────────────────────────────────────────────
def _yf(year_sel: str, col: str) -> str:
    if year_sel == "Both":
        return f"YEAR(CAST({col} AS DATE)) IN (2024, 2025)"
    return f"YEAR(CAST({col} AS DATE)) = {year_sel}"

def _qf(quarter_sel: str, col: str) -> str:
    if quarter_sel == "Full Year":
        return "1=1"
    q = int(quarter_sel[1])
    months = ",".join(str(m) for m in range((q - 1) * 3 + 1, q * 3 + 1))
    return f"MONTH(CAST({col} AS DATE)) IN ({months})"

def _wh(ys: str, qs: str, col: str) -> str:
    return f"{_yf(ys, col)} AND {_qf(qs, col)}"

def _prior_wh(ys: str, qs: str, col: str) -> str:
    prior = {"2025": "2024", "2024": "2023"}.get(ys)
    yf = f"YEAR(CAST({col} AS DATE)) = {prior}" if prior else "1=0"
    return f"{yf} AND {_qf(qs, col)}"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:{NAVY};margin:0'>🚞 AlpenRail</h2>", unsafe_allow_html=True)
    st.caption("Executive Dashboard")
    st.divider()
    year_sel    = st.selectbox("Year",    ["Both", "2024", "2025"])
    quarter_sel = st.selectbox("Quarter", ["Full Year", "Q1", "Q2", "Q3", "Q4"])
    st.divider()
    st.markdown("**Questions covered**")
    st.caption("Q1 · Revenue YoY")
    st.caption("Q2 · On-time by route")
    st.caption("Q3 · Avg price by channel")
    st.caption("Q4 · Weather vs delays")
    st.caption("Q5 · Busiest day of week")
    st.caption("Q6 · Top onboard SKU")
    st.caption("Q7 · Loyalty tier spend")
    st.caption("Q8 · Route volume")
    st.caption("Q9 · Punctuality trend")
    st.caption("Q10 · Stockout revenue loss")

period_label = year_sel if year_sel != "Both" else "2024–2025"
if quarter_sel != "Full Year":
    period_label += f" {quarter_sel}"

# ── Cached query functions ────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_kpis(ys: str, qs: str):
    cur = query(f"""
        SELECT
            ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue,
            ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price,
            COUNT(DISTINCT passenger_id)                               AS passengers
        FROM tickets WHERE {_wh(ys, qs, 'booking_date')}
    """).iloc[0]
    prior = query(f"""
        SELECT ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue,
               ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price,
               COUNT(DISTINCT passenger_id)                               AS passengers
        FROM tickets WHERE {_prior_wh(ys, qs, 'booking_date')}
    """).iloc[0]
    cur_ot = query(f"""
        SELECT ROUND(SUM(CASE WHEN DATEDIFF('minute',
            CAST(scheduled_arrival AS TIMESTAMP),
            CAST(actual_arrival AS TIMESTAMP)) <= 3 THEN 1 ELSE 0 END
        ) * 100.0 / NULLIF(COUNT(*),0), 1) AS pct
        FROM journeys WHERE {_wh(ys, qs, 'scheduled_departure')}
    """).iloc[0, 0]
    prior_ot = query(f"""
        SELECT ROUND(SUM(CASE WHEN DATEDIFF('minute',
            CAST(scheduled_arrival AS TIMESTAMP),
            CAST(actual_arrival AS TIMESTAMP)) <= 3 THEN 1 ELSE 0 END
        ) * 100.0 / NULLIF(COUNT(*),0), 1) AS pct
        FROM journeys WHERE {_prior_wh(ys, qs, 'scheduled_departure')}
    """).iloc[0, 0]
    return cur, prior, cur_ot, prior_ot


# Q1
@st.cache_data(ttl=3600)
def get_monthly_revenue(ys: str, qs: str):
    df = query(f"""
        SELECT YEAR(CAST(booking_date AS DATE)) AS yr,
               MONTH(CAST(booking_date AS DATE)) AS mo,
               ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue
        FROM tickets
        WHERE YEAR(CAST(booking_date AS DATE)) IN (2024,2025)
          AND {_qf(qs, 'booking_date')}
        GROUP BY 1,2 ORDER BY 1,2
    """)
    df["month"] = df["mo"].map(MONTH_NAMES)
    df["year"]  = df["yr"].astype(str)
    return df


# Q2
@st.cache_data(ttl=3600)
def get_ontime_by_route(ys: str, qs: str):
    df = query(f"""
        SELECT route_id,
            ROUND(SUM(CASE WHEN DATEDIFF('minute',
                CAST(scheduled_arrival AS TIMESTAMP),
                CAST(actual_arrival AS TIMESTAMP)) <= 3 THEN 1 ELSE 0 END
            ) * 100.0 / NULLIF(COUNT(*),0), 1) AS pct_on_time
        FROM journeys WHERE {_wh(ys, qs, 'scheduled_departure')}
        GROUP BY route_id ORDER BY pct_on_time
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    df["color"] = df["pct_on_time"].apply(
        lambda v: RED if v < 85 else (AMBER if v < 93 else GREEN)
    )
    return df


# Q3
@st.cache_data(ttl=3600)
def get_avg_price_channel(ys: str, qs: str):
    return query(f"""
        SELECT channel,
               ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price
        FROM tickets WHERE {_wh(ys, qs, 'booking_date')}
        GROUP BY channel ORDER BY avg_price DESC
    """)


# Q4
@st.cache_data(ttl=3600)
def get_weather_delays(ys: str, qs: str):
    df = query(f"""
        SELECT route_id,
               weather_code,
               COUNT(*) AS journeys,
               ROUND(AVG(GREATEST(DATEDIFF('minute',
                   CAST(scheduled_arrival AS TIMESTAMP),
                   CAST(actual_arrival AS TIMESTAMP)), 0)), 1) AS avg_delay_min
        FROM journeys
        WHERE {_wh(ys, qs, 'scheduled_departure')}
        GROUP BY route_id, weather_code
        ORDER BY route_id, avg_delay_min DESC
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    return df


# Q5
@st.cache_data(ttl=3600)
def get_busiest_dow(ys: str, qs: str):
    df = query(f"""
        SELECT DAYOFWEEK(CAST(scheduled_departure AS DATE)) AS dow_num,
               STRFTIME(CAST(scheduled_departure AS DATE), '%A') AS day_name,
               COUNT(*) AS journeys
        FROM journeys
        WHERE {_wh(ys, qs, 'scheduled_departure')}
        GROUP BY 1,2 ORDER BY 1
    """)
    return df


# Q6
@st.cache_data(ttl=3600)
def get_top_skus(ys: str, qs: str):
    return query(f"""
        SELECT s.sku_name, s.category,
               SUM(s.quantity) AS units_sold,
               ROUND(SUM(s.quantity * s.unit_price_chf), 0) AS total_revenue_chf,
               ROUND(SUM(CASE WHEN s.was_stockout THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                   AS stockout_pct
        FROM onboard_sales s
        JOIN journeys j ON s.journey_id = j.journey_id
        WHERE {_wh(ys, qs, 'j.scheduled_departure')}
        GROUP BY s.sku_name, s.category
        ORDER BY total_revenue_chf DESC
        LIMIT 10
    """)


# Q7
@st.cache_data(ttl=3600)
def get_loyalty_spend(ys: str, qs: str):
    return query(f"""
        WITH annual AS (
            SELECT t.passenger_id,
                   YEAR(CAST(t.booking_date AS DATE)) AS yr,
                   SUM(CAST(REPLACE(t.price_chf,',','.') AS DOUBLE)) AS annual_spend
            FROM tickets t
            WHERE {_wh(ys, qs, 't.booking_date')}
            GROUP BY t.passenger_id, yr
        )
        SELECT p.loyalty_tier,
               ROUND(AVG(a.annual_spend), 2)  AS avg_spend,
               COUNT(DISTINCT a.passenger_id) AS passengers
        FROM annual a
        JOIN passengers p ON a.passenger_id = p.passenger_id
        GROUP BY p.loyalty_tier ORDER BY avg_spend DESC
    """)


# Q8
@st.cache_data(ttl=3600)
def get_route_volume(ys: str, qs: str):
    df = query(f"""
        SELECT j.route_id, COUNT(t.ticket_id) AS tickets_sold
        FROM journeys j
        LEFT JOIN tickets t ON t.journey_id = j.journey_id
        WHERE {_wh(ys, qs, 'j.scheduled_departure')}
        GROUP BY j.route_id ORDER BY tickets_sold DESC
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    return df


# Q9
@st.cache_data(ttl=3600)
def get_punctuality_trend(ys: str, qs: str):
    df = query(f"""
        SELECT YEAR(CAST(scheduled_departure AS DATE))  AS yr,
               MONTH(CAST(scheduled_departure AS DATE)) AS mo,
               ROUND(SUM(CASE WHEN DATEDIFF('minute',
                   CAST(scheduled_arrival AS TIMESTAMP),
                   CAST(actual_arrival AS TIMESTAMP)) <= 3 THEN 1 ELSE 0 END
               ) * 100.0 / NULLIF(COUNT(*),0), 2) AS pct_on_time
        FROM journeys
        WHERE YEAR(CAST(scheduled_departure AS DATE)) IN (2024,2025)
          AND {_qf(qs, 'scheduled_departure')}
        GROUP BY 1,2 ORDER BY 1,2
    """)
    df["month"]  = df["mo"].map(MONTH_NAMES)
    df["year"]   = df["yr"].astype(str)
    return df


# Q10
@st.cache_data(ttl=3600)
def get_stockout_loss(ys: str, qs: str):
    df = query(f"""
        SELECT j.route_id, s.sku_name, s.category,
               COUNT(*) AS incidents,
               SUM(CASE WHEN s.was_stockout THEN 1 ELSE 0 END) AS stockouts,
               ROUND(SUM(CASE WHEN s.was_stockout THEN 1 ELSE 0 END)
                     * 100.0 / COUNT(*), 1) AS stockout_pct,
               ROUND(SUM(CASE WHEN s.was_stockout THEN s.unit_price_chf ELSE 0 END), 0)
                   AS lost_revenue_chf
        FROM onboard_sales s
        JOIN journeys j ON s.journey_id = j.journey_id
        WHERE {_wh(ys, qs, 'j.scheduled_departure')}
        GROUP BY j.route_id, s.sku_name, s.category
        HAVING stockouts > 0
        ORDER BY lost_revenue_chf DESC
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    return df


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{NAVY};margin-bottom:0'>AlpenRail — Executive Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown(f"**Period: {period_label}**  ·  All 10 business questions")
st.divider()

# ── Row 1: KPI cards ──────────────────────────────────────────────────────────
cur, prior, cur_ot, prior_ot = get_kpis(year_sel, quarter_sel)

def _pct(a, b):
    return f"{(a-b)/abs(b)*100:+.1f}% vs prior yr" if b and b != 0 else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue",      f"CHF {cur.revenue/1e6:.2f}M",
          delta=_pct(cur.revenue, prior.revenue))
c2.metric("On-Time %",          f"{cur_ot:.1f}%",
          delta=f"{cur_ot-prior_ot:+.1f} pp vs prior yr" if prior_ot else None)
c3.metric("Avg Ticket Price",   f"CHF {cur.avg_price:.2f}",
          delta=_pct(cur.avg_price, prior.avg_price))
c4.metric("Unique Passengers",  f"{int(cur.passengers):,}",
          delta=_pct(cur.passengers, prior.passengers))

st.divider()

# ── Row 2: Q1 Revenue trend | Q2 On-time by route ────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Q1 · Monthly Ticket Revenue")
    df_rev = get_monthly_revenue(year_sel, quarter_sel)
    fig_rev = px.line(
        df_rev, x="month", y="revenue", color="year", markers=True,
        color_discrete_map={"2024": NAVY, "2025": RED},
        labels={"revenue": "Revenue (CHF)", "month": "Month", "year": "Year"},
        category_orders={"month": list(MONTH_NAMES.values())},
    )
    fig_rev.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                          legend_title_text="", yaxis_tickformat=",.0f",
                          margin=dict(t=10, b=10))
    fig_rev.update_traces(line_width=2.5)
    st.plotly_chart(fig_rev, use_container_width=True)

with col_r:
    st.subheader("Q2 · On-Time % by Route")
    df_ot = get_ontime_by_route(year_sel, quarter_sel)
    fig_ot = go.Figure(go.Bar(
        x=df_ot["pct_on_time"], y=df_ot["route_name"], orientation="h",
        marker_color=df_ot["color"].tolist(),
        text=df_ot["pct_on_time"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_ot.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(range=[75, 100], title="On-Time %"), yaxis_title="",
        margin=dict(t=10, b=10),
        shapes=[
            dict(type="line", x0=85, x1=85, y0=-0.5, y1=len(df_ot)-0.5,
                 line=dict(color=RED, dash="dash", width=1.5)),
            dict(type="line", x0=93, x1=93, y0=-0.5, y1=len(df_ot)-0.5,
                 line=dict(color=AMBER, dash="dash", width=1.5)),
        ],
        annotations=[
            dict(x=85.2, y=len(df_ot)-0.5, text="85%", showarrow=False,
                 font=dict(color=RED, size=9)),
            dict(x=93.2, y=len(df_ot)-0.5, text="93%", showarrow=False,
                 font=dict(color=AMBER, size=9)),
        ],
    )
    st.plotly_chart(fig_ot, use_container_width=True)

st.divider()

# ── Row 3: Q3 Avg price by channel | Q4 Weather vs delays ────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Q3 · Avg Ticket Price by Channel")
    df_ch = get_avg_price_channel(year_sel, quarter_sel)
    fig_ch = px.bar(
        df_ch, x="channel", y="avg_price", text="avg_price",
        color="avg_price", color_continuous_scale=["#A8C7E8", NAVY],
        labels={"avg_price": "Avg Price (CHF)", "channel": "Channel"},
    )
    fig_ch.update_traces(texttemplate="CHF %{text:.2f}", textposition="outside")
    fig_ch.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", coloraxis_showscale=False,
        margin=dict(t=10, b=10),
        yaxis=dict(range=[0, df_ch["avg_price"].max() * 1.18]),
    )
    st.plotly_chart(fig_ch, use_container_width=True)

with col_r:
    st.subheader("Q4 · Weather vs Delays by Route")
    df_wd = get_weather_delays(year_sel, quarter_sel)
    if df_wd.empty:
        st.info("No journey data for this period.")
    else:
        fig_wd = px.bar(
            df_wd, x="weather_code", y="avg_delay_min", color="route_name",
            barmode="group",
            color_discrete_map=ROUTE_COLORS,
            labels={"avg_delay_min": "Avg Delay (min)",
                    "weather_code": "Weather Condition",
                    "route_name": "Route"},
            category_orders={"weather_code": WEATHER_ORDER},
        )
        fig_wd.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend_title_text="Route", legend=dict(font=dict(size=10)),
            margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_wd, use_container_width=True)

st.divider()

# ── Row 4: Q5 Busiest day | Q6 Top onboard SKU ───────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Q5 · Busiest Day of Week")
    df_dow = get_busiest_dow(year_sel, quarter_sel)
    DOW_ORDER = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    fig_dow = px.bar(
        df_dow, x="day_name", y="journeys", text_auto=",d",
        color="journeys", color_continuous_scale=["#A8C7E8", NAVY],
        labels={"journeys": "Journeys", "day_name": "Day of Week"},
        category_orders={"day_name": DOW_ORDER},
    )
    fig_dow.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        coloraxis_showscale=False, margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_dow, use_container_width=True)

with col_r:
    st.subheader("Q6 · Top Onboard SKU by Revenue")
    df_sku = get_top_skus(year_sel, quarter_sel)
    if df_sku.empty:
        st.info("No onboard sales data for this period.")
    else:
        fig_sku = px.bar(
            df_sku.sort_values("total_revenue_chf"),
            x="total_revenue_chf", y="sku_name",
            orientation="h", color="category", text_auto=".3s",
            labels={"total_revenue_chf": "Revenue (CHF)", "sku_name": "SKU",
                    "category": "Category"},
        )
        fig_sku.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend_title_text="Category", margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_sku, use_container_width=True)

st.divider()

# ── Row 5: Q7 Loyalty spend | Q9 Punctuality trend ───────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Q7 · Loyalty Tier Avg Annual Spend")
    df_loy = get_loyalty_spend(year_sel, quarter_sel)
    if not df_loy.empty:
        top_tier = df_loy.iloc[0]["loyalty_tier"]
        bot_tier = df_loy.iloc[-1]["loyalty_tier"]
        gap      = df_loy.iloc[0]["avg_spend"] - df_loy.iloc[-1]["avg_spend"]
        st.caption(f"**{top_tier}** leads **{bot_tier}** by CHF {gap:,.0f}/yr — consider upsell campaigns")
        fig_loy = px.bar(
            df_loy, x="loyalty_tier", y="avg_spend", text="avg_spend",
            color="loyalty_tier",
            color_discrete_sequence=[NAVY, AMBER, "#7B9EC4"],
            labels={"avg_spend": "Avg Annual Spend (CHF)", "loyalty_tier": "Tier"},
        )
        fig_loy.update_traces(texttemplate="CHF %{text:,.2f}", textposition="outside")
        fig_loy.update_layout(
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
            margin=dict(t=10, b=10),
            yaxis=dict(range=[0, df_loy["avg_spend"].max() * 1.2]),
        )
        st.plotly_chart(fig_loy, use_container_width=True)

with col_r:
    st.subheader("Q9 · Punctuality Trend 2024→2025")
    df_pt = get_punctuality_trend(year_sel, quarter_sel)
    avg_24 = df_pt[df_pt.yr == 2024]["pct_on_time"].mean()
    avg_25 = df_pt[df_pt.yr == 2025]["pct_on_time"].mean()
    delta_pp = avg_25 - avg_24
    direction = "improved" if delta_pp > 0 else "worsened"
    st.caption(f"Punctuality **{direction}** by {abs(delta_pp):.1f} pp in 2025 vs 2024")
    fig_pt = px.line(
        df_pt, x="month", y="pct_on_time", color="year",
        markers=True,
        color_discrete_map={"2024": NAVY, "2025": RED},
        labels={"pct_on_time": "On-Time % (≤3 min)", "month": "Month", "year": "Year"},
        category_orders={"month": list(MONTH_NAMES.values())},
    )
    fig_pt.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        legend_title_text="", margin=dict(t=10, b=10),
        yaxis=dict(range=[85, 100]),
    )
    fig_pt.update_traces(line_width=2.5)
    st.plotly_chart(fig_pt, use_container_width=True)

st.divider()

# ── Row 6: Q8 Route volume | Partner bookings trend ──────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Q8 · Tickets Sold by Route")
    st.caption("No origin_station in source data — route volume used as proxy for boardings")
    df_rv = get_route_volume(year_sel, quarter_sel)
    fig_rv = px.bar(
        df_rv.sort_values("tickets_sold"),
        x="tickets_sold", y="route_name",
        orientation="h", text_auto=",d",
        color="tickets_sold", color_continuous_scale=["#A8C7E8", NAVY],
        labels={"tickets_sold": "Tickets Sold", "route_name": "Route"},
    )
    fig_rv.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        coloraxis_showscale=False, margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_rv, use_container_width=True)

with col_r:
    st.subheader("Partner Bookings by Type")
    df_pb = query(f"""
        SELECT YEAR(CAST(booking_timestamp AS TIMESTAMP))  AS yr,
               MONTH(CAST(booking_timestamp AS TIMESTAMP)) AS mo,
               partner_type,
               ROUND(SUM(price_chf), 0) AS revenue_chf
        FROM partner_bookings
        WHERE is_cancelled = false
          AND {_wh(year_sel, quarter_sel, 'booking_timestamp')}
        GROUP BY 1,2,3 ORDER BY 1,2,3
    """)
    if df_pb.empty:
        st.info("No partner booking data for this period.")
    else:
        df_pb["period"] = df_pb["yr"].astype(str) + "-" + df_pb["mo"].apply(lambda m: f"{m:02d}")
        fig_pb = px.area(
            df_pb, x="period", y="revenue_chf", color="partner_type",
            color_discrete_map={"ski": NAVY, "cheese": AMBER, "chocolate": RED},
            labels={"revenue_chf": "Revenue (CHF)", "period": "Month",
                    "partner_type": "Partner Type"},
        )
        fig_pb.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend_title_text="Partner", margin=dict(t=10, b=10),
            xaxis=dict(tickangle=45, tickmode="array",
                       tickvals=df_pb["period"].unique()[::3]),
            yaxis_tickformat=",.0f",
        )
        st.plotly_chart(fig_pb, use_container_width=True)

st.divider()

# ── Row 7: Q10 Stockout revenue loss (full width) ─────────────────────────────
st.subheader("Q10 · Surprise Insight — Onboard Stockout Revenue Loss")
df_sl = get_stockout_loss(year_sel, quarter_sel)

if df_sl.empty:
    st.info("No stockout data for this period.")
else:
    total_lost = df_sl["lost_revenue_chf"].sum()
    worst      = df_sl.iloc[0]
    st.markdown(
        f"**CHF {total_lost:,.0f}** estimated lost onboard revenue from stockouts — "
        f"worst: **{worst['route_name']}** / **{worst['sku_name']}** "
        f"(CHF {worst['lost_revenue_chf']:,.0f}, {worst['stockout_pct']:.0f}% stockout rate)"
    )
    col_l, col_r = st.columns([3, 2])
    with col_l:
        fig_sl_tree = px.treemap(
            df_sl, path=["route_name", "sku_name"],
            values="lost_revenue_chf", color="stockout_pct",
            color_continuous_scale=px.colors.sequential.Oranges,
            labels={"lost_revenue_chf": "Lost Revenue (CHF)",
                    "stockout_pct": "Stockout %"},
        )
        fig_sl_tree.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig_sl_tree, use_container_width=True)
    with col_r:
        fig_sl_bar = px.bar(
            df_sl.head(10).sort_values("lost_revenue_chf"),
            x="lost_revenue_chf", y="sku_name", orientation="h",
            color="stockout_pct", text_auto=".3s",
            color_continuous_scale=px.colors.sequential.Oranges,
            labels={"lost_revenue_chf": "Lost Revenue (CHF)",
                    "sku_name": "SKU", "stockout_pct": "Stockout %"},
        )
        fig_sl_bar.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_sl_bar, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("AlpenRail Analytics Dashboard  |  Data: 2024–2025  |  Built with Streamlit")
