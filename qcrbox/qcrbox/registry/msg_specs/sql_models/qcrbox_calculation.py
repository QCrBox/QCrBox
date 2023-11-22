from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship


class QCrBoxCalculation(BaseModel):
    id: int
    command_id: int
    arguments: dict
    started_at: datetime


class QCrBoxCalculationDB(SQLModel, table=True):
    __tablename__ = "calculation"
    __table_args__ = (UniqueConstraint("command_id", "started_at"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    command_id: str = Field(foreign_key="command.id")
    arguments: dict = Field(sa_column=Column(JSON), default={})
    started_at: datetime = Field(default_factory=datetime.now)
    container_qcrbox_id: str = Field(foreign_key="container.qcrbox_id", nullable=False)

    command: "QCrBoxCommandDB" = Relationship(back_populates="calculations")
    container: "QCrBoxContainerDB" = Relationship(back_populates="calculations")


class QCrBoxCalculationStatusDetails(BaseModel):
    status: str
    details: dict


class QCrBoxCalculationRead(BaseModel):
    id: int
    command_id: int
    arguments: dict
    started_at: datetime
    status_details: Optional[QCrBoxCalculationStatusDetails] = None


class QCrBoxCalculationCreate(BaseModel):
    command_id: int
    arguments: Optional[dict] = None
    container_qcrbox_id: Optional[str] = None
