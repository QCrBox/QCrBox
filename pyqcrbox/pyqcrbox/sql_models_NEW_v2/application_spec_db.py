from datetime import datetime

import sqlalchemy
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel, select

from pyqcrbox.logging import logger
from pyqcrbox.settings import settings

from .application_spec import ApplicationSpec, ApplicationSpecBase
from .calculation import CalculationDB
from .command_spec import CommandSpecDB


class ApplicationSpecDB(ApplicationSpecBase, SQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("slug", "version"),)
    __pydantic_model_cls__ = ApplicationSpec

    id: int | None = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    private_routing_key: str

    commands: list[CommandSpecDB] = Relationship(back_populates="application")
    calculations: list[CalculationDB] = Relationship(back_populates="application")

    def model_dump(self, as_response_model=False, **kwargs):
        if as_response_model:
            assert "exclude" not in kwargs
            kwargs["exclude"] = {"private_routing_key"}

        data = super().model_dump(**kwargs)
        data["commands"] = [cmd.model_dump(as_response_model=as_response_model) for cmd in self.commands]
        return data

    @classmethod
    def from_pydantic_model(cls, application: __pydantic_model_cls__, private_routing_key: str = None):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(application, pydantic_model_cls)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandSpecDB.from_pydantic_model(cmd) for cmd in application.commands]
        data["private_routing_key"] = private_routing_key or "super-secret-private-routing-key-001"
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)

    def save_to_db(self, init_db: bool = False):
        cls = self.__class__

        with settings.db.get_session(init_db=init_db) as session:
            try:
                result = session.exec(select(cls).where(cls.slug == self.slug, cls.version == self.version)).one()
                logger.debug(
                    f"An application was registered before with slug={self.slug!r}, version={self.version!r}. "
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

    def to_response_model(self):
        from .application_spec import ApplicationSpecWithCommands

        return ApplicationSpecWithCommands(**self.model_dump(as_response_model=True))
