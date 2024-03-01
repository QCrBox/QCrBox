from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from ..settings import settings
from .command_spec import CommandSpecCreate, CommandSpecDB
from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ApplicationSpecBase(SQLModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class ApplicationSpecCreate(ApplicationSpecBase):
    commands: list[CommandSpecCreate] = []

    def save_to_db(self):
        with settings.db.get_session() as session:
            application_db = ApplicationSpecDB(**self.model_dump(exclude={"commands"}))
            session.add(application_db)
            session.commit()
            session.refresh(application_db)

            for cmd in self.commands:
                cmd.save_to_db()

            return application_db


class ApplicationSpecDB(ApplicationSpecBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: list[CommandSpecDB] = Relationship(back_populates="application")
