import functools
import inspect
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

from . import msg_types

__all__ = ["QCrBoxBaseAction", "QCrBoxGenericResponse"]


class QCrBoxBaseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QCrBoxActionBasePayload(BaseModel):
    pass


class QCrBoxBaseAction(QCrBoxBaseMessage):
    action: str
    payload: QCrBoxActionBasePayload

    @classmethod
    @property
    def action_name(cls) -> str:
        """
        Allows accessing the action name directly from the class (without needing a concrete instance).
        """
        return cls.model_fields["action"].annotation.__args__[0]


class QCrBoxGenericResponse(QCrBoxBaseMessage):
    response_to: str = Literal["incoming_message"]
    status: str
    msg: Optional[str] = None
    payload: Optional[BaseModel] = None

    @classmethod
    @property
    def response_to_str(cls) -> str:
        """
        Allows accessing the value of 'response_to' directly from the QCrBoxGenericResponse class
        (without needing to instantiate a concrete object).
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


@functools.lru_cache(maxsize=1)
def populate_valid_qcrbox_actions_lookup():
    """
    Populate a dictionary to allow looking up valid QCrBox actions by name.

    Note that this must happen within a helper function (rather than during
    import of this module) to avoid an error due to the 'actions' submodule
    only being partially imported. However, we're caching the result to
    avoid repeated construction of this dictionary upon each lookup.
    """
    valid_qcrbox_actions_by_name = {
        cls.action_name: cls for cls in msg_types._qcrbox_actions if represents_valid_qcrbox_action(cls)
    }
    return valid_qcrbox_actions_by_name


def look_up_action_class(action_name: str):
    VALID_QCRBOX_ACTIONS_BY_NAME = populate_valid_qcrbox_actions_lookup()
    try:
        return VALID_QCRBOX_ACTIONS_BY_NAME[action_name]
    except KeyError:
        raise InvalidQCrBoxAction(f"Invalid action: {action_name!r}")
