import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

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
    with engine.connect() as connection:
        dataframe = pd.read_sql(query, connection)
    logger.info("Extracted service_requests rows=%d", len(dataframe))
    return dataframe


def extract_sla_policies(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, category, priority, response_time_hours, resolution_time_hours
        FROM sla_policies ORDER BY category, priority
        """
    )
    with engine.connect() as connection:
        dataframe = pd.read_sql(query, connection)
    logger.info("Extracted sla_policies rows=%d", len(dataframe))
    return dataframe


def extract_users(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, full_name, email, role, department, created_at
        FROM users WHERE is_active = TRUE
        """
    )
    with engine.connect() as connection:
        dataframe = pd.read_sql(query, connection)
    logger.info("Extracted active users rows=%d", len(dataframe))
    return dataframe


def extract_departments(engine: Engine) -> pd.DataFrame:
    query = text(
        """
        SELECT id, name, category, contact_email
        FROM departments WHERE is_active = TRUE
        """
    )
    with engine.connect() as connection:
        dataframe = pd.read_sql(query, connection)
    logger.info("Extracted active departments rows=%d", len(dataframe))
    return dataframe
