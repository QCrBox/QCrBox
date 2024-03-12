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


def represents_valid_qcrbox_response(cls: Any) -> bool:
    return inspect.isclass(cls) and issubclass(cls, QCrBoxGenericResponse)
