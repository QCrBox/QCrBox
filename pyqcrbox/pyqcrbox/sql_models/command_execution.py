from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship

from pyqcrbox.settings import settings

from .command_invocation import CommandInvocationDB
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class CommandExecutionCreate(QCrBoxPydanticBaseModel):
    command_invocation_db: CommandInvocationDB

    def to_sql_model(self):
        return CommandExecutionDB.from_pydantic_model(self)

    def save_to_db(self):
        return self.to_sql_model().save_to_db()


class CommandExecutionDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command_execution"
    __pydantic_model_cls__ = CommandExecutionCreate

    timestamp: datetime = Field(default_factory=datetime.now)

    id: Optional[int] = Field(default=None, primary_key=True)

    command_invocation: Optional["CommandInvocationDB"] = Relationship(
        sa_relationship_kwargs={"uselist": False},
        back_populates="command_execution",
    )

    @classmethod
    def from_pydantic_model(cls, model):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(model, pydantic_model_cls)
        data = model.model_dump()
        return cls(**data)

    def save_to_db(self):
        with settings.db.get_session() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self
