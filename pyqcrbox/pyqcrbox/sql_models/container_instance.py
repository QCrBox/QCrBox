from datetime import datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .base import QCrBoxPydanticBaseModel

__all__ = ["ContainerInstanceDB", "ContainerInstanceResponse", "ContainerInstanceStatusEnum"]


class ContainerInstanceStatusEnum(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    GONE = "gone"


class ContainerInstanceDB(SQLModel, table=True):
    """Model for tracking a live application container (registry client).

    One row per container that has registered with the registry server via
    NATS. Rows are kept up to date through client heartbeats, deleted on
    graceful client shutdown and marked as ``gone`` by the server's stale
    instance sweeper when heartbeats stop arriving.
    """

    __tablename__ = "container_instance"
    __table_args__ = (UniqueConstraint("private_inbox"),)

    id: int | None = Field(default=None, primary_key=True)
    client_id: str = Field(index=True)
    private_inbox: str = Field(index=True)
    application_id: int = Field(foreign_key="application.id")
    status: ContainerInstanceStatusEnum = ContainerInstanceStatusEnum.IDLE
    registered_at: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    pyqcrbox_version: str
    # Docker container id, set by the orchestrator for containers it spawned;
    # None for containers started externally (e.g. via docker compose).
    docker_container_id: str | None = None
    # Reserved for per-user container binding (not populated yet)
    owner_user_id: str | None = None

    def to_response_model(self, application_slug: str, application_version: str) -> "ContainerInstanceResponse":
        return ContainerInstanceResponse(
            id=self.id,
            client_id=self.client_id,
            private_inbox=self.private_inbox,
            application_slug=application_slug,
            application_version=application_version,
            status=ContainerInstanceStatusEnum(self.status),
            registered_at=self.registered_at,
            last_seen=self.last_seen,
            pyqcrbox_version=self.pyqcrbox_version,
            docker_container_id=self.docker_container_id,
            owner_user_id=self.owner_user_id,
        )


class ContainerInstanceResponse(QCrBoxPydanticBaseModel):
    id: int
    client_id: str
    private_inbox: str
    application_slug: str
    application_version: str
    status: ContainerInstanceStatusEnum
    registered_at: datetime
    last_seen: datetime
    pyqcrbox_version: str
    docker_container_id: str | None = None
    owner_user_id: str | None = None
