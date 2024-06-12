from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import sqlalchemy
from pydantic import computed_field
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, desc, select

from pyqcrbox import logger, sql_models
from pyqcrbox.settings import settings

from .calculation_status_event import CalculationStatusEnum, CalculationStatusEventDB
from .command import CommandSpecDB
from .qcrbox_base_models import QCrBoxBaseSQLModel

if TYPE_CHECKING:
    from .application import ApplicationSpecDB
    from .command_invocation import CommandInvocationDB


class CalculationDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "calculation"
    __table_args__ = (UniqueConstraint("correlation_id"),)

    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any] = Field(sa_column=Column(JSON))
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    status_events: list[CalculationStatusEventDB] = Relationship(back_populates="calculation")

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

    @computed_field
    @property
    def status(self) -> CalculationStatusEnum:
        with settings.db.get_session() as session:
            event = self._get_latest_or_create_initial_status_event(session)
        return event.status

    def get_status_events(self) -> list[CalculationStatusEventDB]:
        with settings.db.get_session() as session:
            events = session.exec(select(CalculationStatusEventDB).order_by(CalculationStatusEventDB.timestamp)).all()
        return events

    def get_status_values(self) -> list[CalculationStatusEnum]:
        return [e.status for e in self.get_status_events()]

    def _get_latest_or_create_initial_status_event(self, session):
        latest_status_event = session.exec(
            select(CalculationStatusEventDB).order_by(desc(CalculationStatusEventDB.timestamp))
        ).first()

        if latest_status_event is None:
            session.add(self)
            session.commit()
            session.refresh(self)

            initial_status_event = CalculationStatusEventDB(
                calculation_id=self.id,
                status=CalculationStatusEnum.RECEIVED,
            )
            session.add(initial_status_event)
            session.commit()
            session.refresh(initial_status_event)

            latest_status_event = initial_status_event

        return latest_status_event

    def update_status(self, new_status: CalculationStatusEnum | str, comment: str = ""):
        logger.debug(f"Creating new status event for calculation {self.id}")
        new_status = CalculationStatusEnum(new_status)

        with settings.db.get_session() as session:
            status_event = CalculationStatusEventDB(calculation_id=self.id, status=new_status, comment=comment)
            session.add(status_event)
            session.commit()

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

            _ = self._get_latest_or_create_initial_status_event(session)

            session.commit()
            session.refresh(self)
            return self
