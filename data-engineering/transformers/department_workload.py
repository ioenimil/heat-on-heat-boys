from datetime import datetime, timezone

import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

OPEN_STATUSES = {"OPEN", "ASSIGNED", "IN_PROGRESS"}
RESOLVED_STATUSES = {"RESOLVED", "CLOSED"}
OUTPUT_COLUMNS = [
    "department_id",
    "department_name",
    "week_start",
    "open_tickets",
    "resolved_tickets",
    "breached_tickets",
    "avg_resolution_hours",
    "last_updated_at",
]


def transform_department_workload(requests_df: pd.DataFrame) -> pd.DataFrame:
    if requests_df is None or requests_df.empty:
        logger.warning("Department workload transform skipped: requests input is empty.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = requests_df.copy()
    df = df[df["department_id"].notna()].copy()
    if df.empty:
        logger.warning(
            "Department workload transform skipped: no rows with department_id."
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    for column in ["created_at", "resolved_at"]:
        df[column] = pd.to_datetime(df[column], utc=True)

    df["week_start"] = df["created_at"].dt.to_period("W").apply(lambda p: p.start_time.date())
    df["is_open"] = df["status"].isin(OPEN_STATUSES)
    df["is_resolved"] = df["status"].isin(RESOLVED_STATUSES) & df["resolved_at"].notna()
    df["resolution_hours"] = np.where(
        df["is_resolved"],
        (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600,
        np.nan,
    )
    df["is_sla_breached"] = (
        df["is_sla_breached"].fillna(False).astype(bool)
        if "is_sla_breached" in df.columns
        else False
    )

    grouped = (
        df.groupby(["department_id", "department_name", "week_start"], dropna=False)
        .agg(
            open_tickets=("is_open", "sum"),
            resolved_tickets=("is_resolved", "sum"),
            breached_tickets=("is_sla_breached", "sum"),
            avg_resolution_hours=("resolution_hours", "mean"),
        )
        .reset_index()
    )

    grouped["open_tickets"] = grouped["open_tickets"].astype(int)
    grouped["resolved_tickets"] = grouped["resolved_tickets"].astype(int)
    grouped["breached_tickets"] = grouped["breached_tickets"].astype(int)
    grouped["avg_resolution_hours"] = grouped["avg_resolution_hours"].fillna(0.0).round(2)
    grouped["last_updated_at"] = datetime.now(timezone.utc)

    result = grouped[OUTPUT_COLUMNS]
    logger.info(
        "Department workload transformed successfully: rows=%d groups=%d",
        len(result),
        result.groupby(["department_id", "week_start"]).ngroups,
    )
    return result
