from datetime import datetime
from pathlib import Path
from typing import Optional

import sqlalchemy
import yaml
from litestar.contrib.pydantic import PydanticDTO
from litestar.dto import DTOConfig
from pydantic import field_validator
from sqlmodel import Field, Relationship, UniqueConstraint, select

from pyqcrbox import logger
from pyqcrbox.settings import settings

from .. import helpers
from .cif_entry_set import CifEntrySetCreate
from .command import CommandSpecCreate, CommandSpecDB, CommandSpecWithParameters
from .command_invocation import CommandInvocationDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ApplicationSpecBase(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class ApplicationSpecCreate(ApplicationSpecBase):
    commands: list[CommandSpecCreate] = []
    cif_entry_sets: list[CifEntrySetCreate] = []

    @field_validator("commands")
    @classmethod
    def validate_command_names_are_unique(cls, value: list[CommandSpecCreate]) -> list[CommandSpecCreate]:
        command_names = [c.name for c in value]
        if len(command_names) != len(set(command_names)):
            raise ValueError("Command names must be unique")
        return value

    @classmethod
    def from_yaml_file(cls, path: str | Path):
        return cls(**yaml.safe_load(Path(path).open()))

    @property
    def routing_key_command_invocation(self):
        return helpers.get_routing_key_for_command_invocation_requests(
            application_slug=self.slug,
            application_version=self.version,
        )

    def get_command_spec(self, command_name: str) -> CommandSpecCreate:
        cmds = [c for c in self.commands if c.name == command_name]
        if len(cmds) == 0:
            raise ValueError(f"Invalid command name: {command_name}")
        elif len(cmds) == 1:
            return cmds[0]
        else:
            raise RuntimeError(
                f"Found multiple definitions for command {command_name!r}. This branch should never be reached."
            )

    def to_sql_model(self, private_routing_key: str = None):
        return ApplicationSpecDB.from_pydantic_model(self, private_routing_key=private_routing_key)

    def save_to_db(self, private_routing_key: str = None):
        sql_model = self.to_sql_model(private_routing_key=private_routing_key)
        return sql_model.save_to_db()


class ApplicationSpecDB(ApplicationSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)
    __pydantic_model_cls__ = ApplicationSpecCreate

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    private_routing_key: str
    routing_key_command_invocation: str

    commands: list[CommandSpecDB] = Relationship(back_populates="application")
    command_invocations: list[CommandInvocationDB] = Relationship(back_populates="application")
    # cif_entry_sets: list[str] = Field(sa_column=Column(JSON()))

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data["commands"] = [cmd.model_dump(**kwargs) for cmd in self.commands]
        return data

    @classmethod
    def from_pydantic_model(cls, application: __pydantic_model_cls__, private_routing_key: str = None):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(application, pydantic_model_cls)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandSpecDB.from_pydantic_model(cmd) for cmd in application.commands]
        data["private_routing_key"] = private_routing_key or "super-secret-private-routing-key-001"
        data["routing_key_command_invocation"] = application.routing_key_command_invocation
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)

    def save_to_db(self):
        cls = self.__class__

        with settings.db.get_session() as session:
            try:
                result = session.exec(select(cls).where(cls.name == self.name and cls.version == self.version)).one()
                logger.debug(
                    f"An application was registered before with name={self.name!r}, version={self.version!r}. "
                    "Loading details from the previously stored data."
                )
                logger.debug(
                    "TODO: check that the commands specified in this application spec "
                    "are consistent with the previously stored ones!"
                )
                return result
            except sqlalchemy.exc.NoResultFound:
                session.add(self)
                session.commit()
                session.refresh(self)
                return self

    def to_read_model(self):
        return ApplicationSpecWithCommands(**self.model_dump())


class ApplicationSpecWithCommands(ApplicationSpecBase):
    commands: list[CommandSpecWithParameters]
    # cif_entry_sets: list[CifEntrySetRead] = []


class ApplicationReadDTO(PydanticDTO[ApplicationSpecDB]):
    config = DTOConfig(exclude={"private_routing_key", "cif_entry_sets"})
