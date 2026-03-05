import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import get_department_workload


def render():
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("Department Workload")

    selected_weeks = st.sidebar.slider(
        "Weeks to show",
        min_value=1,
        max_value=12,
        value=4,
        key="department_workload_weeks",
    )

    df = get_department_workload(weeks=selected_weeks)
    if df.empty:
        st.info("ETL pipeline has not run yet. No department data is available.")
        return

    latest_week = df["week_start"].max()
    current_week_df = df[df["week_start"] == latest_week].copy()

    st.subheader("Current Week Summary")
    dept_columns = st.columns(max(len(current_week_df), 1))
    for idx, (_, row) in enumerate(current_week_df.iterrows()):
        column = dept_columns[idx]
        column.markdown(f"**{row['department_name']}**")
        column.metric("Open", int(row["open_tickets"]))
        column.metric("Resolved", int(row["resolved_tickets"]))
        column.metric("Breached", int(row["breached_tickets"]))
        column.metric("Avg Resolution", f"{row['avg_resolution_hours']:.1f}h")

    workload_df = df[
        ["week_start", "department_name", "open_tickets", "resolved_tickets"]
    ].copy()
    workload_melted = workload_df.melt(
        id_vars=["week_start", "department_name"],
        value_vars=["open_tickets", "resolved_tickets"],
        var_name="ticket_type",
        value_name="ticket_count",
    )

    fig_workload = px.bar(
        workload_melted,
        x="week_start",
        y="ticket_count",
        color="department_name",
        pattern_shape="ticket_type",
        barmode="group",
        title="Weekly Open vs Resolved by Department",
    )
    st.plotly_chart(fig_workload, use_container_width=True)

    breach_df = (
        df.groupby(["week_start", "department_name"], dropna=False)["breached_tickets"]
        .sum()
        .reset_index()
    )
    fig_breach = px.line(
        breach_df,
        x="week_start",
        y="breached_tickets",
        color="department_name",
        title="Weekly SLA Breaches by Department",
    )
    st.plotly_chart(fig_breach, use_container_width=True)

    fig_resolution = px.bar(
        current_week_df,
        x="department_name",
        y="avg_resolution_hours",
        title="Avg Resolution Hours - Current Week",
    )
    st.plotly_chart(fig_resolution, use_container_width=True)

    last_updated = pd.to_datetime(df["last_updated_at"], utc=True, errors="coerce").max()
    if pd.isna(last_updated):
        st.caption("Data last refreshed: Data not yet available")
    else:
        st.caption(
            f"Data last refreshed: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}"
        )
