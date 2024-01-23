from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from .qcrbox_container import CommandContainerLink
from .qcrbox_keyword import CommandKeywordLink


class QCrBoxCommand(BaseModel):
    id: int
    name: str
    parameters: dict
    application_id: int


class QCrBoxCommandDB(SQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "parameters", "application_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    parameters: dict = Field(sa_column=Column(JSON), default={})
    application_id: Optional[int] = Field(foreign_key="application.id", nullable=False)

    application: "QCrBoxApplicationDB" = Relationship(back_populates="commands")
    keywords: List["KeywordDB"] = Relationship(back_populates="commands", link_model=CommandKeywordLink)
    calculations: List["QCrBoxCalculationDB"] = Relationship(back_populates="command")
    containers: List["QCrBoxContainerDB"] = Relationship(back_populates="commands", link_model=CommandContainerLink)


class QCrBoxCommandRead(BaseModel):
    id: int
    name: str
    parameters: dict
    application_id: int


class QCrBoxCommandCreate(BaseModel):
    name: str
    parameters: dict
    application_id: int
    container_id: int
