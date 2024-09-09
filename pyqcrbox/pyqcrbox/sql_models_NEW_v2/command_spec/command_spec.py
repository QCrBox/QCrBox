from typing import Annotated, Union

from pydantic import Field, Tag, TypeAdapter

from .base_command_spec import BaseCommandSpec
from .cli_command_spec import CLICommandSpec
from .interactive_command_spec import InteractiveCommandSpec
from .python_callable_spec import PythonCallableSpec

__all__ = ["CommandSpecDiscriminatedUnion", "CommandSpec", "CommandSpecWithParameters"]


CommandSpecTaggedUnion = Union[
    Annotated[CLICommandSpec, Tag("cli_command")],
    Annotated[PythonCallableSpec, Tag("python_callable")],
    Annotated[InteractiveCommandSpec, Tag("interactive")],
]


CommandSpecDiscriminatedUnion = Annotated[CommandSpecTaggedUnion, Field(discriminator="implemented_as")]
command_spec_adapter: TypeAdapter[CommandSpecTaggedUnion] = TypeAdapter(CommandSpecDiscriminatedUnion)


def CommandSpec(**command_spec_json) -> CommandSpecDiscriminatedUnion:
    return command_spec_adapter.validate_python(command_spec_json)


class CommandSpecWithParameters(BaseCommandSpec):
    id: int
    application_id: int
    parameters: dict
    application: str
    version: str
    cmd_name: str
    # cif_entry_sets: list[CifEntrySetRead] = []
