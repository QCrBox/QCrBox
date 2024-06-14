from typing import Any

from sqlmodel import Field

from pyqcrbox.helpers import generate_correlation_id

from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CommandInvocationCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: str = Field(default_factory=generate_correlation_id)
