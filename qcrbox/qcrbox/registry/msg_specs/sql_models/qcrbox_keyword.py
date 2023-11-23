from typing import Optional, List

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Relationship

__all__ = ["Keyword", "KeywordDB", "KeywordRead"]


class CommandKeywordLink(SQLModel, table=True):
    command_id: Optional[int] = Field(default=None, foreign_key="command.id", primary_key=True)
    keyword_id: Optional[int] = Field(default=None, foreign_key="keyword.id", primary_key=True)


class Keyword(BaseModel):
    id: int
    text: str


class KeywordDB(SQLModel, table=True):
    __tablename__ = "keyword"

    id: Optional[int] = Field(default=None, primary_key=True)
    text: str = Field(default=None, unique=True, nullable=False)

    commands: List["QCrBoxCommandDB"] = Relationship(back_populates="keywords", link_model=CommandKeywordLink)


class KeywordRead(BaseModel):
    id: int
    text: str
