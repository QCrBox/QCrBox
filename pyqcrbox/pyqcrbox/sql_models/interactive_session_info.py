from typing import Any

from pyqcrbox.msg_specs import CommandExecutionRequestNATS
from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = ["InteractiveSessionInfo"]


class InteractiveSessionInfoResponse(QCrBoxPydanticBaseModel):
    session_id: str
    client_private_inbox: str
    application_slug: str | None
    application_version: str | None
    command_name: str
    arguments: dict[str, Any]


class InteractiveSessionInfo(QCrBoxPydanticBaseModel):
    session_id: str
    client_private_inbox: str
    cmd_execution_request: CommandExecutionRequestNATS

    def to_response_model(self) -> "InteractiveSessionInfoResponse":
        return InteractiveSessionInfoResponse(
            session_id=self.session_id,
            client_private_inbox=self.client_private_inbox,
            application_slug=self.cmd_execution_request.application_slug,
            application_version=self.cmd_execution_request.application_version,
            command_name=self.cmd_execution_request.command_name,
            arguments=self.cmd_execution_request.command_arguments,
        )
