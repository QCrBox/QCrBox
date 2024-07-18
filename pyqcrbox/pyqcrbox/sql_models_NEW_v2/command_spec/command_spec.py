from typing import Annotated, Union

from pydantic import Field, Tag

from .cli_command_spec import CLICommandSpec
from .interactive_command_spec import InteractiveCommandSpec
from .python_callable_spec import PythonCallableSpec

__all__ = ["CommandSpec"]


CommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
        Annotated[InteractiveCommandSpec, Tag("interactive")],
    ],
    Field(discriminator="implemented_as"),
]
