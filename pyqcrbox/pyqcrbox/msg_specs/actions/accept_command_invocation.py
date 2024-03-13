from typing import Literal, Optional

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["AcceptCommandInvocation", "AcceptCommandInvocationResponse"]

from ... import sql_models


class AcceptCommandInvocation(QCrBoxBaseAction):
    class AcceptCommandInvocationPayload(sql_models.CommandInvocationCreate):
        private_routing_key: str

    Payload = AcceptCommandInvocationPayload

    action: Literal["accept_command_invocation"]
    payload: AcceptCommandInvocationPayload


class AcceptCommandInvocationResponse(QCrBoxGenericResponse):
    response_to: Literal[AcceptCommandInvocation.action_name]
    status: str
    msg: Optional[str] = None
    payload: AcceptCommandInvocation.Payload
