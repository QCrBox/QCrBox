from pydantic import model_validator

from typing import Self
from .base import QCrBoxPydanticBaseModel

__all__ = ["CifEntrySet"]


class CifEntrySet(QCrBoxPydanticBaseModel):
    name: str
    required: list[str] | None = []
    optional: list[str] | None = []

    @model_validator(mode="after")
    def ensure_required_and_optional_entries_are_not_both_missing(self) -> Self:
        if self.required == [] and self.optional == []:
            raise ValueError(f"At least one of 'required' and 'optional' entry sets must be provided.")
        return self
