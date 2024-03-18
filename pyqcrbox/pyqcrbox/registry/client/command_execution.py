from pyqcrbox.sql_models.command import CommandSpecCreate, CommandSpecDB, ImplementedAs

from .external_command import ExternalCommand

__all__ = ["instantiate_command"]


def instantiate_command(cmd_spec: CommandSpecCreate | CommandSpecDB):
    if cmd_spec.implemented_as == ImplementedAs.cli:
        return ExternalCommand(cmd_spec.call_pattern)
    else:
        raise NotImplementedError(f"Cannot instantiate non-CLI commands. (Got: {cmd_spec.implemented_as.value})")
