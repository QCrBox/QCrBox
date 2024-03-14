from typing import Literal

from pyqcrbox import sql_models

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["ExecuteCommand", "ExecuteCommandResponse"]

PayloadForExecuteCommand = sql_models.CommandInvocationCreate


class ExecuteCommand(QCrBoxBaseAction):
    action: Literal["execute_command"]
    payload: PayloadForExecuteCommand


class ExecuteCommandResponse(QCrBoxGenericResponse):
    response_to: Literal[ExecuteCommand.action_name]
    status: str
    msg: str
