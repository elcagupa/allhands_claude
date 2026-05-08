"""
AlpenRail Executive Dashboard
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

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="AlpenRail Executive Dashboard",
    page_icon="🚞",
)

# ── Brand palette ─────────────────────────────────────────────────────────────
NAVY   = "#1B3A6B"
RED    = "#E63946"
CREAM  = "#F4F1DE"
AMBER  = "#E9A100"
GREEN  = "#2DC653"

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

# ── Filter helpers (pure functions — safe to call inside @st.cache_data) ─────
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

def _wh(year_sel: str, quarter_sel: str, col: str) -> str:
    return f"{_yf(year_sel, col)} AND {_qf(quarter_sel, col)}"

def _prior_yf(year_sel: str, col: str) -> str:
    prior = {"2025": "2024", "2024": "2023"}.get(year_sel)
    return f"YEAR(CAST({col} AS DATE)) = {prior}" if prior else "1=0"

def _prior_wh(year_sel: str, quarter_sel: str, col: str) -> str:
    return f"{_prior_yf(year_sel, col)} AND {_qf(quarter_sel, col)}"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:{NAVY};margin:0'>🚞 AlpenRail</h2>", unsafe_allow_html=True)
    st.caption("Executive Dashboard")
    st.divider()
    year_sel    = st.selectbox("Year",    ["Both", "2024", "2025"])
    quarter_sel = st.selectbox("Quarter", ["Full Year", "Q1", "Q2", "Q3", "Q4"])
    st.divider()
    st.caption("Filters apply to all panels")

period_label = year_sel if year_sel != "Both" else "2024–2025"
if quarter_sel != "Full Year":
    period_label += f" {quarter_sel}"

# ── Cached queries ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_kpis(year_sel: str, quarter_sel: str):
    cur = query(f"""
        SELECT
            ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue,
            COUNT(*)                                                    AS tickets,
            ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price,
            COUNT(DISTINCT passenger_id)                               AS passengers
        FROM tickets
        WHERE {_wh(year_sel, quarter_sel, 'booking_date')}
    """).iloc[0]

    prior = query(f"""
        SELECT
            ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue,
            COUNT(*)                                                    AS tickets,
            ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price,
            COUNT(DISTINCT passenger_id)                               AS passengers
        FROM tickets
        WHERE {_prior_wh(year_sel, quarter_sel, 'booking_date')}
    """).iloc[0]

    cur_ot = query(f"""
        SELECT ROUND(
            SUM(CASE WHEN DATEDIFF('minute',
                CAST(scheduled_arrival AS TIMESTAMP),
                CAST(actual_arrival AS TIMESTAMP)) <= 3
            THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS pct
        FROM journeys
        WHERE {_wh(year_sel, quarter_sel, 'scheduled_departure')}
    """).iloc[0, 0]

    prior_ot = query(f"""
        SELECT ROUND(
            SUM(CASE WHEN DATEDIFF('minute',
                CAST(scheduled_arrival AS TIMESTAMP),
                CAST(actual_arrival AS TIMESTAMP)) <= 3
            THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS pct
        FROM journeys
        WHERE {_prior_wh(year_sel, quarter_sel, 'scheduled_departure')}
    """).iloc[0, 0]

    return cur, prior, cur_ot, prior_ot


@st.cache_data(ttl=3600)
def get_monthly_revenue(year_sel: str, quarter_sel: str):
    df = query(f"""
        SELECT
            YEAR(CAST(booking_date AS DATE))  AS yr,
            MONTH(CAST(booking_date AS DATE)) AS mo,
            ROUND(SUM(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 0) AS revenue
        FROM tickets
        WHERE YEAR(CAST(booking_date AS DATE)) IN (2024, 2025)
          AND {_qf(quarter_sel, 'booking_date')}
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)
    df["month"] = df["mo"].map(MONTH_NAMES)
    df["year"]  = df["yr"].astype(str)
    return df


@st.cache_data(ttl=3600)
def get_ontime_by_route(year_sel: str, quarter_sel: str):
    df = query(f"""
        SELECT
            route_id,
            ROUND(SUM(CASE WHEN DATEDIFF('minute',
                CAST(scheduled_arrival AS TIMESTAMP),
                CAST(actual_arrival AS TIMESTAMP)) <= 3
            THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS pct_on_time
        FROM journeys
        WHERE {_wh(year_sel, quarter_sel, 'scheduled_departure')}
        GROUP BY route_id
        ORDER BY pct_on_time
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    df["color"] = df["pct_on_time"].apply(
        lambda v: RED if v < 85 else (AMBER if v < 93 else GREEN)
    )
    return df


@st.cache_data(ttl=3600)
def get_avg_price_channel(year_sel: str, quarter_sel: str):
    return query(f"""
        SELECT
            channel,
            ROUND(AVG(CAST(REPLACE(price_chf,',','.') AS DOUBLE)), 2) AS avg_price,
            COUNT(*) AS tickets
        FROM tickets
        WHERE {_wh(year_sel, quarter_sel, 'booking_date')}
        GROUP BY channel
        ORDER BY avg_price DESC
    """)


@st.cache_data(ttl=3600)
def get_delay_precip(year_sel: str, quarter_sel: str):
    df = query(f"""
        WITH w AS (
            SELECT
                COALESCE(TRY_STRPTIME(date,'%d.%m.%Y'), CAST(date AS DATE)) AS w_date,
                AVG(precip_mm) AS avg_precip
            FROM weather
            GROUP BY w_date
        )
        SELECT
            j.route_id,
            GREATEST(DATEDIFF('minute',
                CAST(j.scheduled_arrival AS TIMESTAMP),
                CAST(j.actual_arrival AS TIMESTAMP)), 0) AS delay_min,
            w.avg_precip
        FROM journeys j
        JOIN w ON CAST(j.scheduled_departure AS DATE) = w.w_date
        WHERE {_wh(year_sel, quarter_sel, 'j.scheduled_departure')}
          AND w.avg_precip > 0
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    return df


@st.cache_data(ttl=3600)
def get_loyalty_spend(year_sel: str, quarter_sel: str):
    return query(f"""
        WITH annual AS (
            SELECT
                t.passenger_id,
                YEAR(CAST(t.booking_date AS DATE)) AS yr,
                SUM(CAST(REPLACE(t.price_chf,',','.') AS DOUBLE)) AS annual_spend
            FROM tickets t
            WHERE {_wh(year_sel, quarter_sel, 't.booking_date')}
            GROUP BY t.passenger_id, yr
        )
        SELECT
            p.loyalty_tier,
            ROUND(AVG(a.annual_spend), 2)  AS avg_spend,
            COUNT(DISTINCT a.passenger_id) AS passengers
        FROM annual a
        JOIN passengers p ON a.passenger_id = p.passenger_id
        GROUP BY p.loyalty_tier
        ORDER BY avg_spend DESC
    """)


@st.cache_data(ttl=3600)
def get_route_volume(year_sel: str, quarter_sel: str):
    df = query(f"""
        SELECT
            j.route_id,
            COUNT(t.ticket_id) AS tickets_sold
        FROM journeys j
        LEFT JOIN tickets t ON t.journey_id = j.journey_id
        WHERE {_wh(year_sel, quarter_sel, 'j.scheduled_departure')}
        GROUP BY j.route_id
        ORDER BY tickets_sold DESC
        LIMIT 8
    """)
    df["route_name"] = df["route_id"].map(ROUTE_LABELS)
    return df


@st.cache_data(ttl=3600)
def get_partner_trend(year_sel: str, quarter_sel: str):
    df = query(f"""
        SELECT
            YEAR(CAST(booking_timestamp AS TIMESTAMP))  AS yr,
            MONTH(CAST(booking_timestamp AS TIMESTAMP)) AS mo,
            partner_type,
            COUNT(*) AS bookings,
            ROUND(SUM(price_chf), 0) AS revenue_chf
        FROM partner_bookings
        WHERE is_cancelled = false
          AND {_wh(year_sel, quarter_sel, 'booking_timestamp')}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """)
    df["month"] = df["mo"].map(MONTH_NAMES)
    df["year"]  = df["yr"].astype(str)
    df["period"] = df["yr"].astype(str) + "-" + df["mo"].apply(lambda m: f"{m:02d}")
    return df


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{NAVY};margin-bottom:0'>AlpenRail — Executive Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown(f"**Period: {period_label}**  ·  Ticket revenue · Punctuality · Onboard & partner performance")
st.divider()

# ── Row 1: KPI Cards ──────────────────────────────────────────────────────────
cur, prior, cur_ot, prior_ot = get_kpis(year_sel, quarter_sel)

def pct_delta(a, b):
    return f"{(a - b) / abs(b) * 100:+.1f}% vs prior yr" if b and b != 0 else None

def pp_delta(a, b):
    return f"{a - b:+.1f} pp vs prior yr" if b is not None and b == b else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue (CHF)", f"CHF {cur.revenue / 1e6:.2f}M",
          delta=pct_delta(cur.revenue, prior.revenue))
c2.metric("On-Time %", f"{cur_ot:.1f}%",
          delta=pp_delta(cur_ot, prior_ot) if prior_ot else None)
c3.metric("Avg Ticket Price", f"CHF {cur.avg_price:.2f}",
          delta=pct_delta(cur.avg_price, prior.avg_price))
c4.metric("Unique Passengers", f"{int(cur.passengers):,}",
          delta=pct_delta(cur.passengers, prior.passengers))

st.divider()

# ── Row 2: Revenue trend | On-time by route ───────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Monthly Ticket Revenue")
    df_rev = get_monthly_revenue(year_sel, quarter_sel)
    fig_rev = px.line(
        df_rev, x="month", y="revenue", color="year",
        markers=True,
        color_discrete_map={"2024": NAVY, "2025": RED},
        labels={"revenue": "Revenue (CHF)", "month": "Month", "year": "Year"},
        category_orders={"month": list(MONTH_NAMES.values())},
    )
    fig_rev.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        legend_title_text="",
        yaxis_tickformat=",.0f",
        margin=dict(t=10, b=10),
    )
    fig_rev.update_traces(line_width=2.5)
    st.plotly_chart(fig_rev, use_container_width=True)

with col_r:
    st.subheader("On-Time % by Route")
    df_ot = get_ontime_by_route(year_sel, quarter_sel)
    fig_ot = go.Figure(go.Bar(
        x=df_ot["pct_on_time"],
        y=df_ot["route_name"],
        orientation="h",
        marker_color=df_ot["color"].tolist(),
        text=df_ot["pct_on_time"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_ot.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(range=[75, 100], title="On-Time %"),
        yaxis_title="",
        margin=dict(t=10, b=10),
        shapes=[
            dict(type="line", x0=85, x1=85, y0=-0.5, y1=len(df_ot)-0.5,
                 line=dict(color=RED, dash="dash", width=1.5)),
            dict(type="line", x0=93, x1=93, y0=-0.5, y1=len(df_ot)-0.5,
                 line=dict(color=AMBER, dash="dash", width=1.5)),
        ],
        annotations=[
            dict(x=85, y=len(df_ot)-0.3, text="85% threshold", showarrow=False,
                 font=dict(color=RED, size=10), xanchor="left"),
            dict(x=93, y=len(df_ot)-0.3, text="93% threshold", showarrow=False,
                 font=dict(color=AMBER, size=10), xanchor="left"),
        ],
    )
    st.plotly_chart(fig_ot, use_container_width=True)

st.divider()

# ── Row 3: Avg price by channel | Delay vs precipitation ─────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Avg Ticket Price by Channel")
    df_ch = get_avg_price_channel(year_sel, quarter_sel)
    fig_ch = px.bar(
        df_ch, x="channel", y="avg_price",
        text="avg_price",
        color="avg_price",
        color_continuous_scale=["#A8C7E8", NAVY],
        labels={"avg_price": "Avg Price (CHF)", "channel": "Channel"},
    )
    fig_ch.update_traces(texttemplate="CHF %{text:.2f}", textposition="outside")
    fig_ch.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        coloraxis_showscale=False,
        margin=dict(t=10, b=10),
        yaxis=dict(range=[0, df_ch["avg_price"].max() * 1.15]),
    )
    st.plotly_chart(fig_ch, use_container_width=True)

with col_r:
    st.subheader("Delay vs Precipitation — by Route")
    df_dp = get_delay_precip(year_sel, quarter_sel)
    if df_dp.empty:
        st.info("No weather-matching journey data for this period.")
    else:
        fig_dp = px.scatter(
            df_dp.sample(min(4000, len(df_dp)), random_state=42),
            x="avg_precip", y="delay_min", color="route_name",
            opacity=0.45, trendline="ols",
            color_discrete_map=ROUTE_COLORS,
            labels={"avg_precip": "Avg Daily Precip (mm)",
                    "delay_min": "Delay (min)", "route_name": "Route"},
        )
        fig_dp.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend_title_text="Route",
            margin=dict(t=10, b=10),
            yaxis=dict(range=[-1, df_dp["delay_min"].quantile(0.98)]),
        )
        st.plotly_chart(fig_dp, use_container_width=True)

st.divider()

# ── Row 4: Loyalty spend ──────────────────────────────────────────────────────
st.subheader("Loyalty Tier — Avg Annual Spend per Passenger")
df_loy = get_loyalty_spend(year_sel, quarter_sel)

if not df_loy.empty:
    top_spend  = df_loy.iloc[0]["avg_spend"]
    bot_spend  = df_loy.iloc[-1]["avg_spend"]
    gap        = top_spend - bot_spend
    top_tier   = df_loy.iloc[0]["loyalty_tier"]
    bot_tier   = df_loy.iloc[-1]["loyalty_tier"]

    fig_loy = px.bar(
        df_loy, x="loyalty_tier", y="avg_spend",
        text="avg_spend",
        color="loyalty_tier",
        color_discrete_sequence=[NAVY, AMBER, "#7B9EC4"],
        labels={"avg_spend": "Avg Annual Spend (CHF)", "loyalty_tier": "Loyalty Tier"},
    )
    fig_loy.update_traces(texttemplate="CHF %{text:,.2f}", textposition="outside")
    fig_loy.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False,
        margin=dict(t=40, b=10),
        yaxis=dict(range=[0, top_spend * 1.2]),
        annotations=[dict(
            x=0.5, y=1.08, xref="paper", yref="paper",
            text=f"<b>{top_tier}</b> cardholders spend CHF {gap:,.0f}/yr more than <b>{bot_tier}</b> — consider upsell campaigns",
            showarrow=False, font=dict(color=NAVY, size=13),
        )],
    )
    st.plotly_chart(fig_loy, use_container_width=True)

st.divider()

# ── Row 5: Route volume | Partner bookings trend ──────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Tickets Sold by Route (Top 8)")
    st.caption("Note: no station-level boarding data in source — route volume used as proxy")
    df_rv = get_route_volume(year_sel, quarter_sel)
    fig_rv = px.bar(
        df_rv.sort_values("tickets_sold"),
        x="tickets_sold", y="route_name",
        orientation="h", text_auto=",d",
        color="tickets_sold",
        color_continuous_scale=["#A8C7E8", NAVY],
        labels={"tickets_sold": "Tickets Sold", "route_name": "Route"},
    )
    fig_rv.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        coloraxis_showscale=False,
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_rv, use_container_width=True)

with col_r:
    st.subheader("Partner Bookings by Type — Monthly Revenue")
    df_pt = get_partner_trend(year_sel, quarter_sel)
    if df_pt.empty:
        st.info("No partner booking data for this period.")
    else:
        partner_colors = {"ski": NAVY, "cheese": AMBER, "chocolate": RED}
        fig_pt = px.area(
            df_pt, x="period", y="revenue_chf", color="partner_type",
            color_discrete_map=partner_colors,
            labels={"revenue_chf": "Revenue (CHF)", "period": "Month",
                    "partner_type": "Partner Type"},
        )
        fig_pt.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            legend_title_text="Partner",
            margin=dict(t=10, b=10),
            xaxis=dict(
                tickangle=45,
                tickmode="array",
                tickvals=df_pt["period"].unique()[::3],
            ),
            yaxis_tickformat=",.0f",
        )
        st.plotly_chart(fig_pt, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("AlpenRail Analytics Dashboard  |  Data: 2024–2025  |  Built with Streamlit")
