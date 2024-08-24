from typing import Literal

from pyqcrbox import sql_models_NEW_v2

from ..base import QCrBoxBaseAction

__all__ = ["InitiateCommandExecution", "PayloadForInitiateCommandExecution"]

PayloadForInitiateCommandExecution = sql_models_NEW_v2.CommandExecutionCreate


class InitiateCommandExecution(QCrBoxBaseAction):
    action: Literal["initiate_command_execution"] = "initiate_command_execution"
    payload: PayloadForInitiateCommandExecution
