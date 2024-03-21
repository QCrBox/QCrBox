from datetime import datetime
from typing import Any, Optional

from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint, select

from pyqcrbox.settings import settings

from .command_invocation import CommandInvocationDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class CommandExecutionCreate(QCrBoxPydanticBaseModel):
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    correlation_id: str
    private_routing_key: str

    def to_sql_model(self):
        return CommandExecutionDB.from_pydantic_model(self)

    def save_to_db(self):
        return self.to_sql_model().save_to_db()


class CommandExecutionDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command_execution"
    __table_args__ = (UniqueConstraint("correlation_id"),)
    __pydantic_model_cls__ = CommandExecutionCreate

    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any] = Field(sa_column=Column(JSON))
    correlation_id: str
    private_routing_key: str

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)

    command_invocation: Optional["CommandInvocationDB"] = Relationship(
        sa_relationship_kwargs={"uselist": False},
        back_populates="command_execution",
    )

    @classmethod
    def from_pydantic_model(cls, model) -> "CommandExecutionDB":
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(model, pydantic_model_cls)
        data = model.model_dump(exclude={"command_spec_db"})
        return cls(**data)

    def save_to_db(self) -> "CommandExecutionDB":
        with settings.db.get_session() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    @classmethod
    def load_from_db(cls, correlation_id: str) -> "CommandExecutionDB":
        with settings.db.get_session() as session:
            return session.exec(select(cls).where(cls.correlation_id == correlation_id)).one()

    @classmethod
    def get_client_routing_key(cls, correlation_id: str) -> str:
        cmd_execution_db = cls.load_from_db(correlation_id)
        return cmd_execution_db.private_routing_key
