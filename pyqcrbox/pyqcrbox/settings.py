import functools
import logging
import sys
from enum import Enum
from typing import Any, Optional

import sqlalchemy
import sqlmodel
from loguru import logger
from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine

__all__ = ["settings"]

IS_RUNNING_INSIDE_TESTS = hasattr(sys, "_qcrbox_running_inside_tests")

SQLiteDsn = str  # alias for readability


def get_log_level_as_int(level: str):
    mapping = logging.getLevelNamesMapping()
    return mapping[level]


@functools.lru_cache
def create_sqlmodel_engine(url: Optional[SQLiteDsn], echo: bool, connect_args: tuple[(str, Any)]):
    return create_engine(str(url), echo=echo, connect_args=connect_args)


@functools.lru_cache
def _create_db_tables(engine, purge_existing: bool):
    from pyqcrbox.sql_models_NEW_v2 import QCrBoxBaseSQLModel  # import here to avoid a circular import

    logger.debug(f"Initialising the database for engine: {engine}")
    if purge_existing:
        logger.debug("Purging existing tables.")
        QCrBoxBaseSQLModel.metadata.drop_all(engine)
    QCrBoxBaseSQLModel.metadata.create_all(engine)


class DatabaseSettings(BaseModel):
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


class RabbitMQSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    management_port: int = 15672
    rpc_timeout: float = 5.0
    graceful_timeout: Optional[int] = 5

    routing_key_qcrbox_registry: str = "qcrbox-registry"

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"


class NATSSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 4222
    rpc_timeout: float = 3  # seconds
    graceful_timeout: Optional[int] = 5  # seconds

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return f"nats://{self.host}:{self.port}/"


class ServerAPISettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8001

    @computed_field  # type: ignore
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}/"


class ClientAPISettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8002


class RegistrySettings(BaseModel):
    server: ServerAPISettings = ServerAPISettings()
    client: ClientAPISettings = ClientAPISettings()


class TestingSettings(BaseModel):
    # report_coverage: bool = False
    use_in_memory_db: bool = False
    use_real_rabbitmq_broker: bool = False


class CLISettings(BaseModel):
    disable_rich: bool = False


class StructlogRendererEnum(Enum):
    CONSOLE = "console"
    JSON = "json"


class LoggingSettings(BaseModel):
    log_level: str = "INFO" if not IS_RUNNING_INSIDE_TESTS else "DEBUG"
    renderer: StructlogRendererEnum = StructlogRendererEnum.CONSOLE

    @property
    def log_level_as_int(self):
        return get_log_level_as_int(self.log_level)


class QCrBoxSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        # env_file='.env',
        env_nested_delimiter="__",
        env_prefix="QCRBOX__",
    )

    nats: NATSSettings = NATSSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    registry: RegistrySettings = RegistrySettings()
    db: DatabaseSettings = DatabaseSettings()
    testing: TestingSettings = TestingSettings()
    cli: CLISettings = CLISettings()
    logging: LoggingSettings = LoggingSettings()


settings = QCrBoxSettings()
