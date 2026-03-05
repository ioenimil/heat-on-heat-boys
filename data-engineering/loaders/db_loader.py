import pandas as pd
from sqlalchemy.engine import Engine

from utils.logger import get_logger

logger = get_logger(__name__)

ANALYTICS_TABLES = [
    "analytics_sla_metrics",
    "analytics_daily_volume",
    "analytics_agent_performance",
    "analytics_department_workload",
]


def load_dataframe(df: pd.DataFrame, table_name: str, engine: Engine) -> int:
    if table_name not in ANALYTICS_TABLES:
        raise ValueError(
            f"Invalid analytics table '{table_name}'. Allowed tables: {ANALYTICS_TABLES}"
        )

    if df is None or df.empty:
        logger.warning("Skipping load for %s: dataframe is empty.", table_name)
        return 0

    try:
        df.to_sql(
            table_name,
            engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=500,
        )
        rows_written = len(df)
        logger.info("Loaded %d rows into %s", rows_written, table_name)
        return rows_written
    except Exception as exc:
        raise RuntimeError(f"Failed to load dataframe into {table_name}") from exc
