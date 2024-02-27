import inspect
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

__all__ = ["QCrBoxBaseAction", "QCrBoxGenericResponse"]


class QCrBoxBaseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QCrBoxBaseAction(QCrBoxBaseMessage):
    action: str
    payload: BaseModel


class QCrBoxGenericResponse(QCrBoxBaseMessage):
    response_to: str
    status: str
    msg: Optional[str] = None
    payload: Optional[dict[Any, Any]] = None


def represents_valid_qcrbox_response(cls: Any) -> bool:
    return inspect.isclass(cls) and issubclass(cls, QCrBoxGenericResponse)
