from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

import sqlalchemy
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, select

from pyqcrbox import logger, sql_models
from pyqcrbox.settings import settings

from .command import CommandSpecDB
from .qcrbox_base_models import QCrBoxBaseSQLModel

if TYPE_CHECKING:
    from .application import ApplicationSpecDB
    from .command_invocation import CommandInvocationDB


class CalculationStatusEnum(StrEnum):
    RECEIVED = "received"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CalculationDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "calculation"
    __table_args__ = (UniqueConstraint("correlation_id"),)

    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any] = Field(sa_column=Column(JSON))
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: CalculationStatusEnum = CalculationStatusEnum.RECEIVED

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: Optional["ApplicationSpecDB"] = Relationship(back_populates="calculations")

    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: Optional["CommandSpecDB"] = Relationship(back_populates="calculations")

    command_invocation_id: Optional[int] = Field(default=None, foreign_key="command_invocation.id")
    command_invocation: Optional["CommandInvocationDB"] = Relationship(
        sa_relationship_kwargs={"uselist": False},
        back_populates="calculation",
    )

    def save_to_db(self):
        with settings.db.get_session() as session:
            session.add(self)

            try:
                application = session.exec(
                    select(sql_models.ApplicationSpecDB).where(
                        sql_models.ApplicationSpecDB.slug == self.application_slug,
                        sql_models.ApplicationSpecDB.version == self.application_version,
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
                        select(CommandSpecDB).where(
                            CommandSpecDB.application == self.application,
                            CommandSpecDB.name == self.command_name,
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
