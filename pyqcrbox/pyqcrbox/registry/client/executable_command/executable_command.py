from typing import TYPE_CHECKING

from click import BaseCommand

from pyqcrbox.sql_models.command_spec import ImplementedAs

from .cli_command import CLICommand
from .interactive_session import InteractiveSession
from .python_callable import PythonCallable

if TYPE_CHECKING:
    from pyqcrbox.sql_models.command_spec.command_spec import CommandSpecDiscriminatedUnion

__all__ = ["ExecutableCommand"]


def ExecutableCommand(cmd_spec: "CommandSpecDiscriminatedUnion", **kwargs) -> BaseCommand:
    """Instantiate a command implementation from a command specification.

    Parameters
    ----------
    cmd_spec : CommandSpecDiscriminatedUnion
        The command specification describing how the command should be implemented.
    **kwargs
        Additional keyword arguments passed to the command constructor.

    Returns
    -------
    BaseCommand
        An instance of the appropriate command class based on the implementation type.

    Raises
    ------
    ValueError
        If the 'implemented_as' attribute of cmd_spec is not recognized.

    """
    match cmd_spec.implemented_as:
        case ImplementedAs.python_callable:
            return PythonCallable(cmd_spec)
        case ImplementedAs.cli_command:
            return CLICommand(cmd_spec)
        case ImplementedAs.interactive_session:
            return InteractiveSession(cmd_spec, **kwargs)
        case _:
            raise ValueError(f"Invalid value for 'implemented_as': {cmd_spec.implemented_as}")
