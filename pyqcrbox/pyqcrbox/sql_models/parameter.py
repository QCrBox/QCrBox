from typing import Any, Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class ParameterSpecBase(QCrBoxPydanticBaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = True
    default_value: Optional[Any] = None


class ParameterSpecCreate(ParameterSpecBase):
    def to_sql_model(self):
        return ParameterSpecDB.from_pydantic_model(self)


class ParameterSpecDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "parameter"
    __table_args__ = (UniqueConstraint("name", "command_id"), {"extend_existing": True})
    __pydantic_model_cls__ = ParameterSpecCreate

    name: str
    type: str
    description: str = ""
    required: bool = True

    id: Optional[int] = Field(default=None, primary_key=True)
    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    command: "CommandSpecDB" = Relationship(back_populates="parameters")

    @classmethod
    def from_pydantic_model(cls, param):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(param, pydantic_model_cls)
        return cls(**param.model_dump())


class ParameterSpecRead(ParameterSpecBase):
    pass
