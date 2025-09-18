from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyqcrbox import logger
from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.sql_models.application_spec import ApplicationSpec
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import (
    BaseParameter,
    Cif2CifOptions,
    CifDataFileParameter,
    parse_parameter_as_its_dtype,
)

if TYPE_CHECKING:
    from pyqcrbox.sql_models import CommandSpecDiscriminatedUnion

__all__ = ["BaseCommand"]


class BaseCommand(metaclass=ABCMeta):
    """Abstract base class for command execution.

    Parameters
    ----------
    cmd_spec : CommandSpecDiscriminatedUnion
        The command specification object describing the command to execute.

    """

    def __init__(self, cmd_spec: "CommandSpecDiscriminatedUnion"):
        self.cmd_spec = cmd_spec
        self.type = cmd_spec.implemented_as

    def __repr__(self):
        """Return a string representation of the command instance.

        Returns
        -------
        str
            String representation of the object.

        """
        clsname = self.__class__.__name__
        return f"<{clsname}: {self.cmd_spec.name!r}>"

    # TODO
    # The fact that a parsed parameter can be BaseParameter or CifDataFileParameter
    # is unsatisfying and warrants changing

    def _parse_params_into_dtype(
        self, command_arguments: dict[str, Any]
    ) -> dict[str, BaseParameter | CifDataFileParameter]:
        """Convert a command arguments into a BaseParameter derived classes.

        Create a mapping of the parameters, where each item in the output
        dictionary will be a QCrBox specific representation of the data type of
        the parameter, e.g. see pyqcrbox.sql_models.parameter_spec.

        This method takes in an argument and the provided user input value and
        instantiates a class which is used during command execution.

        Parameters
        ----------
        command_arguments : dict[str, Any]
            A mapping of a command argument names and the provided value to be
            converted into a BaseParameter class.

        Returns
        -------
        dict[str, BaseParameter]
            A mapping of argument/parameter name to a BaseParameter derived
            class which is used for command execution.

        """
        logger.debug(
            f"Parsing command arguments/parameters into QCrBox representation for command '{self.cmd_spec.name}'"
        )

        parsed_arguments = {}
        for param_name, param_value in command_arguments.items():
            param_spec = self.cmd_spec.get_parameter_by_name(param_name)
            parsed_arguments[param_name] = parse_parameter_as_its_dtype(param_value, param_spec.dtype)

        logger.debug(f"Parsed arguments for command '{self.cmd_spec.name}': {parsed_arguments}")

        return parsed_arguments

    async def _prepare_params_for_execution(
        self,
        parsed_params: dict[str, BaseParameter | CifDataFileParameter],
        application_spec: ApplicationSpec,
        working_dir: str,
    ) -> dict[str, Any]:
        """Prepare parameters for command execution.

        Create a mapping of the parameters, where each item in the output
        dictionary corresponds to the name of the parameter and the value which
        will be passed to the command function.

        Parameters
        ----------
        parsed_params : dict[str, BaseParameter | CifDataFileParameter]
            A mapping of argument/parameter name to a BaseParameter derived
            class which is used for command execution.
        application_spec : ApplicationSpec
            The application specification of the application for the command
            that the parameters belong to.
        working_dir : str
            The working directory where the command will execute.

        Returns
        -------
        dict[str, Any]
            A mapping of parameter names to the value which will be passed to
            the command.

        """
        logger.debug(f"Preparing command arguments/parameters for execution for command '{self.cmd_spec.name}'")

        prepared_params = {}
        for param_name, parsed_param in parsed_params.items():
            # CifDataFileParameters can be converted between different CIF formats
            # TODO: this should be moved into CifDataFileParameter
            if isinstance(parsed_param, CifDataFileParameter):
                cif2cif_options = Cif2CifOptions(
                    application_yaml=str(application_spec.yaml_file_path),
                    command_name=self.cmd_spec.name,
                    parameter_name=param_name,
                )
                prepared_params[param_name] = await parsed_param.prepare_for_execution(
                    target_dir=working_dir, cif2cif_options=cif2cif_options
                )
            else:
                prepared_params[param_name] = await parsed_param.prepare_for_execution(target_dir=working_dir)

        logger.debug(f"Prepared arguments for '{self.cmd_spec.name}': {prepared_params}")

        return prepared_params

    @abstractmethod
    async def prepare_params(
        self,
        application_spec: ApplicationSpec,
        command_arguments: dict[str, BaseParameter | CifDataFileParameter],
        working_dir: str | Path,
    ) -> dict[str, Any]:
        """Prepare the parameters required for command execution.

        If there are optional arguments for the command which are not included
        in the `command_arguments` dictionary, then the value for these arguments
        will be taken from the command specification used to initialise
        the BaseCommand class.

        Parameters
        ----------
        application_spec : ApplicationSpec
            The application specification for application the command belongs to.
        command_arguments : dict[str, BaseParameter]
            The names and values of the parameters for the command in a dict
            mapping of { param_name: param_value }
        working_dir : str
            The working directory to potentially write any files to.

        """

    @abstractmethod
    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin: Any | None = None,
        _stdout: Any | None = None,
        _stderr: Any | None = None,
        _cwd: str | Path | None = None,
        **kwargs: dict[str, Any],
    ) -> BaseCalculation:
        """Execute the command asynchronously in the background.

        Parameters
        ----------
        _calculation_id : str
            Unique identifier for the calculation instance.
        _stdin : Any, optional
            Standard input stream or data (default is None).
        _stdout : Any, optional
            Standard output stream or handler (default is None).
        _stderr : Any, optional
            Standard error stream or handler (default is None).
        _cwd : str or Path, optional
            Working directory for command execution (default is None).
        **kwargs
            Additional keyword arguments for command execution.

        Returns
        -------
        BaseCalculation
            An instance representing the background calculation.

        """
