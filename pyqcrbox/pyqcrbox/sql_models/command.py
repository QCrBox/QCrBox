from enum import Enum
from typing import TYPE_CHECKING, Optional

from loguru import logger
from pydantic import model_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, UniqueConstraint

from .call_pattern import CallPattern
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel

if TYPE_CHECKING:
    from .calculation import CalculationDB


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    # gui = "GUI"
    interactive = "interactive"


class CommandSpecBase(QCrBoxPydanticBaseModel):
    name: str
    implemented_as: ImplementedAs
    interactive: bool = False
    call_pattern: Optional[str] = None  # for CLI commands
    import_path: Optional[str] = None  # for python_callable
    callable_name: Optional[str] = None  # for python_callable
    description: str = ""
    merge_cif_su: bool = False
    # TODO: verify that implemented_as == "GUI" when interactive == True

    # required_cif_entry_sets: list[str] = []
    # optional_cif_entry_sets: list[str] = []
    # custom_cif_categories: list[str] = []


class CommandSpecCreate(CommandSpecBase):
    call_pattern: Optional[CallPattern] = None  # for CLI commands

    parameters: list[dict] = []

    @model_validator(mode="after")
    def validate_interactive_commands(self) -> "CommandSpecCreate":
        if self.interactive and not self.implemented_as == ImplementedAs.gui:
            msg = f"Interactive command {self.name!r} must be implemented as 'GUI', got: {self.implemented_as.value!r}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_call_pattern(self) -> "CommandSpecCreate":
        if self.implemented_as == ImplementedAs.cli and self.call_pattern is None:
            raise ValueError(f"CLI command is missing a call_pattern: {self.name!r}")

        if self.call_pattern is not None:
            call_pattern_params = set(self.call_pattern.param_names)
            cmd_params = set([x["name"] for x in self.parameters])
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

    @model_validator(mode="after")
    def validate_import_path_for_python_callables(self) -> "CommandSpecCreate":
        if self.implemented_as == ImplementedAs.python_callable and self.import_path is None:
            raise ValueError(f"Python callable is missing an import_path: {self.name!r}")

        return self

    @model_validator(mode="after")
    def set_callable_name_for_python_callables(self) -> "CommandSpecCreate":
        if self.implemented_as == ImplementedAs.python_callable and self.callable_name is None:
            self.callable_name = self.name

        return self

    def to_sql_model(self):
        return CommandSpecDB.from_pydantic_model(self)


class CommandSpecDB(CommandSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"),)
    __pydantic_model_cls__ = CommandSpecCreate

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")
    parameters: dict = Field(sa_column=Column(JSON), default={})
    calculations: list["CalculationDB"] = Relationship(back_populates="command")

    # required_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    # optional_cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))
    # custom_cif_categories: list[str] = Field(sa_column=Column(JSON()))

    # def model_dump(self, **kwargs):
    #     data = super().model_dump(**kwargs)
    #     data["parameters"] = [param.model_dump(**kwargs) for param in self.parameters]
    #     return data

    @classmethod
    def from_pydantic_model(cls, command):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(command, pydantic_model_cls)
        data = command.model_dump(exclude={"parameters"})
        # data["parameters"] = [ParameterSpecDB.from_pydantic_model(param) for param in command.parameters]
        data["parameters"] = {param["name"]: param for param in command.parameters}
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)

    def to_read_model(self):
        return CommandSpecWithParameters(**self.model_dump())


class CommandSpecWithParameters(CommandSpecBase):
    id: int
    application_id: int
    parameters: dict
    # cif_entry_sets: list[CifEntrySetRead] = []
