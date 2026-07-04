from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxBasePayload

__all__ = ["PayloadForRegisterApplication", "RegisterApplication"]


class PayloadForRegisterApplication(QCrBoxBasePayload):
    application_spec: sql_models.ApplicationSpec
    private_routing_key: str
    client_id: str = "anonymous_client"
    private_inbox: str | None = None


# class PayloadForRegisterApplicationResponse(QCrBoxBasePayload):
#     application_id: sql_models.ApplicationSpecDB.__annotations__["id"]


class RegisterApplication(QCrBoxBaseAction):
    action: Literal["register_application"] = "register_application"
    payload: PayloadForRegisterApplication
