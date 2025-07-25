from typing import Annotated

from pydantic import Field, Tag

from pyqcrbox.sql_models.command_spec.cli_command_spec import CLICommandSpec
from pyqcrbox.sql_models.command_spec.python_callable_spec import PythonCallableSpec

NonInteractiveCommandSpec = Annotated[
    Annotated[CLICommandSpec, Tag("cli_command")] | Annotated[PythonCallableSpec, Tag("python_callable")],
    Field(discriminator="implemented_as"),
]
