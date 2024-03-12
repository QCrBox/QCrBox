import inspect
from typing import Any, Literal, Optional

from pydantic import BaseModel

from .. import sql_models
from .base import QCrBoxBaseAction, QCrBoxBaseMessage, QCrBoxGenericResponse

__all__ = ["InvalidQCrBoxAction", "RegisterApplication", "RegisterApplicationResponse", "look_up_action_class"]


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


def represents_valid_qcrbox_response(cls, include_generic_base_class: bool = False):
    return inspect.isclass(cls) and issubclass(cls, QCrBoxGenericResponse)


VALID_QCRBOX_ACTIONS_BY_NAME = {
    cls.action_name: cls for cls in locals().values() if represents_valid_qcrbox_action(cls)
}
# VALID_QCRBOX_RESPONSES_BY_NAME = {
#     cls.response_to_str: cls
#     for cls in locals().values()
#     if represents_valid_qcrbox_response(cls, include_generic_base_class=False)
# }
# VALID_QCRBOX_RESPONSES_BY_NAME["incoming_message"] = QCrBoxGenericResponse


class InvalidQCrBoxAction(Exception):
    """
    Custom exception to indicate that an action is not supported by QCrbox.
    """


def look_up_action_class(action_name: str):
    try:
        return VALID_QCRBOX_ACTIONS_BY_NAME[action_name]
    except KeyError:
        raise InvalidQCrBoxAction(f"Invalid action: {action_name!r}")
