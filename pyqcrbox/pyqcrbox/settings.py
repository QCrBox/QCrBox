import functools
from typing import Annotated, Any, Optional

import sqlalchemy
import sqlmodel
from loguru import logger
from pydantic import BaseModel, UrlConstraints, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine

__all__ = ["settings"]

from pyqcrbox.sql_models import QCrBoxBaseSQLModel

SQLiteDsn = Annotated[
    MultiHostUrl,
    UrlConstraints(
        host_required=True,
        allowed_schemes=["sqlite", "sqlite+aiosqlite"],
    ),
]


@functools.lru_cache
def create_sqlmodel_engine(url: str, echo: bool, connect_args: tuple[(str, Any)]):
    return create_engine(url, echo=echo, connect_args=connect_args)


@functools.lru_cache
def create_db_tables(engine):
    logger.debug(f"Initialising the database for engine: {engine}")
    QCrBoxBaseSQLModel.metadata.create_all(engine)


class DatabaseSettings(BaseModel):
    url: SQLiteDsn = "sqlite:///:memory:"
    connect_args: dict = {"check_same_thread": False}
    echo: bool = False

    def get_engine(self, url: Optional[SQLiteDsn] = None, echo: Optional[bool] = None) -> sqlalchemy.Engine:
        url = url if url is not None else self.url
        echo = echo if echo is not None else self.echo
        return create_sqlmodel_engine(url=url, echo=echo, connect_args=tuple(self.connect_args.items()))

    def get_session(
        self, url: Optional[SQLiteDsn] = None, echo: Optional[bool] = None, init_db: bool = False
    ) -> sqlmodel.Session:
        engine = self.get_engine(url=url, echo=echo)
        if init_db:
            create_db_tables(engine)
        return Session(engine)


class RabbitMQSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    graceful_timeout: Optional[int] = 10

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"


class QCrBoxSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        # env_file='.env',
        env_nested_delimiter="_",
        env_prefix="QCRBOX_",
    )

    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    db: DatabaseSettings = DatabaseSettings()


settings = QCrBoxSettings()
