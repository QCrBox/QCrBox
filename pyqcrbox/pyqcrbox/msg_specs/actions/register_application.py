from typing import Literal

from pyqcrbox import sql_models

from ..base import QCrBoxActionBasePayload, QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["RegisterApplication", "RegisterApplicationResponse"]


class RegisterApplicationPayload(QCrBoxActionBasePayload):
    application_spec: sql_models.ApplicationSpecCreate
    private_routing_key: str


class RegisterApplication(QCrBoxBaseAction):
    action: Literal["register_application"]
    payload: RegisterApplicationPayload

    Payload = RegisterApplicationPayload  # convenience alias


class RegisterApplicationResponse(QCrBoxGenericResponse):
    response_to: Literal[RegisterApplication.action_name]
    status: str
    msg: str