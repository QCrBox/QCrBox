from pyqcrbox.sql_models_NEW_v2.base import QCrBoxPydanticBaseModel

from ..server_side.invoke_command_nats import CommandInvocationRequestNATS

__all__ = ["DiscardCommandInvocationNATS", "CommandExecutionRequestNATS"]


class DiscardCommandInvocationNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CommandExecutionRequestNATS(CommandInvocationRequestNATS):
    pass
