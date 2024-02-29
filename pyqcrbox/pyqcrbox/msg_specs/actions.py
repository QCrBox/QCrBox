import inspect
from typing import Any, Literal

from pydantic import BaseModel

from .. import sql_models
from .base import QCrBoxBaseAction

__all__ = ["VALID_QCRBOX_ACTIONS", "RegisterApplication"]


class RegisterApplication(QCrBoxBaseAction):
    class Payload(BaseModel):
        application_config: sql_models.ApplicationSpec
        routing_key__registry_to_application: str

    action: Literal["register_application"]
    payload: Payload


def represents_valid_qcrbox_action(cls: Any) -> bool:
    return inspect.isclass(cls) and issubclass(cls, QCrBoxBaseAction) and cls is not QCrBoxBaseAction


VALID_QCRBOX_ACTIONS = [cls for cls in locals().values() if represents_valid_qcrbox_action(cls)]
