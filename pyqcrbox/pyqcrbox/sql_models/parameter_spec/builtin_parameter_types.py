from typing import Literal

from .base_parameter_spec import BaseParameterSpec

__all__ = ["StrParameterSpec", "IntParameterSpec", "FloatParameterSpec", "BoolParameterSpec"]


class StrParameterSpec(BaseParameterSpec):
    dtype: Literal["str"] = "str"


class IntParameterSpec(BaseParameterSpec):
    dtype: Literal["int"] = "int"


class FloatParameterSpec(BaseParameterSpec):
    dtype: Literal["float"] = "float"


class BoolParameterSpec(BaseParameterSpec):
    dtype: Literal["bool"] = "bool"
