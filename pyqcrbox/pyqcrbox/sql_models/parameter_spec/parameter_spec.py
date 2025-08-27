import inspect
from typing import Annotated, Union

from pydantic import Field, Tag, TypeAdapter

from pyqcrbox import logger

from .builtin_parameter_types import BoolParameterSpec, FloatParameterSpec, IntParameterSpec, StrParameterSpec
from .filesystem_path_parameters import (
    CifDataFileParameterSpec,
    DataFileParameterSpec,
    # FolderPathParameterSpec,
    # GenericInputPathParameterSpec,
    # GenericOutputPathParameterSpec,
    # InputCifParameterSpec,
    # InputFolderParameterSpec,
    OutputCifParameterSpec,
    # WorkCifParameterSpec,
)

__all__ = ["ParameterSpecDiscriminatedUnion"]


ParameterSpecTaggedUnion = Union[  # noqa: UP007
    #
    # Builtin types
    #
    Annotated[StrParameterSpec, Tag("str")],
    Annotated[IntParameterSpec, Tag("int")],
    Annotated[FloatParameterSpec, Tag("float")],
    Annotated[BoolParameterSpec, Tag("bool")],
    #
    # File/directory types with QCrBox-specific logic
    #
    Annotated[OutputCifParameterSpec, Tag("QCrBox.output_cif")],
    Annotated[DataFileParameterSpec, Tag("QCrBox.data_file")],
    Annotated[CifDataFileParameterSpec, Tag("QCrBox.cif_data_file")],
    #
    # Deprecated parameters
    #
    # Annotated[InputCifParameterSpec, Tag("QCrBox.input_cif")],
    # Annotated[GenericInputPathParameterSpec, Tag("QCrBox.input_path")],
    # Annotated[GenericOutputPathParameterSpec, Tag("QCrBox.output_path")],
    # Annotated[WorkCifParameterSpec, Tag("QCrBox.work_cif")],
    # Annotated[FolderPathParameterSpec, Tag("QCrBox.folder_path")],
    # Annotated[InputFolderParameterSpec, Tag("QCrBox.input_folder")],
]

ParameterSpecDiscriminatedUnion = Annotated[ParameterSpecTaggedUnion, Field(discriminator="dtype")]
parameter_spec_adapter: TypeAdapter[ParameterSpecTaggedUnion] = TypeAdapter(ParameterSpecDiscriminatedUnion)


def get_param_spec_from_json(param_spec_json: dict) -> ParameterSpecDiscriminatedUnion:
    return parameter_spec_adapter.validate_python(param_spec_json)


def get_param_spec_from_signature_param(p: inspect.Parameter) -> ParameterSpecDiscriminatedUnion | None:
    if p.annotation == inspect._empty:
        logger.error(f"Parameter {p.name} has no annotation")
        return None

    dtype = p.annotation.__name__
    is_required = p.default == inspect._empty
    default_value = None if is_required else repr(p.default)

    param_spec_json = {
        "name": p.name,
        "dtype": dtype,
        "default_value": default_value,
        "description": "dummy description which can be whatever for this validation step",
    }
    return get_param_spec_from_json(param_spec_json)
