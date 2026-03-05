import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import get_daily_volume


def render():
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("Daily Ticket Volume")

    selected_days = st.sidebar.slider(
        "Days to include",
        min_value=7,
        max_value=60,
        value=30,
        key="daily_volume_days",
    )

    df = get_daily_volume(days=selected_days)
    if df.empty:
        st.info("ETL pipeline has not run yet. Daily volume data is not available.")
        return

    all_categories = sorted(df["category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Category filter",
        options=all_categories,
        default=all_categories,
        key="daily_volume_category_filter",
    )
    filtered_df = df[df["category"].isin(selected_categories)].copy()
    if filtered_df.empty:
        st.info("No rows match the selected category filter.")
        return

    total_tickets = int(filtered_df["ticket_count"].fillna(0).sum())
    by_day = filtered_df.groupby("report_date", dropna=False)["ticket_count"].sum()
    peak_day = by_day.idxmax()
    by_category = filtered_df.groupby("category", dropna=False)["ticket_count"].sum()
    most_active_category = by_category.idxmax()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total tickets in period", total_tickets)
    col2.metric("Peak day", str(peak_day))
    col3.metric("Most active category", str(most_active_category))

    trend_df = (
        filtered_df.groupby(["report_date", "category"], dropna=False)["ticket_count"]
        .sum()
        .reset_index()
    )
    fig_trend = px.line(
        trend_df,
        x="report_date",
        y="ticket_count",
        color="category",
        title="Daily Ticket Volume by Category",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    status_df = (
        filtered_df.groupby(["report_date", "status"], dropna=False)["ticket_count"]
        .sum()
        .reset_index()
    )
    fig_status = px.bar(
        status_df,
        x="report_date",
        y="ticket_count",
        color="status",
        barmode="stack",
        title="Daily Ticket Volume by Status",
    )
    st.plotly_chart(fig_status, use_container_width=True)

    priority_df = (
        filtered_df.groupby("priority", dropna=False)["ticket_count"]
        .sum()
        .reset_index()
        .sort_values("ticket_count", ascending=False)
    )
    st.dataframe(priority_df, use_container_width=True)

    last_updated = pd.to_datetime(
        filtered_df["last_updated_at"], utc=True, errors="coerce"
    ).max()
    if pd.isna(last_updated):
        st.caption("Data last refreshed: Data not yet available")
    else:
        st.caption(
            f"Data last refreshed: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}"
        )
