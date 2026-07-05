from typing import Any

from pyqcrbox import helpers

__all__ = ["InvokeCommandNATS", "CommandInvocationRequestNATS"]

from pyqcrbox.sql_models import QCrBoxPydanticBaseModel


class InvokeCommandNATS(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    command_arguments: dict[str, Any]
    # Private inbox of the container instance this invocation is bound to
    # (per-user container binding); None dispatches via the shared broadcast
    # subject (first available container wins).
    target_private_inbox: str | None = None

    @property
    def nats_subject_parts(self):
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_version)
        return f"{slug_sanitized}.{version_sanitized}"

    @property
    def invocation_request_subject(self) -> str:
        """The subject to send the invocation request to: targeted or broadcast."""
        if self.target_private_inbox:
            return f"{self.target_private_inbox}.cmd.handle_invocation_request"
        return f"client.cmd.handle_invocation_request.{self.nats_subject_parts}"


class CommandInvocationRequestNATS(InvokeCommandNATS):
    calculation_id: str
