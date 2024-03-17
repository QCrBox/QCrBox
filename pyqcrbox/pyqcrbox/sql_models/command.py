from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import model_validator
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint

from .call_pattern import CallPattern
from .parameter import ParameterSpecCreate, ParameterSpecDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    gui = "GUI"


class CommandSpecCreate(QCrBoxPydanticBaseModel):
    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    call_pattern: Optional[CallPattern] = None
    description: str = ""
    merge_cif_su: bool = False
    # TODO: verify that implemented_as == "GUI" when interactive == True

    parameters: list[ParameterSpecCreate] = []
    required_cif_entry_sets: list[str] = []
    optional_cif_entry_sets: list[str] = []
    custom_cif_categories: list[str] = []

    @model_validator(mode="after")
    def validate_call_pattern(self) -> "CommandSpecCreate":
        if self.interactive and not self.implemented_as == ImplementedAs.gui:
            raise ValueError(
                f"Interactive command {self.name!r} must be implemented as 'GUI', got: {self.implemented_as.value!r}"
            )

        if self.implemented_as == ImplementedAs.cli and self.call_pattern is None:
            raise ValueError(f"CLI command is missing a call_pattern: {self.name!r}")

        if self.call_pattern is not None:
            call_pattern_params = set(self.call_pattern.param_names)
            cmd_params = set([x.name for x in self.parameters])
            if not call_pattern_params.issubset(cmd_params):
                missing_params = sorted(call_pattern_params.difference(cmd_params))
                raise ValueError(
                    f"Command {self.name!r} does not declare all parameters referenced in the call pattern. "
                    f"Missing parameters: {missing_params}"
                )
            if not call_pattern_params.issuperset(cmd_params):
                missing_params = sorted(cmd_params.difference(call_pattern_params))
                logger.warning(
                    f"Command {self.name!r} declares the following parameters "
                    f"that are missing in the call pattern: {missing_params}"
                )

        return self

    def to_sql_model(self):
        return CommandSpecDB.from_pydantic_model(self)


class CommandSpecDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"),)
    __pydantic_model_cls__ = CommandSpecCreate

    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    call_pattern: Optional[str] = None
    description: str = ""
    merge_cif_su: bool = False

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")
    parameters: list["ParameterSpecDB"] = Relationship(back_populates="command")
    command_invocations: list["CommandInvocationDB"] = Relationship(back_populates="command")

    required_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    optional_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    custom_cif_categories: list[str] = Field(sa_column=Column(JSON()))

    @classmethod
    def from_pydantic_model(cls, command):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(command, pydantic_model_cls)
        data = command.model_dump(exclude={"parameters"})
        data["parameters"] = [ParameterSpecDB.from_pydantic_model(param) for param in command.parameters]
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)
