from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .parameter_spec import ParameterSpecCreate
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    gui = "GUI"


class CommandSpecBase(QCrBoxPydanticBaseModel):
    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    description: str = ""
    # TODO: verify that implemented_as == "GUI" when interactive == True


class CommandSpecDB(CommandSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"), {"extend_existing": True})

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")
    parameters: list["ParameterSpecDB"] = Relationship(back_populates="command")


class CommandSpecCreate(CommandSpecBase):
    __qcrbox_sql_model__ = CommandSpecDB

    parameters: list[ParameterSpecCreate] = []
