from typing import Literal

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.msg_specs.base import QCrBoxBaseAction

__all__ = ["CommandInvocationRequest", "PayloadForCommandInvocationRequest"]


PayloadForCommandInvocationRequest = sql_models_NEW_v2.CommandInvocationCreate


class CommandInvocationRequest(QCrBoxBaseAction):
    action: Literal["command_invocation_request"] = "command_invocation_request"
    payload: PayloadForCommandInvocationRequest
