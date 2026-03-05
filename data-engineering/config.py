import os
from dataclasses import dataclass

from dotenv import load_dotenv
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: str
    name: str
    user: str
    password: str

    @property
    def url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class AppConfig:
    db: DBConfig
    log_level: str


def load_config() -> AppConfig:
    load_dotenv()
    db_config = DBConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", "servicehub"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )
    log_level = "INFO"

    return AppConfig(db=db_config, log_level=log_level)
