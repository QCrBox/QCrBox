from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox import sql_models

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["ExecuteCommand", "ExecuteCommandResponse"]


class ExecuteCommand(QCrBoxBaseAction):
    action: Literal["execute_command"]
    payload: sql_models.CommandInvocationCreate


class ExecuteCommandResponse(QCrBoxGenericResponse):
    class Payload(BaseModel):
        pass

    response_to: Literal[ExecuteCommand.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[Payload] = None
