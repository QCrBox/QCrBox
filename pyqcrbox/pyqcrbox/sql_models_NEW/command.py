from typing import Annotated, Literal, Self, Union

from pydantic import BaseModel, Field, Tag, model_validator

from .call_pattern import CallPattern
from .command_implementation import (
    ImplementedAs,
)

__all__ = ["CommandSpecCreate"]


class CommandSpecCreateBase(BaseModel):
    name: str
    description: str = ""
    merge_cif_su: bool = False
    implemented_as: ImplementedAs

    @property
    def is_python_callable(self):
        return self.implementation.implemented_as == ImplementedAs.python_callable

    @property
    def is_cli_command(self):
        return self.implementation.implemented_as == ImplementedAs.cli_command


class CLICommandSpecCreate(CommandSpecCreateBase):
    implemented_as: Literal["cli_command"]
    call_pattern: CallPattern


class PythonCallableSpecCreate(CommandSpecCreateBase):
    implemented_as: Literal["python_callable"]
    import_path: str
    callable_name: str | None = None

    @model_validator(mode="after")
    def set_callable_name_if_not_provided(self) -> Self:
        """
        If `callable_name` is not explicitly provided, assume it is the same as the command name.
        """
        if self.callable_name is None:
            self.callable_name = self.name
        return self


class InteractiveCommandSpecCreate(CommandSpecCreateBase):
    implemented_as: Literal["interactive"]


CommandSpecCreate = Annotated[
    Union[
        Annotated[CLICommandSpecCreate, Tag("cli_command")],
        Annotated[PythonCallableSpecCreate, Tag("python_callable")],
        Annotated[InteractiveCommandSpecCreate, Tag("interactive")],
    ],
    Field(discriminator="implemented_as"),
]
