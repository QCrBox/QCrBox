from typing import Any, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from ..settings import settings
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ParameterSpecBase(SQLModel):
    name: str
    type: str
    description: str = ""
    required: bool = True


class ParameterSpecCreate(ParameterSpecBase):
    default_value: Optional[Any] = None

    def save_to_db(self):
        with settings.db.get_session() as session:
            param_db = ParameterSpecDB(**self.model_dump())
            session.add(param_db)
            session.commit()
            session.refresh(param_db)
            return param_db


class ParameterSpecDB(ParameterSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "parameter"
    __table_args__ = (UniqueConstraint("name", "command_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: "CommandSpecDB" = Relationship(back_populates="parameters")
