from typing import Any

from pyqcrbox import helpers

__all__ = ["InvokeCommandNATS", "CommandInvocationRequestNATS"]

from pyqcrbox.sql_models import QCrBoxPydanticBaseModel


class InvokeCommandNATS(QCrBoxPydanticBaseModel):
    application_slug: str | None
    application_version: str | None
    command_name: str
    arguments: dict[str, Any]

    @property
    def nats_subject_parts(self):
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_version)
        return f"{slug_sanitized}.{version_sanitized}"


class CommandInvocationRequestNATS(InvokeCommandNATS):
    calculation_id: str
