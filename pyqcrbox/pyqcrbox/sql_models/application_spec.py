from datetime import datetime
from typing import List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from .command_spec import CommandSpecCreate, CommandSpecDB
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ApplicationSpecBase(SQLModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class ApplicationSpecCreate(ApplicationSpecBase):
    commands: List[CommandSpecCreate] = []


class ApplicationSpecDB(ApplicationSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: List[CommandSpecDB] = Relationship(back_populates="application")
