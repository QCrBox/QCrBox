from typing import Literal

from .base_spec import BaseParameterSpec

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
    required_entry_sets: list[str] = []
    optional_entry_sets: list[str] = []
    merge_su: bool = False
    custom_categories: list[str] = []


class InputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.input_cif"]


class OutputCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.output_cif"]
    invalidated_entries: list[str]
    output_block: int = 0  # default: select first block from output cif file


class WorkCifParameterSpec(BaseCifFileParameterSpec):
    dtype: Literal["QCrBox.work_cif"]
