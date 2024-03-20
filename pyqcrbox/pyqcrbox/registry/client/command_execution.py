from pyqcrbox.sql_models import ApplicationSpecCreate
from pyqcrbox.sql_models.command import ImplementedAs

from .external_command import ExternalCommand

__all__ = ["instantiate_command_from_spec"]


def instantiate_command_from_spec(app_spec: ApplicationSpecCreate, command_name: str):
    cmd_spec = app_spec.get_command_spec(command_name)
    if cmd_spec.implemented_as == ImplementedAs.cli:
        return ExternalCommand(cmd_spec.call_pattern)
    else:
        raise NotImplementedError(f"Cannot instantiate non-CLI commands. (Got: {cmd_spec.implemented_as.value})")
