import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from sqlalchemy.exc import SQLAlchemyError

PIPELINE_PATH = "/opt/airflow/pipeline"
if PIPELINE_PATH not in sys.path:
    sys.path.insert(0, PIPELINE_PATH)

from config import load_config
from extractors.db_extractor import extract_service_requests, extract_sla_policies
from loaders.db_loader import load_dataframe
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


def _get_engine():
    try:
        config = load_config()
        return get_engine(config.db.url)
    except ValueError as exc:
        logger.exception("Failed to load pipeline config in _get_engine.")
        raise AirflowFailException(
            "task=_get_engine failed: invalid config value. "
            "Check DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD in airflow.env. "
            f"error={exc}"
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to initialize SQLAlchemy engine in _get_engine.")
        raise AirflowFailException(
            "task=_get_engine failed: database engine initialization error. "
            "Check DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD in airflow.env. "
            f"error={exc}"
        ) from exc


def task_test_connection(**context):
    del context
    try:
        engine = _get_engine()
        if not test_connection(engine):
            raise AirflowFailException(
                "task=task_test_connection failed: test_connection returned False. "
                "Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and postgres health."
            )
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_test_connection.")
        raise AirflowFailException(
            "task=task_test_connection failed with SQLAlchemyError. "
            "Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and postgres readiness. "
            f"error={exc}"
        ) from exc


def task_validate_sla_policies(**context):
    del context
    try:
        engine = _get_engine()
        sla_df = extract_sla_policies(engine)
        validate_sla_policies(sla_df)
        logger.info("task_validate_sla_policies passed.")
    except DataQualityError as exc:
        logger.exception("Data quality failure in task_validate_sla_policies.")
        raise AirflowFailException(
            "task=task_validate_sla_policies failed due to invalid sla_policies data. "
            "Check backend seed/data.sql and ensure all 12 category-priority rows exist. "
            f"error={exc}"
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_validate_sla_policies.")
        raise AirflowFailException(
            "task=task_validate_sla_policies failed with SQLAlchemyError. "
            "Check database connectivity and credentials in airflow.env. "
            f"error={exc}"
        ) from exc
    except RuntimeError as exc:
        logger.exception("Runtime error in task_validate_sla_policies extractor.")
        raise AirflowFailException(
            "task=task_validate_sla_policies failed during extract_sla_policies. "
            "Check source table sla_policies and extractor logs. "
            f"error={exc}"
        ) from exc


def task_extract_and_validate(**context):
    ti = context["ti"]
    try:
        engine = _get_engine()
        raw_df = extract_service_requests(engine)
        sla_df = extract_sla_policies(engine)

        if raw_df.empty:
            logger.warning(
                "task_extract_and_validate found empty service_requests; continuing with zero counts."
            )
            ti.xcom_push(key="raw_row_count", value=0)
            ti.xcom_push(key="clean_row_count", value=0)
            ti.xcom_push(key="quarantine_row_count", value=0)
            return

        clean_df, quarantine_df = validate_service_requests(raw_df, sla_df)
        log_quarantine_summary(quarantine_df)

        ti.xcom_push(key="raw_row_count", value=int(len(raw_df)))
        ti.xcom_push(key="clean_row_count", value=int(len(clean_df)))
        ti.xcom_push(key="quarantine_row_count", value=int(len(quarantine_df)))

        if clean_df.empty:
            raise AirflowFailException(
                "task=task_extract_and_validate failed: clean_df is empty after validation. "
                "Inspect quarantine summary and source data quality."
            )
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_extract_and_validate.")
        raise AirflowFailException(
            "task=task_extract_and_validate failed with SQLAlchemyError. "
            "Check DB connectivity and source table availability. "
            f"error={exc}"
        ) from exc
    except RuntimeError as exc:
        logger.exception("Runtime error in task_extract_and_validate.")
        raise AirflowFailException(
            "task=task_extract_and_validate failed at extractor/validation runtime. "
            "Check extractor SQL and dataframe schema. "
            f"error={exc}"
        ) from exc
    except DataQualityError as exc:
        logger.exception("Data quality error in task_extract_and_validate.")
        raise AirflowFailException(
            "task=task_extract_and_validate failed due to schema-level data quality error. "
            "Check service_requests schema and validator requirements. "
            f"error={exc}"
        ) from exc


def task_transform_and_load(**context):
    ti = context["ti"]
    load_results = {}

    try:
        engine = _get_engine()
        requests_df = extract_service_requests(engine)
        sla_df = extract_sla_policies(engine)

        if requests_df.empty:
            logger.warning("task_transform_and_load found empty source data; skipping loads.")
            ti.xcom_push(key="load_results", value={})
            return

        clean_df, quarantine_df = validate_service_requests(requests_df, sla_df)
        log_quarantine_summary(quarantine_df)
        if clean_df.empty:
            raise AirflowFailException(
                "task=task_transform_and_load failed: no clean rows after validation. "
                "Inspect source data and quarantine reasons."
            )

        transformed_data = {}

        transformer_jobs = [
            ("analytics_sla_metrics", transform_sla_metrics, (clean_df, sla_df)),
            ("analytics_daily_volume", transform_daily_volume, (clean_df,)),
            ("analytics_agent_performance", transform_agent_performance, (clean_df,)),
            (
                "analytics_department_workload",
                transform_department_workload,
                (clean_df,),
            ),
        ]

        for table_name, transform_fn, args in transformer_jobs:
            try:
                transformed_df = transform_fn(*args)
                transformed_data[table_name] = transformed_df
            except RuntimeError as exc:
                logger.exception(
                    "Transformer runtime failure for %s in task_transform_and_load.",
                    table_name,
                )
                transformed_data[table_name] = None
                logger.warning(
                    "Continuing after transformer failure for %s. error=%s",
                    table_name,
                    exc,
                )

        attempted_loads = 0
        failed_loads = 0

        for table_name, transformed_df in transformed_data.items():
            if transformed_df is None:
                continue
            attempted_loads += 1
            try:
                load_results[table_name] = load_dataframe(transformed_df, table_name, engine)
            except SQLAlchemyError as exc:
                failed_loads += 1
                load_results[table_name] = 0
                logger.exception(
                    "SQLAlchemy loader failure for %s in task_transform_and_load.",
                    table_name,
                )
            except RuntimeError as exc:
                failed_loads += 1
                load_results[table_name] = 0
                logger.exception(
                    "Runtime loader failure for %s in task_transform_and_load.",
                    table_name,
                )
                logger.warning("Loader error for %s: %s", table_name, exc)

        if attempted_loads == 0:
            raise AirflowFailException(
                "task=task_transform_and_load failed: all transformers failed and no loads were attempted. "
                "Check transformer logs and input schema."
            )

        if failed_loads == attempted_loads:
            raise AirflowFailException(
                "task=task_transform_and_load failed: all loader operations failed. "
                "Check destination DB permissions/table availability and loader logs."
            )

        if failed_loads > 0:
            logger.warning(
                "Partial load completed in task_transform_and_load: failed_loads=%d attempted_loads=%d",
                failed_loads,
                attempted_loads,
            )

        ti.xcom_push(key="load_results", value=load_results)
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_transform_and_load.")
        raise AirflowFailException(
            "task=task_transform_and_load failed with SQLAlchemyError. "
            "Check DB connection and loader target tables. "
            f"error={exc}"
        ) from exc
    except RuntimeError as exc:
        logger.exception("Runtime error in task_transform_and_load.")
        raise AirflowFailException(
            "task=task_transform_and_load failed with RuntimeError. "
            "Check extractor/loader/transformer logs for details. "
            f"error={exc}"
        ) from exc
    except ValueError as exc:
        logger.exception("Value error in task_transform_and_load.")
        raise AirflowFailException(
            "task=task_transform_and_load failed with ValueError. "
            "Check dataframe shapes and required columns. "
            f"error={exc}"
        ) from exc
    except DataQualityError as exc:
        logger.exception("Data quality error in task_transform_and_load.")
        raise AirflowFailException(
            "task=task_transform_and_load failed due to schema-level validation error. "
            "Check validator messages and source schema alignment. "
            f"error={exc}"
        ) from exc


def task_pipeline_summary(**context):
    try:
        ti = context["ti"]
        raw_count = ti.xcom_pull(task_ids="extract_and_validate", key="raw_row_count") or 0
        clean_count = ti.xcom_pull(task_ids="extract_and_validate", key="clean_row_count") or 0
        quarantine_count = (
            ti.xcom_pull(task_ids="extract_and_validate", key="quarantine_row_count") or 0
        )
        load_results = ti.xcom_pull(task_ids="transform_and_load", key="load_results") or {}

        logger.info("========== ServiceHub ETL Summary ==========")
        logger.info("raw_row_count=%s", raw_count)
        logger.info("clean_row_count=%s", clean_count)
        logger.info("quarantine_row_count=%s", quarantine_count)
        logger.info("load_results=%s", load_results)
        logger.info("============================================")
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception("task_pipeline_summary encountered a non-critical error: %s", exc)


default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "depends_on_past": False,
}

with DAG(
    dag_id="servicehub_etl",
    schedule="0 0 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["servicehub", "etl"],
    default_args=default_args,
) as dag:
    test_connection_task = PythonOperator(
        task_id="test_connection",
        python_callable=task_test_connection,
    )

    validate_sla_policies_task = PythonOperator(
        task_id="validate_sla_policies",
        python_callable=task_validate_sla_policies,
    )

    extract_and_validate_task = PythonOperator(
        task_id="extract_and_validate",
        python_callable=task_extract_and_validate,
    )

    transform_and_load_task = PythonOperator(
        task_id="transform_and_load",
        python_callable=task_transform_and_load,
    )

    pipeline_summary_task = PythonOperator(
        task_id="pipeline_summary",
        python_callable=task_pipeline_summary,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    (
        test_connection_task
        >> validate_sla_policies_task
        >> extract_and_validate_task
        >> transform_and_load_task
        >> pipeline_summary_task
    )
