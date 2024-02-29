import functools
from contextlib import contextmanager
from typing import Annotated, Any, Optional

from pydantic import BaseModel, UrlConstraints, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine

__all__ = ["settings"]

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


class DatabaseSettings(BaseModel):
    url: SQLiteDsn = "sqlite:///:memory:"
    connect_args: dict = {"check_same_thread": False}
    echo: bool = True

    @property
    def engine(self):
        return create_sqlmodel_engine(url=self.url, echo=self.echo, connect_args=tuple(self.connect_args.items()))

    @contextmanager
    def session(self):
        with Session(self.engine) as session:
            yield session


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
