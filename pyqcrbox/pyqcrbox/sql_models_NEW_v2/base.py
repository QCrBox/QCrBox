from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel

__all__ = ["QCrBoxPydanticBaseModel"]


class QCrBoxPydanticBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class QCrBoxBaseSQLModel(SQLModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
