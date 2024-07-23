from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["ExecuteCommand", "ExecuteCommandResponse", "PayloadForExecuteCommand", "PayloadForExecuteCommandResponse"]


PayloadForExecuteCommand = sql_models_NEW_v2.CommandExecutionCreate


class ExecuteCommand(QCrBoxBaseAction):
    action: Literal["execute_command"] = "execute_command"
    payload: PayloadForExecuteCommand


class PayloadForExecuteCommandResponse(BaseModel):
    correlation_id: str


class ExecuteCommandResponse(QCrBoxGenericResponse):
    response_to: Literal[ExecuteCommand.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[PayloadForExecuteCommandResponse] = None
