from typing import Any, Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ParameterSpecBase(QCrBoxPydanticBaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = True


class ParameterSpecDB(ParameterSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "parameter"
    __table_args__ = (UniqueConstraint("name", "command_id"), {"extend_existing": True})

    id: Optional[int] = Field(default=None, primary_key=True)

    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: "CommandSpecDB" = Relationship(back_populates="parameters")


class ParameterSpecCreate(ParameterSpecBase):
    __qcrbox_sql_model__ = ParameterSpecDB

    default_value: Optional[Any] = None
