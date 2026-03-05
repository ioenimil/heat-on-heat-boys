import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import get_sla_metrics


def render():
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("SLA Compliance Metrics")

    df = get_sla_metrics()
    if df.empty:
        st.info("ETL pipeline has not run yet. SLA metrics are not available.")
        return

    all_categories = sorted(df["category"].dropna().unique().tolist())
    all_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    selected_categories = st.sidebar.multiselect(
        "Category filter",
        options=all_categories,
        default=all_categories,
        key="sla_category_filter",
    )
    selected_priorities = st.sidebar.multiselect(
        "Priority filter",
        options=all_priorities,
        default=all_priorities,
        key="sla_priority_filter",
    )

    filtered_df = df[
        df["category"].isin(selected_categories) & df["priority"].isin(selected_priorities)
    ].copy()

    if filtered_df.empty:
        st.info("No SLA rows match the selected filters.")
        return

    best_row = filtered_df.loc[filtered_df["compliance_rate_pct"].idxmax()]
    worst_row = filtered_df.loc[filtered_df["compliance_rate_pct"].idxmin()]

    resolved_weights = filtered_df["resolved_tickets"].fillna(0)
    if resolved_weights.sum() > 0:
        avg_response_weighted = float(
            (filtered_df["avg_response_hours"].fillna(0) * resolved_weights).sum()
            / resolved_weights.sum()
        )
    else:
        avg_response_weighted = float(filtered_df["avg_response_hours"].fillna(0).mean())

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Best compliance",
        f"{best_row['compliance_rate_pct']:.1f}%",
        delta=f"{best_row['category']} / {best_row['priority']}",
    )
    col2.metric(
        "Worst compliance",
        f"{worst_row['compliance_rate_pct']:.1f}%",
        delta=f"{worst_row['category']} / {worst_row['priority']}",
    )
    col3.metric("Avg response time", f"{avg_response_weighted:.1f}h")

    table_df = filtered_df[
        [
            "category",
            "priority",
            "total_tickets",
            "resolved_tickets",
            "breached_tickets",
            "compliance_rate_pct",
            "avg_resolution_hours",
            "avg_response_hours",
        ]
    ].copy()
    table_df["compliance_rate_pct"] = table_df["compliance_rate_pct"].map(
        lambda value: f"{value:.1f}%"
    )
    st.dataframe(table_df, use_container_width=True)

    heatmap_df = (
        filtered_df.pivot_table(
            index="category",
            columns="priority",
            values="compliance_rate_pct",
            aggfunc="mean",
        )
        .reindex(columns=all_priorities)
        .sort_index()
    )

    fig_heatmap = go.Figure(
        data=go.Heatmap(
            z=heatmap_df.values,
            x=heatmap_df.columns.tolist(),
            y=heatmap_df.index.tolist(),
            colorscale="RdYlGn",
            colorbar={"title": "%"},
        )
    )
    for row_index, category in enumerate(heatmap_df.index.tolist()):
        for col_index, priority in enumerate(heatmap_df.columns.tolist()):
            value = heatmap_df.iloc[row_index, col_index]
            if pd.notna(value):
                fig_heatmap.add_annotation(
                    x=priority,
                    y=category,
                    text=f"{value:.1f}",
                    showarrow=False,
                )
    fig_heatmap.update_layout(title="SLA Compliance Rate Heatmap (%)")
    st.plotly_chart(fig_heatmap, use_container_width=True)

    fig_resolution = px.bar(
        filtered_df,
        x="category",
        y="avg_resolution_hours",
        color="priority",
        barmode="group",
        title="Average Resolution Hours by Category and Priority",
    )
    st.plotly_chart(fig_resolution, use_container_width=True)

    last_updated = pd.to_datetime(
        filtered_df["last_updated_at"], utc=True, errors="coerce"
    ).max()
    if pd.isna(last_updated):
        st.caption("Data last refreshed: Data not yet available")
    else:
        st.caption(
            f"Data last refreshed: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}"
        )
