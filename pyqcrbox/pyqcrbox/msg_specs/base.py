import inspect
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

__all__ = ["QCrBoxBaseAction", "QCrBoxGenericResponse"]


class QCrBoxBaseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QCrBoxBaseAction(QCrBoxBaseMessage):
    action: str
    payload: BaseModel

    @classmethod
    @property
    def action_name(cls):
        """
        Allows accessing the action name directly from the class (without needing a concrete instance).
        """
        return cls.model_fields["action"].annotation.__args__[0]


class QCrBoxGenericResponse(QCrBoxBaseMessage):
    response_to: str = Literal["incoming_message"]
    status: str
    msg: Optional[str] = None
    payload: Optional[dict[Any, Any]] = None

    @classmethod
    @property
    def response_to_str(cls):
        """
        Allows accessing the value of 'response_to' directly from the class (without needing a concrete instance).
        """
        return cls.model_fields["response_to"].annotation.__args__[0]


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
