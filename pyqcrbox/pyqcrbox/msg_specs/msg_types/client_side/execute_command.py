from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction

__all__ = ["ExecuteCommand", "PayloadForExecuteCommand"]


PayloadForExecuteCommand = sql_models.CommandExecutionCreate


class ExecuteCommand(QCrBoxBaseAction):
    action: Literal["execute_command"]
    payload: PayloadForExecuteCommand
