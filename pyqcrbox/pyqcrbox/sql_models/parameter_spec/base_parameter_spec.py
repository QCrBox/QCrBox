import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import nats.js.errors as nats_errors
import svcs
from pydantic import BeforeValidator, Field, constr, field_validator, model_validator

from pyqcrbox import settings
from pyqcrbox.debug import log_eel
from pyqcrbox.logging import logger

from ..base import QCrBoxPydanticBaseModel

if TYPE_CHECKING:
    from pyqcrbox.data_management import DataManager
    from pyqcrbox.registry.client.executable_command import BaseCommand


async def check_if_id_is_a_dataset(data_manager: "DataManager", id_to_check: str) -> bool:
    """Check if an ID is for a dataset.

    This is used when an exception is raised when trying to write a data file
    to disk. It is easy to pass a dataset ID instead of a data file ID.

    Parameters
    ----------
    data_manager : DataFileManger
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


# Note: output dtypes (QCrBox.output_cif, QCrBox.output_*) are not parameters;
# they are declared in a command's `outputs:` section and their filenames are
# injected into the execution namespace by the client.
_builtin_dtypes = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


class BaseParameter(QCrBoxPydanticBaseModel, ABC):
    """Base parameter abstract class."""

    dtype: str

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

    @log_eel
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
    dtype: str = "QCrBox.data_file"

    # We'll use this to track where the file has been written to disk
    _exported_file_path: str | Path | None

    @log_eel
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
            data_manager = await container.aget(DataManager)
            try:
                self._exported_file_path = await data_manager.export_data_file(
                    self.data_file_id, target_dir, target_filename
                )
            except nats_errors.ObjectNotFoundError as exc:
                if await check_if_id_is_a_dataset(data_manager, self.data_file_id):
                    exc_msg = f"Provided data file ID {self.data_file_id} is a dataset ID"
                else:
                    exc_msg = f"No data file was found with id {self.data_file_id}"
                raise ValueError(exc_msg) from exc

        return str(self._exported_file_path)


class Cif2CifOptions(QCrBoxPydanticBaseModel):
    """Options for Cif2Cif conversion, resolved from the command's spec models.

    Attributes
    ----------
    label : str
        The parameter/output name the settings come from (for log messages).
    spec : dict
        The parameter or output spec dump carrying the CIF entry fields
        (required/optional entries and entry sets, custom categories, ...).
    entry_sets : dict
        The application's named CIF entry sets
        (see `pyqcrbox.cif_entries.entry_sets_by_name`).
    output_path : str | None
        The filename of the merged/unified output CIF, if fixed by the spec.

    """

    label: str
    spec: dict
    entry_sets: dict = {}
    output_path: str | None = None

    def __str__(self) -> str:
        return f"Cif2CifOptions({self.label=},{self.output_path=})"


class CifDataFileParameter(BaseParameter):
    """Class for handling CIF datafile parameters.

    Attributes
    ----------
    data_file_id : str
        The QCrBox data file ID for the CIF file in the DataManager.

    """

    data_file_id: str
    dtype: str = "QCrBox.cif_data_file"

    # We'll use this to track where the file has been written to disk
    _exported_file_path: str | Path | None

    async def _export_from_data_manager(self, target_dir: str, target_filename: str | None = None) -> str | Path:
        """Export the CIF file from the data manager.

        Parameters
        ----------
        target_dir : str
            The target directory to write the CIF to.
        target_filename : str | None
            The target filename to write to disk. If not provided, the filename
            in the DataManger will be used instead.

        Returns
        -------
        str | Path
            The file path where the file was exported to.

        """
        from pyqcrbox.data_management import DataManager
        from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            data_manager = await container.aget(DataManager)
            try:
                file_path = await data_manager.export_data_file(self.data_file_id, target_dir, target_filename)
            except nats_errors.ObjectNotFoundError as exc:
                if await check_if_id_is_a_dataset(data_manager, self.data_file_id):
                    exc_msg = f"The provided data file ID '{self.data_file_id}' is a dataset ID"
                else:
                    exc_msg = f"No data file was found with the provided data file ID {self.data_file_id}'"
                raise ValueError(exc_msg) from exc

        return file_path

    @log_eel
    async def to_specific_format(self, input_cif_path: str | Path, transform_options: Cif2CifOptions) -> str:
        """Convert the CIF to a specific format.

        At the moment, this does an in-place conversion by overwriting the
        original CIF export.

        Parameters
        ----------
        input_cif_path : str | Path
            The path to the CIF file on the disk, in its original format.
        transform_options : Cif2CifOptions
            Options required for Cif2Cif conversion.

        Returns
        -------
        str
            The file path to the converted CIF file.

        """
        # The conversion needs qcrboxtools (lazily imported inside
        # pyqcrbox.cif_entries) which is not available when we build `qcb`.
        from pyqcrbox.cif_entries import NoEntriesDeclaredError, cif_file_to_specific, input_settings_from_spec

        input_cif_path = Path(input_cif_path)
        if not input_cif_path.exists():
            raise OSError("CIF has not yet been exported to disk")
        output_cif_path = input_cif_path.parent / f"{input_cif_path.stem}-converted.cif"

        try:
            logger.debug(f"Converting CIF to specific format with parameters: {transform_options}")
            settings = input_settings_from_spec(transform_options.spec, transform_options.entry_sets)
            cif_file_to_specific(input_cif_path, output_cif_path, settings)
        except NoEntriesDeclaredError as exc:
            logger.warning(f"{transform_options.label} has no required or optional CIF entries defined: {exc}")
            return str(input_cif_path)
        except (BaseException, Exception) as exc:  # QCrBoxTools uses BaseException as the exception subclass
            exc_msg = f"Unable to translate {transform_options.label} due to exception: {exc}"
            logger.error(exc_msg)
            raise ValueError(exc_msg) from exc

        logger.debug(f"Returning {output_cif_path} from CifDataFileParameter.to_specific_format()")

        return str(output_cif_path)

    @log_eel
    async def to_unified_format(
        self,
        new_cif_path: str,
        merge_options: Cif2CifOptions,
    ) -> str:
        """Merge an original and converted CIF together into a unified CIF format.

        Parameters
        ----------
        new_cif_path : str
            The CIF after it has been converted to a new format.
        cif2cif_options : Cif2CifOptions
            Options required for cif2cif conversion to the unified format.

        """
        # Lazily import module for same reason as in `to_specific_format`
        from pyqcrbox.cif_entries import NoEntriesDeclaredError, cif_file_merge_to_unified, output_settings_from_spec

        if not self._exported_file_path:
            raise ValueError("CIF has not been exported to disk, unable to convert to unified format")

        exported_cif_path = Path(self._exported_file_path)

        # Fetch the original (unified) CIF text straight from the data manager;
        # it is only needed as the merge source, so no disk round trip.
        try:
            original_cif_text = await self._get_text_from_data_manager()
        except (BaseException, Exception) as exc:
            exc_msg = f"Problem merging {str(exported_cif_path)} and {str(new_cif_path)} using {merge_options}: {exc}"
            logger.error(exc_msg)
            raise ValueError(exc_msg) from exc

        if not merge_options.output_path:
            unified_cif_path = str(exported_cif_path.parent / f"{exported_cif_path.stem}.cif")
        else:
            new_name = Path(merge_options.output_path).with_suffix(".cif").name
            unified_cif_path = exported_cif_path.parent / new_name
        logger.debug(
            f"Merging the original CIF and {str(new_cif_path)} together at {unified_cif_path}: {merge_options}"
        )

        try:
            settings = output_settings_from_spec(merge_options.spec, merge_options.entry_sets)
            cif_file_merge_to_unified(
                new_cif_path,
                unified_cif_path,  # this is the output, e.g. the merged original and new
                original_cif_text,
                settings,
            )
        except NoEntriesDeclaredError as exc:
            logger.warning(f"{merge_options.label} has no required or optional CIF entries defined: {exc}")
            return str(new_cif_path)
        except (BaseException, Exception) as exc:
            exc_msg = f"Problem merging the original CIF and {str(new_cif_path)} using {merge_options}: {exc}"
            logger.error(exc_msg)
            raise ValueError(exc_msg) from exc

        logger.debug(f"CIFs merged successfully into file {unified_cif_path=}")
        logger.debug(f"Returning {unified_cif_path} from CifDataFileParameter.to_unified_format()")

        return str(unified_cif_path)

    async def _get_text_from_data_manager(self) -> str:
        """Fetch this CIF's contents from the data manager as text (no disk I/O)."""
        from pyqcrbox.data_management import DataManager
        from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            data_manager = await container.aget(DataManager)
            file_contents = await data_manager.get_data_file_contents(self.data_file_id)
        return file_contents.decode("utf-8")

    @log_eel
    async def prepare_for_execution(
        self, target_dir: str, target_filename: str | None = None, *, cif2cif_options: Cif2CifOptions | None = None
    ) -> str:
        """Prepare the CIF file for command execution.

        This method is used to retrieve the contents of the CIF file from the
        DataManager and to write it to a location on the container's file
        system.

        If the `conversion_parameters` argument is set, then the CIF will be
        converted to the required format as defined in the parameter
        specification.

        Parameters
        ----------
        target_dir : str
            The target directory to write the CIF to.
        target_filename : str | None
            The target filename to write to disk. If not provided, the filename
            in the DataManger will be used instead.
        cif2cif_options : Cif2CifOptions | None
            Parameters required to convert the CIF from one format to another.
            By default, CIFs will not be converted unless this argument is
            provided.

        Returns
        -------
        str
            The file path (within the application container) to the CIF file
            written to disk.

        """
        logger.debug(f"Preparing CIF data file for execution: {self.data_file_id}")

        return_path = self._exported_file_path = await self._export_from_data_manager(target_dir, target_filename)

        if cif2cif_options:
            logger.debug(f"Converting CIF to specific format with params: {cif2cif_options}")
            return_path = await self.to_specific_format(self._exported_file_path, cif2cif_options)

        logger.debug(f"Exported CIF data file to: {self._exported_file_path}")

        return str(return_path)


_custom_dtypes = {
    "QCrBox.data_file": DataFileParameter,
    "QCrBox.cif_data_file": CifDataFileParameter,
}

_known_dtypes = _builtin_dtypes | _custom_dtypes

def get_cif_merge_options(
    command: "BaseCommand", parsed_parameters: dict[str, BaseParameter], application_spec
) -> tuple[CifDataFileParameter | None, Cif2CifOptions | None]:
    """Get the input CIF parameter and the options used to merge the output CIF.

    Parameters
    ----------
    command : BaseCommand
        The BaseCommand object used to launch the command.
    parsed_parameters : dict[str, BaseParameter]
        A list of QCrBox data types which were used to execute the command.
    application_spec : ApplicationSpec
        The application spec providing the named CIF entry sets.

    Returns
    -------
    CifDataFileParameter | None
        The QCrBox data type for the input CIF. This is the CIF which will
        be merged with the output. None if the command has no CIF input.
    Cif2CifOptions | None
        The merge options: the entry settings of the command's
        `QCrBox.output_cif` output spec if declared (including the output
        filename), otherwise the input CIF parameter's settings.

    """
    from pyqcrbox.cif_entries import entry_sets_by_name

    # First, find the first QCrBox.cif_data_file parameter as we will be
    # presuming that this is the input CIF for the command.
    parameter_name, cif_parameter = next(
        ((name, param) for name, param in parsed_parameters.items() if isinstance(param, CifDataFileParameter)),
        (None, None),
    )
    logger.debug(f"Input CIF {parameter_name =} and parsed parameter {cif_parameter =}")

    if cif_parameter is None or parameter_name is None:
        return None, None

    entry_sets = entry_sets_by_name(getattr(application_spec, "cif_entry_sets", []) or [])

    # If the command declares a QCrBox.output_cif output, its entry settings
    # (and fixed filename) drive the merge; otherwise fall back to the input
    # CIF parameter's settings.
    output_cif_spec = command.cmd_spec.output_cif_spec
    if output_cif_spec is not None:
        logger.debug(
            f"QCrBox.output_cif output found for {command.name} ({output_cif_spec.name}), using it for Cif2Cif"
        )
        merge_options = Cif2CifOptions(
            label=output_cif_spec.name,
            spec=output_cif_spec.model_dump(),
            entry_sets=entry_sets,
            output_path=output_cif_spec.resolved_filename,
        )
    else:
        logger.debug(f"No QCrBox.output_cif output found for {command.name}, using input CIF settings for Cif2Cif")
        param_spec = command.cmd_spec.get_parameter_by_name(parameter_name)
        merge_options = Cif2CifOptions(
            label=parameter_name,
            spec=param_spec.model_dump(),
            entry_sets=entry_sets,
            output_path=None,
        )

    return cif_parameter, merge_options


class DeclaredArtifact(QCrBoxPydanticBaseModel):
    """A typed output artifact declared by a command's output spec."""

    kind: str
    filename: str
    required_output: bool = True


class DeclaredOutputs(QCrBoxPydanticBaseModel):
    """The declared output files of a command.

    `primary_cif_filename` is the resolved filename of the command's
    `QCrBox.output_cif` output (if any); `artifacts` are the typed output
    artifacts with their resolved filenames.
    """

    primary_cif_filename: str | None = None
    artifacts: list[DeclaredArtifact] = []


def get_declared_outputs(cmd_spec) -> DeclaredOutputs:
    """Collect the declared output files of a command from its spec.

    Parameters
    ----------
    cmd_spec : BaseCommandSpec
        The command specification whose `outputs` section declares the output
        files (filenames are fixed by the spec).

    Returns
    -------
    DeclaredOutputs
        The output CIF filename (if a `QCrBox.output_cif` output exists) and
        the typed artifacts declared via `QCrBox.output_*` outputs.

    """
    from ..command_spec.output_spec import BaseArtifactOutputSpec, OutputCifSpec

    primary_cif_filename = None
    artifacts = []
    for output_spec in getattr(cmd_spec, "outputs", []) or []:
        if isinstance(output_spec, OutputCifSpec):
            primary_cif_filename = output_spec.resolved_filename
        elif isinstance(output_spec, BaseArtifactOutputSpec):
            artifacts.append(
                DeclaredArtifact(
                    kind=output_spec.artifact_kind,
                    filename=output_spec.resolved_filename,
                    required_output=output_spec.required_output,
                )
            )

    return DeclaredOutputs(primary_cif_filename=primary_cif_filename, artifacts=artifacts)


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
    logger.debug(f"Parsing parameter into QCrBox dtype: {dtype_str=} value={v}")

    if dtype_str not in _known_dtypes:
        raise ValueError(f"Unsupported parameter type: {dtype_str}")

    # Anything like QCrBox.output_cif, QCrBox.output_path will be handled by this
    # as well as primitive python types
    if dtype_str in _builtin_dtypes:
        dtype = _builtin_dtypes[dtype_str]
        return BuiltinParameter(dtype=dtype.__name__, value=dtype(v))

    # This deals with the custom QCrBox types, such as QCrBox.data_file, which
    # are unable to be expressed as a simple primitive type
    return _known_dtypes[dtype_str](**v)


DTypeAsStr = Annotated[constr(max_length=settings.db.max_text_length), BeforeValidator(verify_dtype_is_a_known_type)]
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

    name: str = Field(max_length=settings.db.max_text_length)
    dtype: DTypeAsStr = Field(max_length=settings.db.max_text_length)
    description: str | None = Field(default=None, max_length=settings.db.max_desc_length)
    default_value: constr(max_length=settings.db.max_desc_length) | int | float | bool | None = None  # pyright: ignore[reportInvalidTypeForm]
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
