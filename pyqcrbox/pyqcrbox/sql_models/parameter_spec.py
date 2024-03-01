from typing import Any, Optional

from pydantic import BaseModel
from sqlmodel import Field, Relationship, UniqueConstraint

from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ParameterSpecBase(BaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = True


class ParameterSpecCreate(ParameterSpecBase):
    default_value: Optional[Any] = None


class ParameterSpecDB(ParameterSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "parameter"
    __table_args__ = (UniqueConstraint("name", "command_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: "CommandSpecDB" = Relationship(back_populates="parameters")
