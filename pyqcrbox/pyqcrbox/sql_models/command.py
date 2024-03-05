from enum import Enum
from typing import Optional

from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint

from .parameter import ParameterCreate, ParameterDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    gui = "GUI"


class CommandCreate(QCrBoxPydanticBaseModel):
    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    description: str = ""
    merge_cif_su: bool = False
    # TODO: verify that implemented_as == "GUI" when interactive == True

    parameters: list[ParameterCreate] = []
    required_cif_entry_sets: list[str] = []
    optional_cif_entry_sets: list[str] = []
    custom_cif_categories: list[str] = []


class CommandDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    # __table_args__ = (UniqueConstraint("name", "application_id"), {"extend_existing": True})
    __table_args__ = (UniqueConstraint("name"), {"extend_existing": True})
    __pydantic_model_cls__ = CommandCreate

    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    description: str = ""
    merge_cif_su: bool = False

    id: Optional[int] = Field(default=None, primary_key=True)

    parameters: list["ParameterDB"] = Relationship(back_populates="command")
    required_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    optional_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    custom_cif_categories: list[str] = Field(sa_column=Column(JSON()))

    @classmethod
    def from_pydantic_model(cls, command):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(command, pydantic_model_cls)
        data = command.model_dump(exclude={"parameters"})
        data["parameters"] = [ParameterDB.from_pydantic_model(param) for param in command.parameters]
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)
