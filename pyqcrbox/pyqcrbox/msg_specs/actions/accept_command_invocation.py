from typing import Literal, Optional

from pydantic import BaseModel

from ..base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["AcceptCommandInvocation", "AcceptCommandInvocationResponse"]


class AcceptCommandInvocation(QCrBoxBaseAction):
    class Payload(BaseModel):
        correlation_id: str
        private_routing_key: str

    action: Literal["accept_command_invocation"]
    payload: Payload


class AcceptCommandInvocationResponse(QCrBoxGenericResponse):
    class Payload(BaseModel):
        correlation_id: str

    response_to: Literal[AcceptCommandInvocation.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[Payload] = None
