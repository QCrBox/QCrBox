from typing import Literal, Self, Union

from pydantic import model_validator, validator
from typing_extensions import TypeAliasType

from .base import QCrBoxPydanticBaseModel

__all__ = ["CifEntrySet"]


CifEntryLiteral = TypeAliasType("CifEntryLiteral", str)
CifEntryOneOf = TypeAliasType("CifEntryOneOf", dict[Literal["one_of"], list["CifEntryLiteral"]])
CifEntry = TypeAliasType("CifEntry", Union[CifEntryLiteral, CifEntryOneOf])


class OneOfCifEntrySpec(QCrBoxPydanticBaseModel):
    one_of: list[str | list[str]]


class CifEntrySet(QCrBoxPydanticBaseModel):
    name: str
    required: list[str | OneOfCifEntrySpec] | None = []
    optional: list[str | OneOfCifEntrySpec] | None = []

    @model_validator(mode="after")
    def ensure_required_and_optional_entries_are_not_both_missing(self) -> Self:
        if self.required == [] and self.optional == []:
            raise ValueError("At least one of 'required' and 'optional' entry sets must be provided.")
        return self

    # TODO: Check this and add tests
    @validator("required", "optional", pre=True)
    def parse_entries(cls, v):
        if isinstance(v, list):
            return [
                OneOfCifEntrySpec(one_of=item["one_of"]) if isinstance(item, dict) and "one_of" in item else item
                for item in v
            ]
        return v
