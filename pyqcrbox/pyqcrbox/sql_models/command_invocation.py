from datetime import datetime
from typing import Any, Optional

import sqlalchemy
from faststream import Logger, apply_types
from pydantic import field_validator
from sqlmodel import JSON, Column, Field, Relationship, select

from pyqcrbox.helpers import generate_correlation_id
from pyqcrbox.settings import settings

from .application import ApplicationSpecDB
from .command import CommandDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class CommandInvocationCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: Optional[str] = None

    @field_validator("correlation_id")
    @classmethod
    def create_random_correlation_id_if_not_explicitly_provided(cls, value: Optional[str]) -> str:
        if value is not None:
            return value
        else:
            return generate_correlation_id()

    def to_sql_model(self):
        return CommandInvocationDB.from_pydantic_model(self)

    def save_to_db(self):
        return self.to_sql_model().save_to_db()


class CommandInvocationDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command_invocation"
    __pydantic_model_cls__ = CommandInvocationCreate

    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any] = Field(sa_column=Column(JSON))
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: Optional["ApplicationSpecDB"] = Relationship(back_populates="command_invocations")
    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: Optional["CommandDB"] = Relationship(back_populates="command_invocations")

    @classmethod
    def from_pydantic_model(cls, model):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(model, pydantic_model_cls)
        data = model.model_dump()
        return cls(**data)

    @apply_types
    def save_to_db(self, logger: Logger):
        # cls = self.__class__

        with settings.db.get_session() as session:
            session.add(self)

            try:
                application = session.exec(
                    select(ApplicationSpecDB).where(
                        ApplicationSpecDB.slug == self.application_slug,
                        ApplicationSpecDB.version == self.application_version,
                    )
                ).one()
                self.application = application
                logger.debug(f"Found application: {self.application_slug!r}, version: {self.application_version!r}")
            except sqlalchemy.exc.NoResultFound:
                self.application = None
                logger.debug(
                    f"Warning: could not find application {self.application_slug!r}, "
                    f"version: {self.application_version!r}."
                )

            if self.application is not None:
                try:
                    command = session.exec(
                        select(CommandDB).where(
                            CommandDB.application == self.application,
                            CommandDB.name == self.command_name,
                        )
                    ).one()
                    self.command = command
                    logger.debug(f"Found command: {self.command_name!r}")
                except sqlalchemy.exc.NoResultFound:
                    self.command = None
                    logger.debug(f"Warning: could not find command {self.command_name!r}.")

            session.commit()
            session.refresh(self)
            return self
