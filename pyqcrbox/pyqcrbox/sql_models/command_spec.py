from typing import List, Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .application_spec import ApplicationSpecDB
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class CommandSpec(QCrBoxBaseSQLModel):
    name: str
    implemented_as: str  # TODO: use enum to limit the allowed values to 'CLI', 'python_callable', 'interactive', ...
    description: str = ""


class CommandSpecDB(CommandSpec, table=True):
    __tablename__ = "command"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "application_id",
        ),
    )

    # Additional fields stored in the database that are not provided in the incoming message
    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: ApplicationSpecDB = Relationship(back_populates="commands")
    parameters: List["ParameterSpecDB"] = Relationship(back_populates="command")
