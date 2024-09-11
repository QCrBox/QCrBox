from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["InvokeCommand", "InvokeCommandResponse", "PayloadForInvokeCommand", "PayloadForInvokeCommandResponse"]


PayloadForInvokeCommand = sql_models.CommandInvocationCreate


class InvokeCommand(QCrBoxBaseAction):
    action: Literal["invoke_command"] = "invoke_command"
    payload: PayloadForInvokeCommand


class PayloadForInvokeCommandResponse(BaseModel):
    correlation_id: str


class InvokeCommandResponse(QCrBoxGenericResponse):
    response_to: Literal[InvokeCommand.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[PayloadForInvokeCommandResponse] = None
