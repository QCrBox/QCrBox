from pydantic import field_serializer, field_validator, model_validator

__all__ = ["ParameterSpec"]

import inspect
from typing import Any, Self

from .base import QCrBoxPydanticBaseModel
from .parameter_types import get_parameter_type_class


class NoDefaultValue(Exception):
    pass


class ParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: type
    description: str = ""
    required: bool
    default_value: Any

    @classmethod
    def from_function_signature_param(cls, name: str, inspected_param: inspect.Parameter) -> "ParameterSpec":
        assert isinstance(name, str)
        assert isinstance(inspected_param, inspect.Parameter)

        is_optional = inspected_param.default != inspect._empty
        default_value = inspected_param.default if is_optional else Ellipsis

        return cls(name=name, dtype=inspected_param.annotation, required=not is_optional, default_value=default_value)

    @field_validator("dtype", mode="before")
    @classmethod
    def convert_dtype_str_to_actual_type(cls, dtype: str | type) -> type:
        if isinstance(dtype, type):
            return type
        else:
            return get_parameter_type_class(dtype)

    @field_serializer("dtype")
    def serialize_dtype_to_its_string_representation(self, dtype: type) -> str:
        return dtype.__name__

    @field_serializer("default_value")
    def serialize_default_value_to_its_string_representation(self, default_value: Any) -> str:
        if default_value == Ellipsis:
            return "<undefined>"
        else:
            return repr(default_value)

    @model_validator(mode="before")
    def store_default_value_if_provided(self) -> Self:
        assert isinstance(self, dict), "Expected a dictionary in model validator"

        if "default_value" not in self or self["default_value"] == "<undefined>":
            self["required"] = True
            self["default_value"] = Ellipsis
        else:
            self["required"] = False

        return self

    @model_validator(mode="after")
    def validate_default_value_against_dtype(self) -> Self:
        if self.required:
            return self  # nothing to validate (no default value present)

        return self
