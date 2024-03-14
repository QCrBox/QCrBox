from typing import Literal

from pyqcrbox import sql_models

from ..base import QCrBoxBaseAction

__all__ = ["InitiateCommandExecution", "PayloadForInitiateCommandExecution"]

PayloadForInitiateCommandExecution = sql_models.CommandExecutionCreate


class InitiateCommandExecution(QCrBoxBaseAction):
    action: Literal["initiate_command_execution"]
    payload: PayloadForInitiateCommandExecution
