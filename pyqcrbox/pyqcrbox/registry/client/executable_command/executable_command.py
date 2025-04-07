from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyqcrbox.sql_models.command_spec.command_spec import CommandSpecDiscriminatedUnion

from pyqcrbox.sql_models.command_spec import ImplementedAs

from .cli_command import CLICommand
from .interactive_session import InteractiveSession
from .python_callable import PythonCallable

__all__ = ["ExecutableCommand"]


def ExecutableCommand(cmd_spec: "CommandSpecDiscriminatedUnion", **kwargs):
    match cmd_spec.implemented_as:
        case ImplementedAs.python_callable:
            return PythonCallable(cmd_spec)
        case ImplementedAs.cli_command:
            return CLICommand(cmd_spec)
        case ImplementedAs.interactive_session:
            return InteractiveSession(cmd_spec, **kwargs)
        case _:
            raise ValueError(f"Invalid value for 'implemented_as': {cmd_spec.implemented_as}")
