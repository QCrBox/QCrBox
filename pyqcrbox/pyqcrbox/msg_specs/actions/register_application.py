from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox import sql_models

from ..base import QCrBoxActionBasePayload, QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["RegisterApplication", "RegisterApplicationResponse"]


class RegisterApplicationPayload(QCrBoxActionBasePayload):
    application_spec: sql_models.ApplicationCreate
    private_routing_key: str


class RegisterApplication(QCrBoxBaseAction):
    action: Literal["register_application"]
    payload: RegisterApplicationPayload

    Payload = RegisterApplicationPayload  # convenience alias


class RegisterApplicationResponse(QCrBoxGenericResponse):
    class Payload(BaseModel):
        application_id: int

    response_to: Literal[RegisterApplication.action_name]
    status: str
    msg: Optional[str] = None
    payload: Optional[Payload] = None
