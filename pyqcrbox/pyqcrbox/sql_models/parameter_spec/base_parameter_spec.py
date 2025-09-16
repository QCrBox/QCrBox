import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import nats.js.errors as nats_errors
import svcs
from pydantic import BeforeValidator, Field, PrivateAttr, field_validator, model_validator

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
        await data_manager.get_dataset(id_to_check)
        return True
    except DatasetNotFoundError:
        return False


_builtin_dtypes = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "QCrBox.output_cif": str,
    "QCrBox.output_path": str,
    # "QCrBox.input_cif": str,
    # "QCrBox.work_cif": str,
    # "QCrBox.folder_path": str,
    # "QCrBox.input_path": str,
    # "QCrBox.input_folder": str,
}


class BaseParameter(QCrBoxPydanticBaseModel, ABC):
    """Base parameter abstract class."""

    @abstractmethod
    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        """Prepare a parameter for command execution.

        Parameters
        ----------
        target_dir : str
            The target directory to write the parameter to, if relevant.
        target_filename : str | None
            The target filename to write to disk, if relevant.

        Returns
        -------
        Any
            The value of the parameter required for command execution.

        """
        pass


class BuiltinParameter(BaseParameter):
    """Class for handling a builtin data type parameter.

    Attributes
    ----------
    dtype : str
        The data type of the parameter, as a string.
    value : Any
        The value of the parameter.

    """

    dtype: str
    value: Any

    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> Any:
        """Prepare the value for command execution.

        This method essentially converts the value of the parameter into the
        correct data type, ready to be used by the executing command.

        Parameters
        ----------
        target_dir : str
            Unused.
        target_filename: str
            Unused.

        Returns
        -------
        Any
            The value of the parameter as the correct data type.

        """
        return _builtin_dtypes[self.dtype](self.value)


class DataFileParameter(BaseParameter):
    """Class for handling data file parameters, such as JSON or INP files.

    Attributes
    ----------
    data_file_id : str
        The QCrBox data file ID for the CIF file in the DataManager.

    """

    data_file_id: str

    async def prepare_for_execution(self, target_dir: str, target_filename: str | None = None) -> str:
        """Prepare the CIF file for command execution.

        This method is used to retrieve the contents of the file from the
        DataManager and to write it to a location on the container's file
        system.

        Parameters
        ----------
        target_dir : str
            The target directory to write the file to.
        target_filename : str | None
            The target filename to write to disk. If not provided, the filename
            in the DataManger wil lbe used instead.

        Returns
        -------
        str
            The file path (within the application container) to the file written
            to disk.

        """
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


# TODO: change back to BaseParameter
class CifDataFileParameter(QCrBoxPydanticBaseModel):
    """Class for handling CIF datafile parameters.

    Attributes
    ----------
    data_file_id : str
        The QCrBox data file ID for the CIF file in the DataManager.

    """

    data_file_id: str

    # These are CIF specific, required for pre-processing the CIF file
    required_entries: list[str]
    optional_entries: list[str] = []
    merge_su: bool = False
    custom_categories: list[str] = []

    _exported_path: str = PrivateAttr(default="")

    @log_eel
    async def _convert_to_specific_format(self, yaml_path, command_name, parameter_name) -> str:
        """Convert the CIF to a specific format.

        At the moment, this does an in-place conversion by overwriting the
        original CIF export.

        Parameters
        ----------
        yaml_path : str | Path
            The path to the application specification yaml, containing the
            command and parameter specification.
        command_name : str
            The name of the command this parameter is for.
        parameter_name : str
            The name of the CIF parameter.

        Returns
        -------
        str
            The file path to the converted CIF file.

        """
        from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml

        if not Path(self._exported_path).exists():
            raise OSError("CIF has not yet been exported to disk")

        input_cif_path = self._exported_path
        output_cif_path = self._exported_path
        logger.debug(f"_convert_to_specific_format: {input_cif_path=} {output_cif_path=}")

        cif_file_to_specific_by_yml(
            input_cif_path,
            output_cif_path,
            yaml_path,
            command_name,
            parameter_name,
        )

        return output_cif_path

    # async def merge_to_unified_format(self):
    #     """Merge this CIF with another to a unified CIF format."""
    #     from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml
    #     cif_file_merge_to_unified_by_yml(
    #         original_cif_path,
    #         new_cif_path,
    #         output_cif_path,  # merged original and new
    #         YAML_PATH,
    #         command_name,
    #         parameter_name,  # in this case, it will be the parameter name for output_cif_path
    #     )

    @log_eel
    async def prepare_for_execution(
        self, target_dir: str, target_filename: str | None = None, *, conversion_parameters: dict | None
    ) -> str:
        """Prepare the CIF file for command execution.

        This method is used to retrieve the contents of the CIF file from the
        DataManager and to write it to a location on the container's file
        system.

        Parameters
        ----------
        target_dir : str
            The target directory to write the CIF to.
        target_filename : str | None
            The target filename to write to disk. If not provided, the filename
            in the DataManger wil lbe used instead.

        Returns
        -------
        str
            The file path (within the application container) to the CIF file
            written to disk.

        """
        from pyqcrbox.data_management import DataManager
        from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

        logger.debug(f"Preparing CIF data file for execution: {self!r}")
        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            data_file_manager = await container.aget(DataManager)
            try:
                self._exported_path = exported_file_path = await data_file_manager.export_data_file(
                    self.data_file_id, target_dir, target_filename
                )
            except nats_errors.ObjectNotFoundError as exc:
                if await check_if_id_is_a_dataset(data_file_manager, self.data_file_id):
                    exc_msg = f"Provided data file ID {self.data_file_id} is a dataset ID"
                else:
                    exc_msg = f"No data file was found with id {self.data_file_id}"
                raise ValueError(exc_msg) from exc

            if conversion_parameters:
                logger.debug(f"Converting CIF to specific format with params: {conversion_parameters}")
                self._exported_path = exported_file_path = await self._convert_to_specific_format(
                    *conversion_parameters
                )

        return str(exported_file_path)


_custom_dtypes = {
    "QCrBox.data_file": DataFileParameter,
    "QCrBox.cif_data_file": CifDataFileParameter,
}

_known_dtypes = _builtin_dtypes | _custom_dtypes


def verify_dtype_is_a_known_type(v: str) -> str:
    """Verify that a dtype string is known.

    Parameters
    ----------
    v : str
        The dtype to verify as a string.

    Returns
    -------
    str
        The input value.

    """
    if v not in _known_dtypes:
        raise ValueError(f"Unsupported dtype: {v!r}")
    return v


def parse_parameter_default_value_as_string(v: Any, dtype: type | None = None) -> BuiltinParameter:
    """Convert a parameter's value value into a BuiltinParameter class.

    Parameters
    ----------
    v : Any
        The value of the default parameter.
    dtype : type | None
        The data type to convert to. If this is not specified, then the type
        is inferred using Python's `type()` builtin.

    Returns
    -------
    BuiltinParameter
        The parameter as a BuiltinParameter spec.

    """
    if not dtype or not isinstance(dtype, type):
        dtype = type(v)
    return BuiltinParameter(dtype=dtype.__name__, value=v)


def parse_parameter_as_its_dtype(v: Any, dtype_str: str) -> Any:
    """Convert a parameter value into its data type.

    Parameters
    ----------
    v : Any
        The value of the parameter.
    dtype_str : str
        The data type of the parameter, represented as a string.

    Returns
    -------
    Any
        The parameter as the specified data type.

    """
    logger.debug(f"parse_parameter_as_its_dtype: {dtype_str=} value={v}")

    if dtype_str not in _known_dtypes:
        raise ValueError(f"Unsupported parameter type: {dtype_str}")

    if dtype_str in _builtin_dtypes:
        dtype = _builtin_dtypes[dtype_str]
        return BuiltinParameter(dtype=dtype.__name__, value=dtype(v))

    return _known_dtypes[dtype_str](**v)

    # try:
    #     result = _known_dtypes[dtype_str](**v) if isinstance(v, dict) else _known_dtypes[dtype_str](v)
    # except Exception as exc:
    #     logger.warning(
    #         f"Could not convert value to its declared type - leaving unchanged: value={v!r}\n\nOriginal error: {exc}"
    #     )
    #     result = v
    #
    # return result


DTypeAsStr = Annotated[str, BeforeValidator(verify_dtype_is_a_known_type)]
DefaultValueAsStr = Annotated[BuiltinParameter, BeforeValidator(parse_parameter_default_value_as_string)]


class ParameterValidationSpec(QCrBoxPydanticBaseModel):
    """Defines allowed values for a parameter.

    If none of the attributes are filled in, then there will be no validation.

    Attributes
    ----------
    numeric_range : tuple[float | int, float | int]
        The valid numeric range of the parameter (min, max), e.g. [0.0, 1.0].
    chocies: list[str]
        A list of valid string values for the parameters, e.g. ["A", "B", "C"]
    string_regex : str
        A regex pattern to validate string input against.

    """

    numeric_range: tuple[float | int, float | int] | None = None
    choices: list[str] | None = None
    regex: str | None = None

    @model_validator(mode="after")
    def check_at_least_one(cls, values):
        """Check that at least one validation attribute is set."""
        if not (values.numeric_range or values.choices or values.regex):
            raise ValueError("At least one of numeric_range, choices, or regex must be set for validation criteria")
        return values

    @field_validator("numeric_range")
    @classmethod
    def check_numeric_range_valid(cls, value: list[float | int] | None) -> list[float | int] | None:
        """Check if the numeric range is valid (min, max)."""
        if value and value[0] > value[1]:
            raise ValueError("Numeric value range must be (min, max)")
        return value

    def is_valid(self, value: str) -> bool:
        """Check if a value is a valid choice.

        Parameters
        ----------
        value : str
            The value to check.

        Returns
        -------
        bool
            True if valid, False if not.

        """
        if self.numeric_range:
            lo, hi = self.numeric_range
            try:
                if not (lo <= float(value) <= hi):
                    return False
            except ValueError:
                return False
        if self.choices and value not in self.choices:
            return False
        if self.regex:  # noqa: SIM102
            if not re.match(self.regex, value):
                return False

        return True


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    """Base dataclass for defining properties for a command parameter.

    All the attributes as required when defining a parameter. The data type
    (dtype) of the parameter is typically validated when an Application Spec
    class is instantiated.

    Attributes
    ----------
    name : str
        The parameter name/label/identifier.
    dtype : str
        The data type of the parameter as a string, e.g. something like "bool",
        or "QCrBox.cif_data_file".
    description : str
        A human-friendly description of the parameter.
    default_value : Any | None
        An optional default value for parameter, typically used in the frontend
        as a placeholder.
    valid_values : ValidValueSpec | None
        A string representing a range of valid values for the parameter. If this
        is not set, there will be no validation for the parameter.

    """

    name: str
    dtype: DTypeAsStr
    description: str = ""
    default_value: str | int | float | bool | None = None
    valid_value: ParameterValidationSpec | None = None

    # We are marking all parameters as being REQUIRED and freezing the choice.
    # If we want optional parameters later, we can change this to a required
    # field like the above fields.
    required: bool = Field(default_factory=lambda: True, frozen=True)

    @field_validator("required")
    @classmethod
    def verify_parameter_is_required(cls, value: bool) -> bool:
        """Verify that the `required` field is True."""
        if value is not True:
            raise ValueError("`required` field is set to False when it can only be True")

        return value

    @field_validator("dtype")
    @classmethod
    def verify_dtype_is_a_known_type(cls, value: str) -> str:
        """Verify that the dtype attribute is a valid choice and supported."""
        if value not in _known_dtypes:
            raise ValueError(f"Unsupported dtype: {value!r}")
        return value

    @field_validator("default_value")
    @classmethod
    def verify_default_value_is_builtin_dtype(cls, value: Any | None) -> Any | None:
        """Verify that the default value set is the correct dtype.

        TODO : validate that default_value is a dtype compatible with the parameter
        """
        # using `is` to avoid falsey equivalents, such as 0
        if value is None:
            return value
        # Now we have to check to make sure the default value is a compatible
        # data type
        dtype_str = type(value).__name__
        if dtype_str not in _builtin_dtypes:
            supported_dtypes = list(_builtin_dtypes.keys())
            raise ValueError(
                f"Unsupported dtype {dtype_str!r} for default value. Supported values: {', '.join(supported_dtypes)}"
            )
        return value

    @model_validator(mode="after")
    def verify_valid_value_correct_usage(self) -> "BaseParameterSpec":
        """Verify that the correct validation criteria has been used for the dtype."""
        if self.valid_value is None:
            return self

        if self.valid_value.numeric_range and self.dtype == "str":
            raise ValueError(f"numeric_range validator is not compatible with parameter of type {self.dtype}")
        if self.valid_value.choices and self.dtype != "str":
            raise ValueError(f"choices validator is not compatible with parameter of type {self.dtype}")
        if self.valid_value.regex and self.dtype != "str":
            raise ValueError(f"regex validator is not compatible with parameter of type {self.dtype}")

        return self

    def dtype_is_compatible_with(self, other_dtype: type | str) -> bool:
        """Check if this parameter is compatible with another data type.

        TODO: implement more robust checking because e.g. float and int should
              be compatible.

        Parameters
        ----------
        other_dtype : type | str
            The data type to check if the parameter is compatible with.

        Returns
        -------
        bool
            Whether or not the types are compatible.

        """
        if isinstance(other_dtype, type):
            other_dtype = other_dtype.__name__
        return self.dtype == other_dtype
