from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyqcrbox.sql_models import CommandSpecCreate

from pyqcrbox.sql_models.command import ImplementedAs

from .cli_command import CLICommand
from .interactive_command import InteractiveCommand
from .python_callable import PythonCallable

__all__ = ["ExecutableCommand"]


def ExecutableCommand(cmd_spec: "CommandSpecCreate"):
    match cmd_spec.implemented_as:
        case ImplementedAs.python_callable:
            return PythonCallable.from_command_spec(cmd_spec)
        case ImplementedAs.cli:
            return CLICommand(cmd_spec)
        case ImplementedAs.interactive:
            return InteractiveCommand(cmd_spec)
        case _:
            raise ValueError(f"Invalid value for 'implemented_as': {cmd_spec.implemented_as}")
