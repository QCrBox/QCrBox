from typing import Any

from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CommandExecutionCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: str
    private_routing_key: str
