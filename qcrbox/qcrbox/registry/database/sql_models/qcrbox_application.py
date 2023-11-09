from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship
from typing import List, Optional

from .qcrbox_base_sql_model import QCrBoxBaseSQLModel
from .qcrbox_container import ContainerStatus


class QCrBoxApplication(BaseModel):
    id: int
    # qcrbox_id: str
    name: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    registered_at: datetime = Field(default_factory=datetime.now)


class QCrBoxApplicationDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    # qcrbox_id: str = Field(unique=True, nullable=False)
    name: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: List["QCrBoxCommandDB"] = Relationship(back_populates="application")
    containers: List["QCrBoxContainerDB"] = Relationship(back_populates="application")


class QCrBoxApplicationRead(BaseModel):
    id: int
    # qcrbox_id: str
    name: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    registered_at: datetime


class QCrBoxApplicationCreate(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    routing_key__registry_to_application: str
    container_qcrbox_id: str
    container_startup_status: Optional[ContainerStatus] = ContainerStatus.READY
