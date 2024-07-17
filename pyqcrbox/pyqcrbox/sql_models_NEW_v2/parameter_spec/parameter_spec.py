import inspect
from typing import Annotated, Union

from pydantic import Field, Tag, TypeAdapter

from .base_parameter_spec import SENTINEL_UNDEFINED
from .builtin_parameter_types import BoolParameterSpec, FloatParameterSpec, IntParameterSpec, StrParameterSpec

__all__ = ["ParameterSpec"]


ParameterSpecBase = Union[
    Annotated[StrParameterSpec, Tag("str")],
    Annotated[IntParameterSpec, Tag("int")],
    Annotated[FloatParameterSpec, Tag("float")],
    Annotated[BoolParameterSpec, Tag("bool")],
]
ParameterSpec = Annotated[ParameterSpecBase, Field(discriminator="dtype")]

parameter_spec_adapter: TypeAdapter[ParameterSpecBase] = TypeAdapter(ParameterSpec)
parameter_specs_adapter: TypeAdapter[list[ParameterSpecBase]] = TypeAdapter(list[ParameterSpec])


def get_param_spec_from_json(param_spec_json: dict) -> ParameterSpec:
    return parameter_spec_adapter.validate_python(param_spec_json)


def get_param_spec_from_signature_param(p: inspect.Parameter) -> ParameterSpec:
    dtype = p.annotation.__name__
    is_required = p.default == inspect._empty
    default_value = SENTINEL_UNDEFINED if is_required else p.default

    param_spec_json = {"name": p.name, "dtype": dtype, "required": is_required, "default_value": default_value}
    return get_param_spec_from_json(param_spec_json)
