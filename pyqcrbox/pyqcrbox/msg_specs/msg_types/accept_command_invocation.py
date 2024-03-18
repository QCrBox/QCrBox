from typing import Literal

from ..base import QCrBoxBaseAction

__all__ = ["AcceptCommandInvocation", "PayloadForAcceptCommandInvocation"]

from ... import sql_models


class PayloadForAcceptCommandInvocation(sql_models.CommandInvocationCreate):
    private_routing_key: str


class AcceptCommandInvocation(QCrBoxBaseAction):
    action: Literal["accept_command_invocation"]
    payload: PayloadForAcceptCommandInvocation
