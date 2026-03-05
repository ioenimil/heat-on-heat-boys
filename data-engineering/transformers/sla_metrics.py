from datetime import datetime, timezone

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

RESOLVED_STATUSES = {"RESOLVED", "CLOSED"}
OUTPUT_COLUMNS = [
    "category",
    "priority",
    "total_tickets",
    "resolved_tickets",
    "breached_tickets",
    "compliance_rate_pct",
    "avg_resolution_hours",
    "avg_response_hours",
    "last_updated_at",
]


def transform_sla_metrics(
    requests_df: pd.DataFrame,
    sla_policies_df: pd.DataFrame,
) -> pd.DataFrame:
    if requests_df is None or requests_df.empty:
        logger.warning("SLA metrics transform skipped: requests input is empty.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    if sla_policies_df is None or sla_policies_df.empty:
        logger.warning("SLA metrics transform skipped: sla_policies input is empty.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = requests_df.copy()
    for column in ["created_at", "resolved_at", "first_response_at", "sla_deadline"]:
        df[column] = pd.to_datetime(df[column], utc=True)

    df["is_resolved"] = df["status"].isin(RESOLVED_STATUSES) & df["resolved_at"].notna()
    df["resolution_hours"] = np.where(
        df["is_resolved"],
        (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600,
        np.nan,
    )
    df["response_hours"] = np.where(
        df["first_response_at"].notna(),
        (df["first_response_at"] - df["created_at"]).dt.total_seconds() / 3600,
        np.nan,
    )
    df["resolved_within_sla"] = (
        df["is_resolved"]
        & df["sla_deadline"].notna()
        & (df["resolved_at"] <= df["sla_deadline"])
    )
    df["is_sla_breached"] = (
        df["is_sla_breached"].fillna(False).astype(bool)
        if "is_sla_breached" in df.columns
        else False
    )

    grouped = (
        df.groupby(["category", "priority"], dropna=False)
        .agg(
            total_tickets=("id", "count"),
            resolved_tickets=("is_resolved", "sum"),
            breached_tickets=("is_sla_breached", "sum"),
            avg_resolution_hours=("resolution_hours", "mean"),
            avg_response_hours=("response_hours", "mean"),
            resolved_within_sla=("resolved_within_sla", "sum"),
        )
        .reset_index()
    )

    policy_keys = sla_policies_df[["category", "priority"]].drop_duplicates()
    result = policy_keys.merge(grouped, on=["category", "priority"], how="left")

    for count_col in [
        "total_tickets",
        "resolved_tickets",
        "breached_tickets",
        "resolved_within_sla",
    ]:
        result[count_col] = result[count_col].fillna(0).astype(int)

    result["compliance_rate_pct"] = np.where(
        result["resolved_tickets"] > 0,
        (result["resolved_within_sla"] / result["resolved_tickets"]) * 100,
        0.0,
    )
    result["avg_resolution_hours"] = result["avg_resolution_hours"].fillna(0.0)
    result["avg_response_hours"] = result["avg_response_hours"].fillna(0.0)
    result["compliance_rate_pct"] = result["compliance_rate_pct"].round(2)
    result["avg_resolution_hours"] = result["avg_resolution_hours"].round(2)
    result["avg_response_hours"] = result["avg_response_hours"].round(2)
    result["last_updated_at"] = datetime.now(timezone.utc)

    result = result[OUTPUT_COLUMNS]
    logger.info(
        "SLA metrics transformed successfully: rows=%d groups=%d",
        len(result),
        result.groupby(["category", "priority"]).ngroups,
    )
    return result
