from datetime import datetime, timezone

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

RESOLVED_STATUSES = {"RESOLVED", "CLOSED"}
OUTPUT_COLUMNS = [
    "agent_id",
    "agent_name",
    "week_start",
    "tickets_assigned",
    "tickets_resolved",
    "avg_resolution_hours",
    "sla_compliance_rate_pct",
    "last_updated_at",
]


def transform_agent_performance(requests_df: pd.DataFrame) -> pd.DataFrame:
    if requests_df is None or requests_df.empty:
        logger.warning("Agent performance transform skipped: requests input is empty.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = requests_df.copy()
    df = df[df["assigned_to_id"].notna()].copy()
    if df.empty:
        logger.warning(
            "Agent performance transform skipped: no rows with assigned_to_id."
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    for column in ["created_at", "resolved_at", "sla_deadline"]:
        df[column] = pd.to_datetime(df[column], utc=True)

    df["week_start"] = df["created_at"].dt.to_period("W").apply(lambda p: p.start_time.date())
    df["is_resolved"] = df["status"].isin(RESOLVED_STATUSES) & df["resolved_at"].notna()
    df["resolved_within_sla"] = (
        df["is_resolved"]
        & df["sla_deadline"].notna()
        & (df["resolved_at"] <= df["sla_deadline"])
    )
    df["resolution_hours"] = np.where(
        df["is_resolved"],
        (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600,
        np.nan,
    )

    grouped = (
        df.groupby(["assigned_to_id", "agent_name", "week_start"], dropna=False)
        .agg(
            tickets_assigned=("id", "count"),
            tickets_resolved=("is_resolved", "sum"),
            avg_resolution_hours=("resolution_hours", "mean"),
            resolved_within_sla=("resolved_within_sla", "sum"),
        )
        .reset_index()
    )

    grouped["tickets_assigned"] = grouped["tickets_assigned"].astype(int)
    grouped["tickets_resolved"] = grouped["tickets_resolved"].astype(int)
    grouped["sla_compliance_rate_pct"] = np.where(
        grouped["tickets_resolved"] > 0,
        (grouped["resolved_within_sla"] / grouped["tickets_resolved"]) * 100,
        0.0,
    )
    grouped["avg_resolution_hours"] = grouped["avg_resolution_hours"].fillna(0.0).round(2)
    grouped["sla_compliance_rate_pct"] = grouped["sla_compliance_rate_pct"].round(2)
    grouped["last_updated_at"] = datetime.now(timezone.utc)

    result = grouped.rename(columns={"assigned_to_id": "agent_id"}).drop(
        columns=["resolved_within_sla"]
    )
    result = result[OUTPUT_COLUMNS]

    logger.info(
        "Agent performance transformed successfully: rows=%d groups=%d",
        len(result),
        result.groupby(["agent_id", "week_start"]).ngroups,
    )
    return result
