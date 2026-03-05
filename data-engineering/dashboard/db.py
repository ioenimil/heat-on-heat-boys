import os
import sys

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SLA_METRICS_COLUMNS = [
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

DAILY_VOLUME_COLUMNS = [
    "report_date",
    "category",
    "priority",
    "status",
    "ticket_count",
    "last_updated_at",
]

AGENT_PERFORMANCE_COLUMNS = [
    "agent_id",
    "agent_name",
    "week_start",
    "tickets_assigned",
    "tickets_resolved",
    "avg_resolution_hours",
    "sla_compliance_rate_pct",
    "last_updated_at",
]

DEPARTMENT_WORKLOAD_COLUMNS = [
    "department_id",
    "department_name",
    "week_start",
    "open_tickets",
    "resolved_tickets",
    "breached_tickets",
    "avg_resolution_hours",
    "last_updated_at",
]

AT_RISK_COLUMNS = [
    "id",
    "title",
    "category",
    "priority",
    "status",
    "sla_deadline",
    "assigned_to_id",
]

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "servicehub")
DB_USER = os.getenv("DB_USER", "servicehub")
DB_PASSWORD = os.getenv("DB_PASSWORD", "servicehub_pass")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
except SQLAlchemyError as exc:
    st.error(
        "Failed to create database engine. "
        "Check DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD environment variables."
    )
    raise
except Exception as exc:
    st.error(
        "Unexpected error during database engine creation. "
        "Check DB_* environment variables and container networking."
    )
    raise


def _empty_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


@st.cache_data(ttl=300)
def get_sla_metrics() -> pd.DataFrame:
    query = text(
        """
        SELECT * FROM analytics_sla_metrics
        ORDER BY category, priority
        """
    )
    try:
        with ENGINE.connect() as connection:
            return pd.read_sql(query, connection)
    except SQLAlchemyError as exc:
        print(f"get_sla_metrics SQLAlchemyError: {exc}", file=sys.stderr)
        return _empty_df(SLA_METRICS_COLUMNS)
    except Exception as exc:
        print(f"get_sla_metrics unexpected error: {exc}", file=sys.stderr)
        return _empty_df(SLA_METRICS_COLUMNS)


@st.cache_data(ttl=300)
def get_daily_volume(days: int = 30) -> pd.DataFrame:
    safe_days = max(int(days), 1)
    query = text(
        f"""
        SELECT * FROM analytics_daily_volume
        WHERE report_date >= CURRENT_DATE - INTERVAL '{safe_days} days'
        ORDER BY report_date, category
        """
    )
    try:
        with ENGINE.connect() as connection:
            return pd.read_sql(query, connection)
    except SQLAlchemyError as exc:
        print(f"get_daily_volume SQLAlchemyError: {exc}", file=sys.stderr)
        return _empty_df(DAILY_VOLUME_COLUMNS)
    except Exception as exc:
        print(f"get_daily_volume unexpected error: {exc}", file=sys.stderr)
        return _empty_df(DAILY_VOLUME_COLUMNS)


@st.cache_data(ttl=300)
def get_agent_performance(weeks: int = 4) -> pd.DataFrame:
    safe_weeks = max(int(weeks), 1)
    query = text(
        f"""
        SELECT * FROM analytics_agent_performance
        WHERE week_start >= CURRENT_DATE - (INTERVAL '7 days' * {safe_weeks})
        ORDER BY week_start DESC, tickets_resolved DESC
        """
    )
    try:
        with ENGINE.connect() as connection:
            return pd.read_sql(query, connection)
    except SQLAlchemyError as exc:
        print(f"get_agent_performance SQLAlchemyError: {exc}", file=sys.stderr)
        return _empty_df(AGENT_PERFORMANCE_COLUMNS)
    except Exception as exc:
        print(f"get_agent_performance unexpected error: {exc}", file=sys.stderr)
        return _empty_df(AGENT_PERFORMANCE_COLUMNS)


@st.cache_data(ttl=300)
def get_department_workload(weeks: int = 4) -> pd.DataFrame:
    safe_weeks = max(int(weeks), 1)
    query = text(
        f"""
        SELECT * FROM analytics_department_workload
        WHERE week_start >= CURRENT_DATE - (INTERVAL '7 days' * {safe_weeks})
        ORDER BY week_start DESC, department_name
        """
    )
    try:
        with ENGINE.connect() as connection:
            return pd.read_sql(query, connection)
    except SQLAlchemyError as exc:
        print(f"get_department_workload SQLAlchemyError: {exc}", file=sys.stderr)
        return _empty_df(DEPARTMENT_WORKLOAD_COLUMNS)
    except Exception as exc:
        print(f"get_department_workload unexpected error: {exc}", file=sys.stderr)
        return _empty_df(DEPARTMENT_WORKLOAD_COLUMNS)


def get_active_breach_count() -> int:
    query = text(
        """
        SELECT COUNT(*)
        FROM service_requests
        WHERE is_sla_breached = TRUE
          AND status NOT IN ('RESOLVED', 'CLOSED')
        """
    )
    try:
        with ENGINE.connect() as connection:
            value = connection.execute(query).scalar()
            return int(value or 0)
    except SQLAlchemyError as exc:
        print(f"get_active_breach_count SQLAlchemyError: {exc}", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"get_active_breach_count unexpected error: {exc}", file=sys.stderr)
        return 0


def get_at_risk_tickets() -> pd.DataFrame:
    query = text(
        """
        SELECT id, title, category, priority, status, sla_deadline, assigned_to_id
        FROM service_requests
        WHERE is_sla_breached = FALSE
          AND status NOT IN ('RESOLVED', 'CLOSED')
          AND sla_deadline IS NOT NULL
          AND sla_deadline < NOW() + INTERVAL '2 hours'
        ORDER BY sla_deadline ASC
        """
    )
    try:
        with ENGINE.connect() as connection:
            return pd.read_sql(query, connection)
    except SQLAlchemyError as exc:
        print(f"get_at_risk_tickets SQLAlchemyError: {exc}", file=sys.stderr)
        return _empty_df(AT_RISK_COLUMNS)
    except Exception as exc:
        print(f"get_at_risk_tickets unexpected error: {exc}", file=sys.stderr)
        return _empty_df(AT_RISK_COLUMNS)
