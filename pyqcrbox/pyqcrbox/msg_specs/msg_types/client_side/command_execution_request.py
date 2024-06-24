from pyqcrbox.sql_models.qcrbox_base_models import QCrBoxPydanticBaseModel

from ..server_side.invoke_command_nats import CommandInvocationRequestNATS

__all__ = ["DiscardCommandInvocationNATS", "CommandExecutionRequestNATS"]


class DiscardCommandInvocationNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CommandExecutionRequestNATS(CommandInvocationRequestNATS):
    pass
