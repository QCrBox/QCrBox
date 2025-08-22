from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Any

import nats.js.errors as nats_errors
import svcs
from pydantic import BeforeValidator, field_validator, model_validator

from pyqcrbox.debug import log_eel
from pyqcrbox.logging import logger

from ..base import QCrBoxPydanticBaseModel

if TYPE_CHECKING:
    from pyqcrbox.data_management import DataManager

SENTINEL_UNDEFINED = "<undefined>"


async def check_if_id_is_a_dataset(data_manager: "DataManager", id_to_check: str) -> bool:
    """Check if an ID is for a dataset.

    This is used when an exception is raised when trying to write a data file
    to disk. It is easy to pass a dataset ID instead of a data file ID.

    Parameters
    ----------
    data_file_manager : DataFileManger
        An instance of the DataManager
    id_to_check : str
        The ID to check.

    Returns
    -------
    bool
        True if is a dataset ID, False otherwise.

    """
    from pyqcrbox.data_management import DatasetNotFoundError

    try:
        await data_manager.get_dataset_info(id_to_check)
        return True
    except DatasetNotFoundError:
        return False


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


class BaseParameter(QCrBoxPydanticBaseModel, ABC):
    @abstractmethod
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        pass


class BuiltinParameter(BaseParameter):
    dtype: str
    value: Any

    @log_eel
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        return _builtin_dtypes[self.dtype](self.value)


class DataFileParameter(BaseParameter):
    data_file_id: str

    @log_eel
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> str:
        from pyqcrbox.data_management import DataManager
        from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

        logger.debug(f"Preparing data file for execution: {self!r}")
        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            data_file_manager = await container.aget(DataManager)
            try:
                exported_file_path = await data_file_manager.export_data_file(
                    self.data_file_id, target_dir, target_filename
                )
            except nats_errors.ObjectNotFoundError as exc:
                if await check_if_id_is_a_dataset(data_file_manager, self.data_file_id):
                    exc_msg = f"Provided data file ID {self.data_file_id} is a dataset ID"
                else:
                    exc_msg = f"No data file was found with id {self.data_file_id}"
                raise ValueError(exc_msg) from exc

        return str(exported_file_path)


class CifDataFileParameter(BaseParameter):
    data_file_id: str
    # More CIF specific parameters will go in here

    @log_eel
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> str:
        from pyqcrbox.data_management import DataManager
        from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

        logger.debug(f"Preparing CIF data file for execution: {self!r}")
        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            data_file_manager = await container.aget(DataManager)
            try:
                exported_file_path = await data_file_manager.export_data_file(
                    self.data_file_id, target_dir, target_filename
                )
            except nats_errors.ObjectNotFoundError as exc:
                if await check_if_id_is_a_dataset(data_file_manager, self.data_file_id):
                    exc_msg = f"Provided data file ID {self.data_file_id} is a dataset ID"
                else:
                    exc_msg = f"No data file was found with id {self.data_file_id}"
                raise ValueError(exc_msg) from exc

        return str(exported_file_path)


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
    if not dtype or not isinstance(dtype, type):
        dtype = type(v)
    return BuiltinParameter(dtype=dtype.__name__, value=v)


def parse_parameter_as_its_dtype(v: Any, dtype_str: str) -> Any:
    if dtype_str not in _known_dtypes:
        raise ValueError(f"Unsupported parameter type: {dtype_str}")

    if dtype_str in _builtin_dtypes:
        dtype = _builtin_dtypes[dtype_str]
        return BuiltinParameter(dtype=dtype.__name__, value=dtype(v))

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
