from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Self

import sqlalchemy
from pydantic import computed_field, model_validator
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, desc, select

from pyqcrbox import logger, sql_models
from pyqcrbox.settings import settings

from .calculation_status_event import CalculationStatusEnum, CalculationStatusEventDB

# from .command import CommandSpecDB
from .qcrbox_base_models import QCrBoxBaseSQLModel

if TYPE_CHECKING:
    from .application import ApplicationSpecDB


class CalculationBase(QCrBoxBaseSQLModel):
    calculation_id: str
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any] = Field(sa_column=Column(JSON))


class CalculationResponseModel(CalculationBase):
    id: int
    status: str


class CalculationDB(CalculationBase, table=True):
    __tablename__ = "calculation"
    __table_args__ = (UniqueConstraint("calculation_id"),)

    timestamp: datetime = Field(default_factory=datetime.now)
    status_events: list[CalculationStatusEventDB] = Relationship(back_populates="calculation")
    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: Optional["ApplicationSpecDB"] = Relationship(back_populates="calculations")

    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: Optional["CommandSpecDB"] = Relationship(back_populates="calculations")

    @model_validator(mode="after")
    def check_command_exists(self) -> Self:
        with settings.db.get_session() as session:
            try:
                _ = session.exec(
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
                    f"Command not found: {self.command_name} "
                    f"(application: {self.application_slug!r}, "
                    f"version: {self.application_version!r})"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        return self

    @computed_field
    @property
    def status(self) -> CalculationStatusEnum:
        with settings.db.get_session() as session:
            # event = self._get_latest_status_event(session)
            event = self._get_latest_status_event(session, create_if_not_exists=False)
            if event:
                status = event.status
            else:
                logger.warning(f"Unknown calculation status: {self.calculation_id!r}")
                status = CalculationStatusEnum.UNKNOWN
        return status

    def get_status_events(self) -> list[CalculationStatusEventDB]:
        with settings.db.get_session() as session:
            events = session.exec(select(CalculationStatusEventDB).order_by(CalculationStatusEventDB.timestamp)).all()
        return events

    def get_status_values(self) -> list[CalculationStatusEnum]:
        return [e.status for e in self.get_status_events()]

    def _get_latest_status_event(self, session, create_if_not_exists: bool = False):
        latest_status_event = session.exec(
            select(CalculationStatusEventDB)
            .where(CalculationStatusEventDB.calculation_id == self.id)
            .order_by(desc(CalculationStatusEventDB.timestamp))
        ).first()

        if latest_status_event is None and create_if_not_exists:
            session.add(self)
            session.commit()
            session.refresh(self)

            initial_status_event = CalculationStatusEventDB(
                calculation_id=self.id,
                status=CalculationStatusEnum.SUBMITTED,
            )
            session.add(initial_status_event)
            session.commit()
            session.refresh(initial_status_event)

            latest_status_event = initial_status_event

        return latest_status_event

    def update_status(self, new_status: CalculationStatusEnum | str, comment: str = ""):
        logger.debug(f"Creating new status event for calculation {self.calculation_id}")
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

            # _ = self._get_latest_status_event(session)

            session.commit()
            session.refresh(self)
            return self

    def to_response_model(self) -> CalculationResponseModel:
        return CalculationResponseModel(**self.model_dump())
