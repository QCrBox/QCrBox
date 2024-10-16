from typing import Literal

from .base_command_spec import BaseCommandSpec
from .call_pattern import CallPattern

__all__ = ["CLICommandSpec"]


class CLICommandSpec(BaseCommandSpec):
    implemented_as: Literal["cli_command"] = "cli_command"
    call_pattern: CallPattern
