import inspect
from typing import Any, Literal, Optional

from pydantic import BaseModel

from .. import sql_models
from .base import QCrBoxBaseAction, QCrBoxBaseMessage, QCrBoxGenericResponse

__all__ = ["VALID_QCRBOX_ACTIONS", "RegisterApplication", "RegisterApplicationResponse"]


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


def represents_valid_qcrbox_message(cls):
    return (
        inspect.isclass(cls) and issubclass(cls, QCrBoxBaseMessage) and cls not in (QCrBoxBaseMessage, QCrBoxBaseAction)
    )


def represents_valid_qcrbox_action(cls: Any) -> bool:
    return inspect.isclass(cls) and issubclass(cls, QCrBoxBaseAction) and cls is not QCrBoxBaseAction


def represents_valid_qcrbox_response(cls):
    return inspect.isclass(cls) and issubclass(cls, QCrBoxGenericResponse)


# Generate a list of all classes representing valid QCrBox action messages
VALID_QCRBOX_MESSAGES = [cls for cls in locals().values() if represents_valid_qcrbox_message(cls)]
VALID_QCRBOX_ACTIONS = [cls for cls in locals().values() if represents_valid_qcrbox_action(cls)]
VALID_QCRBOX_RESPONSES = [cls for cls in locals().values() if represents_valid_qcrbox_response(cls)]

# Ensure that QCrBoxGenericResponse comes last because it is the last fallback
# after trying the more specific message types.
VALID_QCRBOX_MESSAGES.remove(QCrBoxGenericResponse)
VALID_QCRBOX_MESSAGES += [QCrBoxGenericResponse]
VALID_QCRBOX_RESPONSES.remove(QCrBoxGenericResponse)
VALID_QCRBOX_RESPONSES += [QCrBoxGenericResponse]
