from typing import Literal

from pydantic import validator

from ..cif_entry_set import OneOfCifEntrySpec
from .base_parameter_spec import BaseParameterSpec

__all__ = [
    "FolderPathParameterSpec",
    "InputCifParameterSpec",
    "GenericInputFileParameterSpec",
    "OutputCifParameterSpec",
    "WorkCifParameterSpec",
]


class BaseFilesystemPathParameterSpec(BaseParameterSpec):
    pass


class GenericInputFileParameterSpec(BaseFilesystemPathParameterSpec):
    dtype: Literal["QCrBox.input_file"]


class GenericOutputFileParameterSpec(BaseFilesystemPathParameterSpec):
    dtype: Literal["QCrBox.output_file"]


class FolderPathParameterSpec(BaseFilesystemPathParameterSpec):
    dtype: Literal["QCrBox.folder_path"]


class BaseCifFileParameterSpec(BaseFilesystemPathParameterSpec):
    required_entries: list[str | OneOfCifEntrySpec] = []
    optional_entries: list[str | OneOfCifEntrySpec] = []
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


class InputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.input_cif"]


class OutputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.output_cif"]
    invalidated_entries: list[str]
    output_block: int = 0  # default: select first block from output cif file


class WorkCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.work_cif"]
