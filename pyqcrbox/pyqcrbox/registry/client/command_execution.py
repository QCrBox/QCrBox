from pyqcrbox.sql_models import CommandSpecCreate
from pyqcrbox.sql_models.command import ImplementedAs

from .external_command import ExternalCommand
from .python_callable import PythonCallable

__all__ = ["instantiate_command_from_spec"]


def instantiate_command_from_spec(cmd_spec: CommandSpecCreate):
    if cmd_spec.implemented_as == ImplementedAs.cli:
        return ExternalCommand(cmd_spec.call_pattern)
    if cmd_spec.implemented_as == ImplementedAs.python_callable:
        return PythonCallable.from_command_spec(cmd_spec)
    else:
        raise NotImplementedError(f"Cannot instantiate non-CLI commands. (Got: {cmd_spec.implemented_as.value})")
