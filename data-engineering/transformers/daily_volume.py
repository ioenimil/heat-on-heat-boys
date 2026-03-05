from datetime import datetime, timezone

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_COLUMNS = [
    "report_date",
    "category",
    "priority",
    "status",
    "ticket_count",
    "last_updated_at",
]


def transform_daily_volume(requests_df: pd.DataFrame) -> pd.DataFrame:
    if requests_df is None or requests_df.empty:
        logger.warning("Daily volume transform skipped: requests input is empty.")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = requests_df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["report_date"] = df["created_at"].dt.date

    grouped = (
        df.groupby(["report_date", "category", "priority", "status"], dropna=False)
        .agg(ticket_count=("id", "count"))
        .reset_index()
    )
    grouped["ticket_count"] = grouped["ticket_count"].astype(int)
    grouped["last_updated_at"] = datetime.now(timezone.utc)

    result = grouped[OUTPUT_COLUMNS]
    logger.info(
        "Daily volume transformed successfully: rows=%d groups=%d",
        len(result),
        result.groupby(["report_date", "category", "priority", "status"]).ngroups,
    )
    return result
