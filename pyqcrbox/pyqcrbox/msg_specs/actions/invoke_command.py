from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox import sql_models

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["InvokeCommand", "InvokeCommandResponse"]


class InvokeCommand(QCrBoxBaseAction):
    action: Literal["invoke_command"]
    payload: sql_models.CommandInvocationCreate


class InvokeCommandResponse(QCrBoxGenericResponse):
    class Payload(BaseModel):
        application_id: int

    response_to: Literal[InvokeCommand.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[Payload] = None
