from typing import Literal
from .base_spec import BaseParameterSpec

__all__ = ["StrParameterSpec", "IntParameterSpec", "FloatParameterSpec", "BoolParameterSpec"]

class StrParameterSpec(BaseParameterSpec):
    dtype: Literal["str"]


class IntParameterSpec(BaseParameterSpec):
    dtype: Literal["int"]


class FloatParameterSpec(BaseParameterSpec):
    dtype: Literal["float"]


class BoolParameterSpec(BaseParameterSpec):
    dtype: Literal["bool"]
