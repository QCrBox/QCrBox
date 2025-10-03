import functools
import logging
import sys
from enum import Enum
from typing import Any, Optional

import sqlalchemy
import sqlmodel
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine

__all__ = ["StructlogRendererEnum", "get_log_level_as_int", "settings"]


SQLiteDsn = str  # alias for readability
IS_RUNNING_INSIDE_TESTS = hasattr(sys, "_qcrbox_running_inside_tests")
IS_RUNNING_DEBUG_MODE = True


def get_log_level_as_int(level: str):
    mapping = logging.getLevelNamesMapping()
    return mapping[level]


@functools.lru_cache
def create_sqlmodel_engine(url: Optional[SQLiteDsn], echo: bool, connect_args: tuple[(str, Any)]):
    return create_engine(str(url), echo=echo, connect_args=connect_args)


@functools.lru_cache
def _create_db_tables(engine, purge_existing: bool):
    from pyqcrbox.logging import logger
    from pyqcrbox.sql_models import QCrBoxBaseSQLModel  # import here to avoid a circular import

    logger.debug(f"Initialising the database for engine: {engine}")
    if purge_existing:
        logger.debug("Purging existing tables.")
        QCrBoxBaseSQLModel.metadata.drop_all(engine)
    QCrBoxBaseSQLModel.metadata.create_all(engine)


class QCrBoxSettingsBaseModel(BaseSettings):
    model_config = SettingsConfigDict(
        validate_assignment=True,
    )


class DatabaseSettings(QCrBoxSettingsBaseModel):
    url: SQLiteDsn = "sqlite:///:memory:"
    connect_args: dict = {"check_same_thread": False}
    echo: bool = False

    def create_db_and_tables(
        self,
        url: Optional[SQLiteDsn] = None,
        echo: Optional[bool] = None,
        purge_existing_tables: bool = False,
    ) -> None:
        engine = self.get_engine(url=url, echo=echo)
        _create_db_tables(engine, purge_existing_tables)

    def get_engine(self, url: Optional[SQLiteDsn] = None, echo: Optional[bool] = None) -> sqlalchemy.Engine:
        url = url if url is not None else self.url
        echo = echo if echo is not None else self.echo
        return create_sqlmodel_engine(url=url, echo=echo, connect_args=tuple(self.connect_args.items()))

    def get_session(
        self,
        url: Optional[SQLiteDsn] = None,
        echo: Optional[bool] = None,
        init_db: bool = False,
        purge_existing_tables: bool = False,
    ) -> sqlmodel.Session:
        engine = self.get_engine(url=url, echo=echo)
        if init_db:
            _create_db_tables(engine, purge_existing_tables)
        return Session(engine)


class NATSSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 4222
    rpc_timeout: float = 3  # seconds
    graceful_timeout: int = 10  # seconds
    max_reconnect_attempts: int = 1

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return f"nats://{self.host}:{self.port}/"


class SeverSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 11000
    enable_autoreload: bool = False

    @computed_field  # type: ignore
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}/api"


class ClientSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 8002
    keep_calc_work_dir: bool = True


class RegistrySettings(QCrBoxSettingsBaseModel):
    server: SeverSettings = SeverSettings()
    client: ClientSettings = ClientSettings()


class TestingSettings(QCrBoxSettingsBaseModel):
    # report_coverage: bool = False
    use_in_memory_db: bool = False
    use_real_rabbitmq_broker: bool = False


class CLISettings(QCrBoxSettingsBaseModel):
    disable_rich: bool = False


class StructlogRendererEnum(Enum):
    CONSOLE = "console"
    JSON = "json"


class LoggingSettings(QCrBoxSettingsBaseModel):
    log_func_entry_exit: bool = False
    log_level: str = "DEBUG" if IS_RUNNING_DEBUG_MODE or IS_RUNNING_INSIDE_TESTS else "INFO"
    renderer: StructlogRendererEnum = StructlogRendererEnum.JSON

    @property
    def log_level_as_int(self):
        return get_log_level_as_int(self.log_level)


class QCrBoxSettings(QCrBoxSettingsBaseModel):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=[".env.local"],
        env_nested_delimiter="__",
        env_prefix="QCRBOX__",
    )

    debug_mode: bool = IS_RUNNING_DEBUG_MODE
    nats: NATSSettings = NATSSettings()
    registry: RegistrySettings = RegistrySettings()
    db: DatabaseSettings = DatabaseSettings()
    testing: TestingSettings = TestingSettings()
    cli: CLISettings = CLISettings()
    logging: LoggingSettings = LoggingSettings()


settings = QCrBoxSettings()
