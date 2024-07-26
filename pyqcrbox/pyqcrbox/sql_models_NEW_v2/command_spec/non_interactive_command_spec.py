from typing import Annotated, Union

from pydantic import Field, Tag

from pyqcrbox.sql_models_NEW_v2.command_spec.cli_command_spec import CLICommandSpec
from pyqcrbox.sql_models_NEW_v2.command_spec.python_callable_spec import PythonCallableSpec

NonInteractiveCommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
    ],
    Field(discriminator="implemented_as"),
    #Field(title="name", default="foo"),
]
