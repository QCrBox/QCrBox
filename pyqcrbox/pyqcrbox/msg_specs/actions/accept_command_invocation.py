from typing import Literal, Optional

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["AcceptCommandInvocation", "AcceptCommandInvocationResponse", "PayloadForAcceptCommandInvocation"]

from ... import sql_models


class PayloadForAcceptCommandInvocation(sql_models.CommandInvocationCreate):
    private_routing_key: str


class AcceptCommandInvocation(QCrBoxBaseAction):
    action: Literal["accept_command_invocation"]
    payload: PayloadForAcceptCommandInvocation


class AcceptCommandInvocationResponse(QCrBoxGenericResponse):
    response_to: Literal[AcceptCommandInvocation.action_name]
    status: str
    msg: Optional[str] = None
    payload: AcceptCommandInvocation.Payload
