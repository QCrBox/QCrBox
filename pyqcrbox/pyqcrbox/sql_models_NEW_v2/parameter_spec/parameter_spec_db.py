import json

from pydantic import field_serializer
from sqlmodel import JSON, Field

from ..base import QCrBoxBaseSQLModel


class ParameterSpecDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "parameter"
    # __table_args__ = (UniqueConstraint("name", "command_id"),)

    name: str
    dtype: str
    required: bool
    default_value: str
    description: str

    required_entry_sets: list[str] = Field(default_factory=list, sa_type=JSON)
    optional_entry_sets: list[str] = Field(default_factory=list, sa_type=JSON)
    merge_su: bool
    custom_categories: list[str] = Field(default_factory=list, sa_type=JSON)

    id: int | None = Field(default=None, primary_key=True)

    #    command_id: Optional[int] = Field(default=None, foreign_key="command.id")
    #    command: "CommandSpecDB" = Relationship(back_populates="commands")

    @field_serializer("required_entry_sets", "optional_entry_sets", "custom_categories")
    def serialize_list_of_strings(values: list[str]):
        return json.dumps(values)
