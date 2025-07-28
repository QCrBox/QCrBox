from abc import ABC, abstractmethod
from typing import Annotated, Any

from pydantic import BeforeValidator, field_validator, model_validator

from pyqcrbox.logging import logger

from ..base import QCrBoxPydanticBaseModel

SENTINEL_UNDEFINED = "<undefined>"


class BaseParameter(QCrBoxPydanticBaseModel, ABC):
    @abstractmethod
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        pass


class BuiltinParameter(BaseParameter):
    dtype: str
    value: Any

    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        return self.value


class DataFileParameter(BaseParameter):
    data_file_id: str

    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> str:
        from pyqcrbox.services import get_data_file_manager

        logger.debug(f"Preparing data file for execution: {self!r}")
        data_file_manager = await get_data_file_manager()
        exported_file_path = await data_file_manager.export_data_file(self.data_file_id, target_dir, target_filename)
        return str(exported_file_path)


class CifDataFileParameter(BaseParameter):
    data_file_id: str

    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> str:
        from pyqcrbox.services import get_data_file_manager

        logger.debug(f"Preparing CIF data file for execution: {self!r}")
        data_file_manager = await get_data_file_manager()
        exported_file_path = await data_file_manager.export_data_file(self.data_file_id, target_dir, target_filename)
        return str(exported_file_path)


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
    "QCrBox.input_folder": str,
}

_custom_dtypes = {
    "QCrBox.data_file": DataFileParameter,
    "QCrBox.cif_data_file": CifDataFileParameter,
}

_known_dtypes = _builtin_dtypes | _custom_dtypes


def verify_dtype_is_a_known_type(v: str) -> str:
    if v not in _known_dtypes:
        raise ValueError(f"Unsupported dtype: {v!r}")
    return v


def parse_parameter_default_value_as_string(v: Any, dtype: type | None = None) -> BuiltinParameter:
    if not dtype:
        dtype = type(v)
    return BuiltinParameter(dtype=str(dtype), value=v)


def parse_parameter_as_its_dtype(v: Any, dtype_str) -> Any:
    if dtype_str not in _known_dtypes:
        raise ValueError(f"Unsupported parameter type: {dtype_str}")

    if dtype_str in _builtin_dtypes:
        dtype = _builtin_dtypes[dtype_str]
        return BuiltinParameter(dtype=str(dtype), value=v)

    try:
        result = _known_dtypes[dtype_str](**v) if isinstance(v, dict) else _known_dtypes[dtype_str](v)
    except Exception as exc:
        logger.warning(
            f"Could not convert value to its declared type - leaving unchanged: value={v!r}\n\n"
            f"Original error: {exc}"
        )
        result = v

    return result


DTypeAsStr = Annotated[str, BeforeValidator(verify_dtype_is_a_known_type)]
DefaultValueAsStr = Annotated[BuiltinParameter, BeforeValidator(parse_parameter_default_value_as_string)]


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: DTypeAsStr
    required: bool = True
    default_value: DefaultValueAsStr | None = None
    description: str = ""

    @field_validator("dtype")
    @classmethod
    def verify_dtype_is_a_known_type(cls, value: str) -> str:
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

    def dtype_is_compatible_with(self, other_dtype: str):
        return self.dtype == other_dtype
