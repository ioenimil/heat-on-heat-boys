import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from utils.logger import get_logger

logger = get_logger(__name__)


def extract_service_requests(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT sr.*,
          u_req.full_name AS requester_name,
          u_agt.full_name AS agent_name,
          d.name          AS department_name,
          d.category      AS department_category
        FROM service_requests sr
        JOIN users u_req        ON sr.requester_id   = u_req.id
        LEFT JOIN users u_agt   ON sr.assigned_to_id = u_agt.id
        LEFT JOIN departments d ON sr.department_id  = d.id
        ORDER BY sr.created_at DESC
        """
    )
    try:
        with engine.connect() as connection:
            dataframe = pd.read_sql(query, connection)
        logger.info("Extracted service_requests rows=%d", len(dataframe))
        return dataframe
    except SQLAlchemyError as exc:
        logger.exception(
            "extract_service_requests failed while querying service_requests table."
        )
        raise RuntimeError("extract_service_requests failed for service_requests") from exc
    except Exception as exc:
        logger.exception(
            "extract_service_requests encountered an unexpected error while querying service_requests."
        )
        raise RuntimeError("extract_service_requests failed for service_requests") from exc


def extract_sla_policies(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, category, priority, response_time_hours, resolution_time_hours
        FROM sla_policies ORDER BY category, priority
        """
    )
    try:
        with engine.connect() as connection:
            dataframe = pd.read_sql(query, connection)
        logger.info("Extracted sla_policies rows=%d", len(dataframe))
        return dataframe
    except SQLAlchemyError as exc:
        logger.exception(
            "extract_sla_policies failed while querying sla_policies table."
        )
        raise RuntimeError("extract_sla_policies failed for sla_policies") from exc
    except Exception as exc:
        logger.exception(
            "extract_sla_policies encountered an unexpected error while querying sla_policies."
        )
        raise RuntimeError("extract_sla_policies failed for sla_policies") from exc


def extract_users(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, full_name, email, role, department, created_at
        FROM users WHERE is_active = TRUE
        """
    )
    try:
        with engine.connect() as connection:
            dataframe = pd.read_sql(query, connection)
        logger.info("Extracted active users rows=%d", len(dataframe))
        return dataframe
    except SQLAlchemyError as exc:
        logger.exception("extract_users failed while querying users table.")
        raise RuntimeError("extract_users failed for users") from exc
    except Exception as exc:
        logger.exception(
            "extract_users encountered an unexpected error while querying users."
        )
        raise RuntimeError("extract_users failed for users") from exc


def extract_departments(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, name, category, contact_email
        FROM departments WHERE is_active = TRUE
        """
    )
    try:
        with engine.connect() as connection:
            dataframe = pd.read_sql(query, connection)
        logger.info("Extracted active departments rows=%d", len(dataframe))
        return dataframe
    except SQLAlchemyError as exc:
        logger.exception(
            "extract_departments failed while querying departments table."
        )
        raise RuntimeError("extract_departments failed for departments") from exc
    except Exception as exc:
        logger.exception(
            "extract_departments encountered an unexpected error while querying departments."
        )
        raise RuntimeError("extract_departments failed for departments") from exc
