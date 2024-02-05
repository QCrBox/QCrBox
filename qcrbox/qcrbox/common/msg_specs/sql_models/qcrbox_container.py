# SPDX-License-Identifier: MPL-2.0

import enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlmodel import Field, Relationship

from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class CommandContainerLink(QCrBoxBaseSQLModel, table=True):
    command_id: Optional[int] = Field(default=None, foreign_key="command.id", primary_key=True)
    container_id: Optional[int] = Field(default=None, foreign_key="container.id", primary_key=True)


class ContainerStatus(str, enum.Enum):
    IDLE = "idle"
    # LOCKED = "locked"
    EXECUTING_COMMAND = "executing_command"
    UNREACHABLE = "unreachable"
    # UNKNOWN = "unknown"


class QCrBoxContainer(BaseModel):
    id: int
    qcrbox_id: str
    application_id: int = Field(foreign_key="application.id")
    routing_key__registry_to_application: str
    status: ContainerStatus


class QCrBoxContainerDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "container"

    id: Optional[int] = Field(default=None, primary_key=True)
    qcrbox_id: str = Field(nullable=False, unique=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    application_id: int = Field(foreign_key="application.id", nullable=False, unique=False)
    routing_key__registry_to_application: str = Field(nullable=False, unique=True)
    status: ContainerStatus

    application: "QCrBoxApplicationDB" = Relationship(back_populates="containers")
    calculations: List["QCrBoxCalculationDB"] = Relationship(back_populates="container")
    commands: List["QCrBoxCommandDB"] = Relationship(back_populates="containers", link_model=CommandContainerLink)


class QCrBoxContainerRead(BaseModel):
    id: int
    qcrbox_id: str
    registered_at: datetime
    application_id: int
    routing_key__registry_to_application: str
    status: str


# class QCrBoxContainerCreate(BaseModel):
#     qcrbox_id: str
#     application_id: int
#     routing_key__registry_to_application: str
