from typing import Annotated, Union

from pydantic import Field, Tag

from .cli_command_spec import CLICommandSpec
from .python_callable_spec import PythonCallableSpec

__all__ = ["CommandSpec"]


NonInteractiveCommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
    ],
    Field(discriminator="implemented_as"),
    Field(title="name", default="foo"),
]


CommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
        # Annotated[InteractiveCommandSpec, Tag("interactive")],
    ],
    Field(discriminator="implemented_as"),
]
