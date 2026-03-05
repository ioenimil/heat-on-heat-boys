from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from utils.logger import get_logger

logger = get_logger(__name__)

_engine: Optional[Engine] = None


def get_engine(database_url: str) -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        logger.info("Created SQLAlchemy engine with pooled connection settings.")
    return _engine


def test_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection test succeeded.")
        return True
    except SQLAlchemyError as exc:
        logger.error("Database connection test failed: %s", exc)
        return False
