from typing import Any

from sqlmodel import Field

from pyqcrbox import helpers

from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CommandInvocationCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: str = Field(default_factory=helpers.generate_correlation_id)

    @property
    def nats_subject(self):
        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_version)
        return f"{slug_sanitized}.{version_sanitized}"
