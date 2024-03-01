from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, Relationship, UniqueConstraint

from .parameter_spec import ParameterSpecCreate, ParameterSpecDB
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    gui = "GUI"


class CommandSpecBase(BaseModel):
    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    description: str = ""
    # TODO: verify that implemented_as == "GUI" when interactive == True


class CommandSpecCreate(CommandSpecBase):
    parameters: list[ParameterSpecCreate] = []


class CommandSpecDB(CommandSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")
    parameters: list[ParameterSpecDB] = Relationship(back_populates="command")
