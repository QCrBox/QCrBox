from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .cif_entry_set import CifEntrySetCreate, CifEntrySetDB
from .command_spec import CommandSpecCreate, CommandSpecDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ApplicationSpecBase(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class ApplicationSpecDB(ApplicationSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: list[CommandSpecDB] = Relationship(back_populates="application")
    cif_entry_sets: list[CifEntrySetDB] = Relationship(back_populates="application")


class ApplicationSpecCreate(ApplicationSpecBase):
    __qcrbox_sql_model__ = ApplicationSpecDB

    commands: list[CommandSpecCreate] = []
    cif_entry_sets: list[CifEntrySetCreate] = []
