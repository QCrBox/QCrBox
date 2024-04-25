from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxActionBasePayload, QCrBoxBaseAction

__all__ = ["PayloadForRegisterApplication", "RegisterApplication"]


class PayloadForRegisterApplication(QCrBoxActionBasePayload):
    application_spec: sql_models.ApplicationSpecCreate
    private_routing_key: str


class RegisterApplication(QCrBoxBaseAction):
    action: Literal["register_application"]
    payload: PayloadForRegisterApplication
