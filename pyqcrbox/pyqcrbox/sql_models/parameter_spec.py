from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .command_spec import CommandSpecDB
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ParameterSpec(QCrBoxBaseSQLModel):
    name: str
    dtype: str
    description: str = ""
    required: bool = True
    # default_value: Optional[Any] = None


class ParameterSpecDB(ParameterSpec, table=True):
    __tablename__ = "parameter"
    __table_args__ = (UniqueConstraint("name", "command_id"),)

    # Additional fields stored in the database that are not provided in the incoming message
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key relationships
    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: CommandSpecDB = Relationship(back_populates="parameters")
