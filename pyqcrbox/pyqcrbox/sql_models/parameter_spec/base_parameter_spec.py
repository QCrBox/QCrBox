from typing import Annotated, Any

from pydantic import BeforeValidator, field_validator, model_validator

from pyqcrbox.logging import logger

from ..base import QCrBoxPydanticBaseModel

SENTINEL_UNDEFINED = "<undefined>"


class DataFileParameter(QCrBoxPydanticBaseModel):
    dataset_id: str
    key: str


_builtin_dtypes = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "QCrBox.input_cif": str,
    "QCrBox.output_cif": str,
    "QCrBox.work_cif": str,
    "QCrBox.folder_path": str,
    "QCrBox.input_path": str,
    "QCrBox.output_path": str,
}

_custom_dtypes = {
    "QCrBox.data_file": DataFileParameter,
}

_known_dtypes = _builtin_dtypes | _custom_dtypes


def verify_dtype_is_a_known_type(v: str) -> str:
    if v not in _known_dtypes:
        raise ValueError(f"Unsupported dtype: {v!r}")
    return v


def parse_parameter_default_value_as_string(v: Any) -> str:
    # logger.debug(f"[DDD] convert_default_value_to_string_representation({v=!r})")
    return repr(v)


def parse_parameter_default_as_its_dtype(v: Any, dtype_str) -> Any:
    try:
        if isinstance(v, dict):
            result = _known_dtypes[dtype_str](**v)
        else:
            result = _known_dtypes[dtype_str](v)
    except Exception as exc:
        logger.warning(f"Could not convert default value to its declared type- leaving unchanged: {exc}")
        result = v

    return result


DTypeAsStr = Annotated[str, BeforeValidator(verify_dtype_is_a_known_type)]
DefaultValueAsStr = Annotated[str, BeforeValidator(parse_parameter_default_value_as_string)]


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: DTypeAsStr
    required: bool = True
    default_value: DefaultValueAsStr | None = None
    description: str = ""

    @field_validator("dtype")
    @classmethod
    def verify_dtype_is_a_known_type(cls, value: str) -> str:
        # logger.debug(f"[DDD] verify_dtype_is_a_known_type({value})")
        if value not in _known_dtypes:
            raise ValueError(f"Unsupported dtype: {value!r}")
        return value

    @model_validator(mode="before")
    @classmethod
    def set_field_required(cls, model_data: dict) -> dict:
        model_data = model_data.copy()

        if "default_value" not in model_data or model_data["default_value"] is None:
            model_data["required"] = True
            # model_data["default_value"] = SENTINEL_UNDEFINED
        else:
            model_data["required"] = False

        return model_data

    # @field_validator("default_value")
    # @classmethod
    # def convert_default_value_to_string_representation(cls, value: Any) -> str:
    #     logger.debug(f"[DDD] convert_default_value_to_string_representation({value})")
    #     return repr(value)

    # @model_validator(mode="before")
    # @classmethod
    # def set_required_and_default_value(cls, model_data: dict) -> dict:
    #     from pyqcrbox.logging import logger
    #
    #     # logger.debug(f"[DDD] Hi there from model_validator")
    #     model_data = model_data.copy()
    #
    #     if "default_value" not in model_data or model_data["default_value"] == SENTINEL_UNDEFINED:
    #         model_data["required"] = True
    #         model_data["default_value"] = SENTINEL_UNDEFINED
    #     else:
    #         model_data["required"] = False
    #
    #     # dtype_val = model_data["dtype"]
    #     # try:
    #     #     actual_dtype = _known_dtypes[dtype_val]
    #     # except KeyError:
    #     #     logger.warning(f"Unrecognised dtype: {dtype_val}")
    #     #
    #     # if isinstance(model_data["dtype"], type):
    #     #     model_data["default_value"] = model_data["dtype"](model_data["default_value"])
    #     # else:
    #     #     logger.warning(f"Could not convert default value to its declared type- leaving as string.")
    #
    #     return model_data
