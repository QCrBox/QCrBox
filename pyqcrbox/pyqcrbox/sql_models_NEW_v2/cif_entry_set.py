from typing import Literal, Self, Union

from pydantic import model_validator
from typing_extensions import TypeAliasType

from .base import QCrBoxPydanticBaseModel

__all__ = ["CifEntrySet"]


CifEntryLiteral = TypeAliasType("CifEntryLiteral", str)
CifEntryOneOf = TypeAliasType("CifEntryOneOf", dict[Literal["one_of"], list["CifEntryLiteral"]])
CifEntry = TypeAliasType("CifEntry", Union[CifEntryLiteral, CifEntryOneOf])


class CifEntrySet(QCrBoxPydanticBaseModel):
    name: str
    required: list[CifEntry] | None = []
    optional: list[CifEntry] | None = []

    @model_validator(mode="after")
    def ensure_required_and_optional_entries_are_not_both_missing(self) -> Self:
        if self.required == [] and self.optional == []:
            raise ValueError("At least one of 'required' and 'optional' entry sets must be provided.")
        return self
