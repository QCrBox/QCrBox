from datetime import datetime
from typing import Optional

import sqlalchemy
from faststream import Logger, apply_types
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, select

from pyqcrbox.settings import settings

from .cif_entry_set import CifEntrySetCreate
from .command import CommandCreate, CommandDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ApplicationCreate(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

    commands: list[CommandCreate] = []
    cif_entry_sets: list[CifEntrySetCreate] = []

    def to_sql_model(self):
        return ApplicationDB.from_pydantic_model(self)

    def save_to_db(self):
        return self.to_sql_model().save_to_db()


class ApplicationDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)
    __pydantic_model_cls__ = ApplicationCreate

    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: list[CommandDB] = Relationship(back_populates="application")
    cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))

    @classmethod
    def from_pydantic_model(cls, application):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(application, pydantic_model_cls)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandDB.from_pydantic_model(cmd) for cmd in application.commands]
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)

    @apply_types
    def save_to_db(self, logger: Logger):
        cls = self.__class__

        with settings.db.get_session() as session:
            try:
                result = session.exec(select(cls).where(cls.name == self.name and cls.version == self.version)).one()
                logger.warning(
                    f"An application was registered before with name={self.name!r}, version={self.version!r}. "
                    "Loading details from the previously stored data."
                )
                return result
            except sqlalchemy.exc.NoResultFound:
                session.add(self)
                session.commit()
                session.refresh(self)
                return self
