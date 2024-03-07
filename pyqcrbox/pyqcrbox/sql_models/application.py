from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint

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
        with settings.db.get_session() as session:
            application_db = self.to_sql_model()
            session.add(application_db)
            session.commit()
            session.refresh(application_db)
            return application_db


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
