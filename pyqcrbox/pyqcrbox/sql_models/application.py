from datetime import datetime
from typing import Optional

import sqlalchemy
from faststream import Logger, apply_types
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, select

from pyqcrbox.settings import settings

from .cif_entry_set import CifEntrySetCreate
from .command import CommandCreate, CommandDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ApplicationSpecCreate(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

    commands: list[CommandCreate] = []
    cif_entry_sets: list[CifEntrySetCreate] = []

    @property
    def routing_key_command_invocation(self):
        return f"qcrbox_rk_{self.slug}_{self.version}"

    def to_sql_model(self, private_routing_key: str = None):
        return ApplicationSpecDB.from_pydantic_model(self, private_routing_key=private_routing_key)

    def save_to_db(self, private_routing_key: str = None):
        return self.to_sql_model(private_routing_key=private_routing_key).save_to_db()


class ApplicationSpecDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)
    __pydantic_model_cls__ = ApplicationSpecCreate

    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    private_routing_key: str
    routing_key_command_invocation: str

    commands: list[CommandDB] = Relationship(back_populates="application")
    command_invocations: list["CommandInvocationDB"] = Relationship(back_populates="application")
    cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))

    @classmethod
    def from_pydantic_model(cls, application, private_routing_key: str = None):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(application, pydantic_model_cls)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandDB.from_pydantic_model(cmd) for cmd in application.commands]
        data["private_routing_key"] = private_routing_key or "super-secret-private-routing-key-001"
        data["routing_key_command_invocation"] = application.routing_key_command_invocation
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
