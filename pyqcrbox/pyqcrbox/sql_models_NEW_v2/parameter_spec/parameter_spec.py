import inspect
from typing import Annotated, Union

from pydantic import Field, Tag, TypeAdapter

# from .base_parameter_spec import SENTINEL_UNDEFINED
from .builtin_parameter_types import BoolParameterSpec, FloatParameterSpec, IntParameterSpec, StrParameterSpec
from .filesystem_path_parameters import (
    FolderPathParameterSpec,
    GenericInputFileParameterSpec,
    GenericOutputFileParameterSpec,
    InputCifParameterSpec,
    OutputCifParameterSpec,
    WorkCifParameterSpec,
)

__all__ = ["ParameterSpecDiscriminatedUnion"]


ParameterSpecTaggedUnion = Union[
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
    Annotated[InputCifParameterSpec, Tag("QCrBox.input_cif")],
    Annotated[GenericInputFileParameterSpec, Tag("QCrBox.input_file")],
    Annotated[OutputCifParameterSpec, Tag("QCrBox.output_cif")],
    Annotated[GenericOutputFileParameterSpec, Tag("QCrBox.output_file")],
    Annotated[WorkCifParameterSpec, Tag("QCrBox.work_cif")],
    Annotated[FolderPathParameterSpec, Tag("QCrBox.folder_path")],
]
ParameterSpecDiscriminatedUnion = Annotated[ParameterSpecTaggedUnion, Field(discriminator="dtype")]

parameter_spec_adapter: TypeAdapter[ParameterSpecTaggedUnion] = TypeAdapter(ParameterSpecDiscriminatedUnion)


def get_param_spec_from_json(param_spec_json: dict) -> ParameterSpecDiscriminatedUnion:
    return parameter_spec_adapter.validate_python(param_spec_json)


def get_param_spec_from_signature_param(p: inspect.Parameter) -> ParameterSpecDiscriminatedUnion:
    dtype = p.annotation.__name__
    is_required = p.default == inspect._empty
    default_value = None if is_required else repr(p.default)

    param_spec_json = {"name": p.name, "dtype": dtype, "required": is_required, "default_value": default_value}
    return get_param_spec_from_json(param_spec_json)


def ParameterSpec(**kwargs):
    return get_param_spec_from_json(kwargs)
    # if isinstance(data, dict):
    #     return get_param_spec_from_json(data)
    # elif isinstance(data, inspect.Parameter):
    #     return get_param_spec_from_signature_param(data)
    # else:
    #     raise TypeError(f"Cannot instantiate ParameterSpec from input data: {data}")
