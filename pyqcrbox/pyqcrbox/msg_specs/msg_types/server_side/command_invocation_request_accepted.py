from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction

__all__ = ["CommandInvocationRequestAccepted", "PayloadForCommandInvocationRequestAccepted"]


class PayloadForCommandInvocationRequestAccepted(sql_models.CommandInvocationCreate):
    private_routing_key: str


class CommandInvocationRequestAccepted(QCrBoxBaseAction):
    action: Literal["command_invocation_request_accepted"]
    payload: PayloadForCommandInvocationRequestAccepted
