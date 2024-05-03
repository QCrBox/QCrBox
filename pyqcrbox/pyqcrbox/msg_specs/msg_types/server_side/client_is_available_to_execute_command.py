from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxBasePayload

__all__ = ["ClientIsAvailableToExecuteCommand", "PayloadForClientIsAvailableToExecuteCommand"]


class PayloadForClientIsAvailableToExecuteCommand(QCrBoxBasePayload):
    cmd_invocation_payload: sql_models.CommandInvocationCreate
    private_routing_key: str


class ClientIsAvailableToExecuteCommand(QCrBoxBaseAction):
    action: Literal["client_is_available_to_execute_command"]
    payload: PayloadForClientIsAvailableToExecuteCommand
