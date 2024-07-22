from typing import Annotated, Any
from pyqcrbox.logging import logger
from pydantic import BeforeValidator, field_validator, model_validator

from ..base import QCrBoxPydanticBaseModel

SENTINEL_UNDEFINED = "<undefined>"

_known_dtypes = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "QCrBox.input_cif": str,
    "QCrBox.output_cif": str,
    "QCrBox.work_cif": str,
    "QCrBox.folder_path": str,
    "QCrBox.input_file": str,
    "QCrBox.output_file": str,
}


def parse_parameter_default_value_as_string(v: Any) -> str:
    # logger.debug(f"[DDD] convert_default_value_to_string_representation({v=!r})")
    return repr(v)


DefaultValue = Annotated[str, BeforeValidator(parse_parameter_default_value_as_string)]


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: str
    required: bool = True
    default_value: DefaultValue | None
    description: str = ""

    merge_su: bool = False
    required_entry_sets: list[str] = []
    optional_entry_sets: list[str] = []
    custom_categories: list[str] = []

    @field_validator("dtype")
    @classmethod
    def verify_dtype_is_a_known_type(cls, value: str) -> str:
        # logger.debug(f"[DDD] verify_dtype_is_a_known_type({value})")
        if value not in _known_dtypes:
            raise ValueError(f"Unsupported dtype: {value!r}")
        return value

    # @field_validator("default_value")
    # @classmethod
    # def convert_default_value_to_string_representation(cls, value: Any) -> str:
    #     logger.debug(f"[DDD] convert_default_value_to_string_representation({value})")
    #     return repr(value)

    @model_validator(mode="before")
    @classmethod
    def set_required_and_default_value(cls, model_data: dict) -> dict:
        from pyqcrbox.logging import logger

        # logger.debug(f"[DDD] Hi there from model_validator")
        model_data = model_data.copy()

        if "default_value" not in model_data or model_data["default_value"] == SENTINEL_UNDEFINED:
            model_data["required"] = True
            model_data["default_value"] = SENTINEL_UNDEFINED
        else:
            model_data["required"] = False

        # dtype_val = model_data["dtype"]
        # try:
        #     actual_dtype = _known_dtypes[dtype_val]
        # except KeyError:
        #     logger.warning(f"Unrecognised dtype: {dtype_val}")
        #
        # if isinstance(model_data["dtype"], type):
        #     model_data["default_value"] = model_data["dtype"](model_data["default_value"])
        # else:
        #     logger.warning(f"Could not convert default value to its declared type- leaving as string.")

        return model_data
