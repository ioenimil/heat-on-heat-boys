import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import get_agent_performance


def render():
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("Agent Performance")

    selected_weeks = st.sidebar.slider(
        "Weeks to show",
        min_value=1,
        max_value=12,
        value=4,
        key="agent_performance_weeks",
    )

    df = get_agent_performance(weeks=selected_weeks)
    if df.empty:
        st.info("ETL pipeline has not run yet. No agent data is available.")
        return

    available_agents = sorted(df["agent_name"].dropna().unique().tolist())
    selected_agents = st.sidebar.multiselect(
        "Agent filter",
        options=available_agents,
        default=available_agents,
        key="agent_performance_agent_filter",
    )

    filtered_df = df[df["agent_name"].isin(selected_agents)].copy()
    if filtered_df.empty:
        st.info("No rows match the selected agent filter.")
        return

    latest_week = filtered_df["week_start"].max()
    current_week_df = filtered_df[filtered_df["week_start"] == latest_week].copy()
    leaderboard_df = current_week_df[
        [
            "agent_name",
            "tickets_assigned",
            "tickets_resolved",
            "avg_resolution_hours",
            "sla_compliance_rate_pct",
        ]
    ].sort_values("tickets_resolved", ascending=False)
    leaderboard_df["sla_compliance_rate_pct"] = leaderboard_df["sla_compliance_rate_pct"].map(
        lambda value: f"{value:.1f}%"
    )

    st.subheader("Current Week Leaderboard")
    st.dataframe(leaderboard_df, use_container_width=True)

    fig_resolution = px.bar(
        current_week_df,
        x="agent_name",
        y="avg_resolution_hours",
        color="agent_name",
        title="Average Resolution Hours - Current Week",
    )
    st.plotly_chart(fig_resolution, use_container_width=True)

    fig_compliance = px.line(
        filtered_df.sort_values("week_start"),
        x="week_start",
        y="sla_compliance_rate_pct",
        color="agent_name",
        title="Agent SLA Compliance Rate Over Time",
    )
    st.plotly_chart(fig_compliance, use_container_width=True)

    fig_resolved = px.line(
        filtered_df.sort_values("week_start"),
        x="week_start",
        y="tickets_resolved",
        color="agent_name",
        title="Tickets Resolved Per Week",
    )
    st.plotly_chart(fig_resolved, use_container_width=True)

    last_updated = pd.to_datetime(
        filtered_df["last_updated_at"], utc=True, errors="coerce"
    ).max()
    if pd.isna(last_updated):
        st.caption("Data last refreshed: Data not yet available")
    else:
        st.caption(
            f"Data last refreshed: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}"
        )
