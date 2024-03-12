from typing import Literal, Optional

from pydantic import BaseModel

from .. import sql_models
from .base import QCrBoxBaseAction, QCrBoxGenericResponse

__all__ = ["RegisterApplication", "RegisterApplicationResponse"]


class RegisterApplication(QCrBoxBaseAction):
    class Payload(BaseModel):
        application_config: sql_models.ApplicationCreate
        private_routing_key: str

    action: Literal["register_application"]
    payload: Payload


class RegisterApplicationResponse(QCrBoxGenericResponse):
    class Payload(BaseModel):
        application_id: int

    response_to: Literal["register_application"]
    status: str
    msg: Optional[str] = None
    payload: Optional[Payload] = None
