import os
import sys
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

PIPELINE_PATH = "/opt/airflow/pipeline"
if PIPELINE_PATH not in sys.path:
    sys.path.insert(0, PIPELINE_PATH)

from config import load_config
from seeders.sample_data import run_seeder
from utils.db import get_engine, test_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_engine():
    try:
        config = load_config()
        return get_engine(config.db.url)
    except ValueError as exc:
        logger.exception("Failed to load config in seed DAG _get_engine.")
        raise AirflowFailException(
            "task=_get_engine failed due to invalid config values. "
            "Check DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD in airflow.env. "
            f"error={exc}"
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to initialize engine in seed DAG _get_engine.")
        raise AirflowFailException(
            "task=_get_engine failed with SQLAlchemyError. "
            "Check database credentials and postgres health. "
            f"error={exc}"
        ) from exc


def task_environment_guard(**context):
    del context
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if app_env != "development":
        raise AirflowFailException(
            f"task=task_environment_guard failed: APP_ENV='{app_env}'. "
            "No database connection was made. "
            "Check APP_ENV in data-engineering/airflow.env."
        )

    db_host = os.environ.get("DB_HOST", "").strip() or "<unset>"
    logger.info("Environment guard passed. APP_ENV=%s", app_env)
    logger.info("Seeder will target DB_HOST=%s", db_host)


def task_confirm_connection(**context):
    del context
    try:
        engine = _get_engine()
        if not test_connection(engine):
            raise AirflowFailException(
                "task=task_confirm_connection failed: test_connection returned False. "
                "Check DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD."
            )
    except ValueError as exc:
        logger.exception("Value error in task_confirm_connection.")
        raise AirflowFailException(
            "task=task_confirm_connection failed due to invalid configuration. "
            "Check airflow.env pipeline DB variables. "
            f"error={exc}"
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_confirm_connection.")
        raise AirflowFailException(
            "task=task_confirm_connection failed with SQLAlchemyError. "
            "Check DB connectivity and credentials. "
            f"error={exc}"
        ) from exc


def task_run_seeder(**context):
    del context
    try:
        engine = _get_engine()
        run_seeder(engine)
        logger.info("Seeder task completed.")
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error in task_run_seeder.")
        raise AirflowFailException(
            "task=task_run_seeder failed with SQLAlchemyError during seeding. "
            "Database may be in a partial state; check users and service_requests counts. "
            f"error={exc}"
        ) from exc
    except RuntimeError as exc:
        logger.exception("Runtime error in task_run_seeder.")
        raise AirflowFailException(
            "task=task_run_seeder failed with RuntimeError during seeding. "
            "Database may be in a partial state; check users and service_requests counts. "
            f"error={exc}"
        ) from exc


def task_seed_summary(**context):
    del context
    try:
        engine = _get_engine()
        with engine.connect() as connection:
            role_counts = connection.execute(
                text("SELECT role, COUNT(*) AS count FROM users GROUP BY role ORDER BY role")
            ).mappings().all()
            ticket_count = int(
                connection.execute(text("SELECT COUNT(*) FROM service_requests")).scalar_one()
            )

        logger.info("========== Seed Summary ==========")
        for row in role_counts:
            logger.info("users role=%s count=%s", row["role"], row["count"])
        logger.info("service_requests count=%d", ticket_count)
        logger.info("==================================")
    except SQLAlchemyError as exc:
        logger.warning("task_seed_summary skipped due to SQLAlchemyError: %s", exc)
    except AirflowFailException as exc:
        logger.warning("task_seed_summary skipped due to engine initialization error: %s", exc)


default_args = {
    "owner": "data-engineering",
    "retries": 0,
    "depends_on_past": False,
}

with DAG(
    dag_id="servicehub_seed",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["servicehub", "seed", "development"],
    default_args=default_args,
) as dag:
    environment_guard_task = PythonOperator(
        task_id="environment_guard",
        python_callable=task_environment_guard,
    )

    confirm_connection_task = PythonOperator(
        task_id="confirm_connection",
        python_callable=task_confirm_connection,
    )

    run_seeder_task = PythonOperator(
        task_id="run_seeder",
        python_callable=task_run_seeder,
    )

    seed_summary_task = PythonOperator(
        task_id="seed_summary",
        python_callable=task_seed_summary,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    environment_guard_task >> confirm_connection_task >> run_seeder_task >> seed_summary_task
