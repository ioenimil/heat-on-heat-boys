import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import get_active_breach_count, get_at_risk_tickets, get_sla_metrics


def render():
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("ServiceHub Dashboard")
    st.caption("Operational overview - data refreshed nightly at midnight UTC")

    df = get_sla_metrics()
    if df.empty:
        st.info("ETL pipeline has not run yet. Analytics data is not available.")
        return

    total_tickets = int(df["total_tickets"].fillna(0).sum())
    total_breached = int(df["breached_tickets"].fillna(0).sum())
    resolved_total = df["resolved_tickets"].fillna(0).sum()
    if resolved_total > 0:
        overall_compliance = float(
            (df["compliance_rate_pct"].fillna(0) * df["resolved_tickets"].fillna(0)).sum()
            / resolved_total
        )
    else:
        overall_compliance = 0.0

    active_breaches_live = int(get_active_breach_count())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric(
        "Overall SLA Compliance",
        f"{overall_compliance:.1f}%",
        delta=f"{(overall_compliance - 90.0):.1f}%",
        delta_color="normal",
    )
    col3.metric("Total Breached Tickets", total_breached)
    col4.metric(
        "Active Breaches (live)",
        active_breaches_live,
        delta=active_breaches_live,
        delta_color="inverse",
    )

    st.subheader("Tickets Approaching SLA Breach (next 2 hours)")
    at_risk_df = get_at_risk_tickets()
    if at_risk_df.empty:
        st.success("No tickets at risk of breaching in the next 2 hours")
    else:
        st.warning(f"{len(at_risk_df)} ticket(s) at risk in the next 2 hours")
        st.dataframe(at_risk_df, use_container_width=True)

    chart_col1, chart_col2 = st.columns(2)

    compliance_by_category = (
        df.groupby("category", dropna=False)["compliance_rate_pct"].mean().reset_index()
    )
    fig_compliance = px.bar(
        compliance_by_category,
        x="category",
        y="compliance_rate_pct",
        color="category",
        title="SLA Compliance by Category",
    )
    chart_col1.plotly_chart(fig_compliance, use_container_width=True)

    ticket_distribution = (
        df.groupby("priority", dropna=False)["total_tickets"].sum().reset_index()
    )
    fig_priority = px.pie(
        ticket_distribution,
        values="total_tickets",
        names="priority",
        title="Ticket Distribution by Priority",
    )
    chart_col2.plotly_chart(fig_priority, use_container_width=True)

    last_updated = pd.to_datetime(df["last_updated_at"], utc=True, errors="coerce").max()
    if pd.isna(last_updated):
        st.caption("Data last refreshed: Data not yet available")
    else:
        st.caption(
            f"Data last refreshed: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}"
        )
