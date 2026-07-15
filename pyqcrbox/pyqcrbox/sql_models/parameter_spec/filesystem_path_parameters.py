from typing import Literal

from pydantic import validator

from ..cif_entry_set import CifEntryLiteral, OneOfCifEntrySpec
from .base_parameter_spec import BaseParameterSpec

__all__ = [
    "DataFileParameterSpec",
    "CifDataFileParameterSpec",
]


class BaseFilesystemPathParameterSpec(BaseParameterSpec):
    def dtype_is_compatible_with(self, other_dtype: str):
        if super().dtype_is_compatible_with(other_dtype):
            return True

        return other_dtype in ["str"]


class DataFileParameterSpec(BaseFilesystemPathParameterSpec):
    dtype: Literal["QCrBox.data_file"]


class BaseCifFileParameterSpec(BaseFilesystemPathParameterSpec):
    required_entries: list[CifEntryLiteral | OneOfCifEntrySpec] = []
    optional_entries: list[CifEntryLiteral | OneOfCifEntrySpec] = []
    required_entry_sets: list[str] = []
    optional_entry_sets: list[str] = []
    merge_su: bool = False
    custom_categories: list[str] = []

    # TODO: Check this and add tests
    @validator("required_entries", "optional_entries", pre=True)
    def parse_entries(cls, v):
        if isinstance(v, list):
            return [
                OneOfCifEntrySpec(one_of=item["one_of"]) if isinstance(item, dict) and "one_of" in item else item
                for item in v
            ]
        return v


class CifDataFileParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.cif_data_file"]
