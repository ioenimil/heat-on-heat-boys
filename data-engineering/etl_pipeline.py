import argparse
import logging
import sys
import time
from datetime import datetime, timezone

import pandas as pd
from config import load_config
from extractors.db_extractor import (
    extract_departments,
    extract_service_requests,
    extract_sla_policies,
    extract_users,
)
from loaders.db_loader import load_dataframe
from seeders.sample_data import run_seeder
from sqlalchemy.engine import Engine
from transformers.agent_performance import transform_agent_performance
from transformers.daily_volume import transform_daily_volume
from transformers.department_workload import transform_department_workload
from transformers.sla_metrics import transform_sla_metrics
from utils.db import get_engine, test_connection
from utils.logger import get_logger
from validators.data_quality import (
    DataQualityError,
    log_quarantine_summary,
    validate_service_requests,
    validate_sla_policies,
)

logger = get_logger(__name__)


def _save_quarantine_df(quarantine_df: pd.DataFrame, engine: Engine) -> int:
    if quarantine_df is None or quarantine_df.empty:
        logger.info("No quarantined rows to persist.")
        return 0

    quarantine_to_save = quarantine_df.copy()
    quarantine_to_save["quarantined_at"] = datetime.now(timezone.utc)
    quarantine_to_save.to_sql(
        "analytics_quarantine_service_requests",
        engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500,
    )
    logger.warning(
        "Saved %d quarantined rows to analytics_quarantine_service_requests",
        len(quarantine_to_save),
    )
    return len(quarantine_to_save)


def run_etl(engine: Engine) -> dict:
    """
    Runs the ETL pipeline.

    The pipeline consists of four phases: extract, validate, transform, and load.
    The extract phase extracts data from the source database into DataFrames.
    The validate phase checks the extracted data for quality issues and quarantines bad rows.
    The transform phase transforms the clean extracted data into the desired analytics format.
    The load phase persists the transformed analytics data to the target database.

    :param engine: The SQLAlchemy engine to use for connecting to the source and target databases.
    :return: A dictionary with the load counts for each analytics table.
    """
    started_at = datetime.now(timezone.utc)
    perf_started = time.perf_counter()
    logger.info("ETL pipeline started at %s", started_at.isoformat())

    logger.info("Extract phase started.")
    requests_df = extract_service_requests(engine)
    sla_policies_df = extract_sla_policies(engine)
    users_df = extract_users(engine)
    departments_df = extract_departments(engine)
    logger.info(
        "Extract phase completed: requests=%d, sla_policies=%d, users=%d, departments=%d",
        len(requests_df),
        len(sla_policies_df),
        len(users_df),
        len(departments_df),
    )

    logger.info("Validation phase started.")
    try:
        validate_sla_policies(sla_policies_df)
    except DataQualityError as exc:
        logger.error("CRITICAL validation failure: %s", exc)
        raise

    clean_df, quarantine_df = validate_service_requests(requests_df, sla_policies_df)
    log_quarantine_summary(quarantine_df)
    quarantine_rows = _save_quarantine_df(quarantine_df, engine)

    if clean_df.empty:
        logger.warning("No clean rows remain after validation. ETL load skipped.")
        return {
            "analytics_sla_metrics": 0,
            "analytics_daily_volume": 0,
            "analytics_agent_performance": 0,
            "analytics_department_workload": 0,
            "analytics_quarantine_service_requests": quarantine_rows,
        }
    logger.info(
        "Validation phase completed: clean_rows=%d quarantined_rows=%d",
        len(clean_df),
        quarantine_rows,
    )

    logger.info("Transform phase started.")
    analytics_sla_metrics_df = transform_sla_metrics(clean_df, sla_policies_df)
    analytics_daily_volume_df = transform_daily_volume(clean_df)
    analytics_agent_performance_df = transform_agent_performance(clean_df)
    analytics_department_workload_df = transform_department_workload(clean_df)
    logger.info(
        "Transform phase completed: sla_metrics=%d, daily_volume=%d, agent_performance=%d, department_workload=%d",
        len(analytics_sla_metrics_df),
        len(analytics_daily_volume_df),
        len(analytics_agent_performance_df),
        len(analytics_department_workload_df),
    )

    logger.info("Load phase started.")
    summary = {
        "analytics_sla_metrics": load_dataframe(
            analytics_sla_metrics_df,
            "analytics_sla_metrics",
            engine,
        ),
        "analytics_daily_volume": load_dataframe(
            analytics_daily_volume_df,
            "analytics_daily_volume",
            engine,
        ),
        "analytics_agent_performance": load_dataframe(
            analytics_agent_performance_df,
            "analytics_agent_performance",
            engine,
        ),
        "analytics_department_workload": load_dataframe(
            analytics_department_workload_df,
            "analytics_department_workload",
            engine,
        ),
        "analytics_quarantine_service_requests": quarantine_rows,
    }
    logger.info("Load phase completed: %s", summary)

    elapsed = time.perf_counter() - perf_started
    logger.info("ETL pipeline completed in %.2f seconds.", elapsed)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="ServiceHub Data Engineering Pipeline")
    execution_group = parser.add_mutually_exclusive_group()
    execution_group.add_argument(
        "--seed-only",
        action="store_true",
        help="Run sample data seeder only, skip ETL transformations/loading.",
    )
    execution_group.add_argument(
        "--skip-seed",
        action="store_true",
        help="Run ETL only, skip sample data seeding.",
    )
    args = parser.parse_args()

    config = load_config()
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    logger.info(
        "Configuration loaded: db_host=%s db_name=%s", config.db.host, config.db.name
    )

    engine = get_engine(config.db.url)
    if not test_connection(engine):
        logger.error("Unable to connect to the database. Exiting with status code 1.")
        sys.exit(1)

    if not args.skip_seed:
        run_seeder(engine)

    if not args.seed_only:
        run_etl(engine)


if __name__ == "__main__":
    main()
