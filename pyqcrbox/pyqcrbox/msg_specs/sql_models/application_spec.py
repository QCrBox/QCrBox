from datetime import datetime
from typing import List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship

from .qcrbox_base_sql_model import QCrBoxBaseSQLModel


class ApplicationSpec(QCrBoxBaseSQLModel):
    name: str
    slug: str
    version: str
    description: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class ApplicationSpecDB(ApplicationSpec, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("name", "version"),)

    # Additional fields stored in the database that are not provided in the incoming message
    id: Optional[int] = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)

    commands: List["CommandSpecDB"] = Relationship(back_populates="application")
