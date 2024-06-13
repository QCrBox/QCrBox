from typing import Any, Self

import sqlalchemy
from pydantic import model_validator
from sqlmodel import Field, select

from pyqcrbox import logger, settings
from pyqcrbox.helpers import generate_correlation_id

from .application import ApplicationSpecDB
from .command import CommandSpecDB
from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CommandInvocationCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: str = Field(default_factory=generate_correlation_id)

    @model_validator(mode="after")
    def check_command_exists(self) -> Self:
        with settings.db.get_session() as session:
            try:
                self._command_db = session.exec(
                    select(CommandSpecDB)
                    .join(ApplicationSpecDB)
                    .where(
                        ApplicationSpecDB.slug == self.application_slug,
                        ApplicationSpecDB.version == self.application_version,
                        CommandSpecDB.name == self.command_name,
                    )
                ).one()
            except sqlalchemy.exc.NoResultFound:
                error_msg = (
                    f"Command not registered: {self.command_name} "
                    f"(application: {self.application_slug!r}, "
                    f"version: {self.application_version!r})"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        return self
