from typing import Annotated, Optional

from pydantic import BaseModel, UrlConstraints, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings"]

SQLiteDsn = Annotated[
    MultiHostUrl,
    UrlConstraints(
        host_required=True,
        allowed_schemes=["sqlite", "sqlite+aiosqlite"],
    ),
]


class DatabaseSettings(BaseModel):
    url: SQLiteDsn = "sqlite:///:memory:"


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
