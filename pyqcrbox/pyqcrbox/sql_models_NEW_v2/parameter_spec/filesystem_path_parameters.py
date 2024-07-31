from typing import Literal, Self

from pydantic import model_validator

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
    required_entries: list[str] = []
    optional_entries: list[str] = []
    required_entry_sets: list[str] = []
    optional_entry_sets: list[str] = []
    merge_su: bool = False
    custom_categories: list[str] = []

    @model_validator(mode="after")
    def ensure_one_cif_entry_definition_present(self) -> Self:
        cif_entry_sources = [
            self.required_entries,
            self.optional_entries,
            self.required_entry_sets,
            self.optional_entry_sets,
        ]
        if all(li == [] for li in cif_entry_sources):
            raise ValueError("At least one of 'required' and 'optional' entry definitions or sets must be provided.")
        return self


class InputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.input_cif"]


class OutputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.output_cif"]
    invalidated_entries: list[str]
    output_block: int = 0  # default: select first block from output cif file


class WorkCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.work_cif"]
