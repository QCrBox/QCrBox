from typing import Literal

from pyqcrbox import sql_models
from pyqcrbox.msg_specs.base import QCrBoxBaseAction

__all__ = ["CommandInvocationRequest", "PayloadForCommandInvocationRequest"]


PayloadForCommandInvocationRequest = sql_models.CommandInvocationCreate


class CommandInvocationRequest(QCrBoxBaseAction):
    action: Literal["command_invocation_request"]
    payload: PayloadForCommandInvocationRequest
