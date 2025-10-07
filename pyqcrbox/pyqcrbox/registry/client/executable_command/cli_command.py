import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models import CLICommandSpec
from pyqcrbox.sql_models.application_spec import ApplicationSpec
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import BaseParameter

from .base_command import BaseCommand
from .cli_command_calculation import CLICmdCalculation

__all__ = ["CLICommand"]


class QCrBoxCmdArgumentMismatch(Exception):
    """Exception raised when command arguments do not match the expected pattern."""

    pass


class CLICommand(BaseCommand):
    """Command class for executing CLI commands as background calculations.

    Parameters
    ----------
    cmd_spec : CLICommandSpec
        The command specification for the CLI command.

    """

    def __init__(self, cmd_spec: CLICommandSpec):
        assert cmd_spec.implemented_as == "cli_command"
        super().__init__(cmd_spec)
        self.call_pattern = cmd_spec.call_pattern
        self.call_pattern_parameter_names = list(set(re.findall("{(.*?)}", self.call_pattern)))
        self.parameter_names = [p.name for p in cmd_spec.parameters]
        logger.warning(
            "TODO: validate that the call_pattern_parameter_names are a subset(?) of the yaml spec parameters"
        )

        self.proc: asyncio.subprocess.Process | None = None

    def __repr__(self):
        """Return a string representation of the CLICommand instance.

        Returns
        -------
        str
            String representation of the object.

        """
        return f"<{self.__class__.__name__}: '{str(self)}'>"

    def __str__(self):
        """Return the call pattern string for the CLI command.

        Returns
        -------
        str
            The call pattern string.

        """
        return self.call_pattern

    async def prepare_params(
        self,
        application_spec: ApplicationSpec,
        command_arguments: dict[str, str],
        working_dir: str | Path,
    ) -> tuple[dict[str, BaseParameter], dict[str, Any]]:
        """Prepare the parameters required for command execution.

        If there are optional arguments for the command which are not included
        in the `command_arguments` dictionary, then the value for these arguments
        will be taken from the command specification used to initialise
        the BaseCommand class.

        Parameters
        ----------
        application_spec : ApplicationSpec
            The application specification for application the command belongs to.
        command_arguments : dict[str, str]
            The names and values of the parameters for the command in a dict
            mapping of { param_name: param_value } where `param_value` will be
            parsed from an string representation.
        working_dir : str
            The working directory to potentially write any files to.

        Returns
        -------
        dict[str, BaseParameter]
            A mapping of argument/parameter name to a BaseParameter derived
            class which is used for command execution.
        dict[str, Any]
            A mapping of parameter name to parameter values, which should be
            passed to a command's execute_in_background method.

        """
        parsed_params = self._parse_params_into_dtype(command_arguments)

        # Combine parsed_params with default values in the command spec, this is
        # only required for optional arguments
        parsed_params = self.cmd_spec.parameter_default_values | parsed_params

        prepared_params = await self._prepare_params_for_execution(parsed_params, application_spec, str(working_dir))

        return parsed_params, prepared_params

    async def bind(self, working_dir: str | Path, **param_values):
        """Bind parameter values to the call pattern for the CLI command.

        Parameters
        ----------
        working_dir : str
            The working directory for the command.
        **param_values
            Parameter values to bind to the call pattern.

        Returns
        -------
        str
            The formatted command string with bound arguments.

        """
        return self.call_pattern.format(**param_values)

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin=None,
        _stdout=subprocess.PIPE,
        _stderr=subprocess.PIPE,
        _cwd=None,
        **kwargs,
    ) -> CLICmdCalculation:
        """Execute the CLI command asynchronously in the background.

        Parameters
        ----------
        _calculation_id : str
            Unique identifier for the calculation instance.
        _stdin : Any, optional
            Standard input stream or data (default is None).
        _stdout : Any, optional
            Standard output stream or handler (default is subprocess.PIPE).
        _stderr : Any, optional
            Standard error stream or handler (default is subprocess.PIPE).
        _cwd : str, optional
            Working directory for command execution (default is None).
        **kwargs
            Additional keyword arguments for command execution.

        Returns
        -------
        CLICmdCalculation
            An instance representing the background calculation.

        """
        calc_finished_event = anyio.Event()

        working_dir = _cwd or os.getcwd()
        param_values = {k: kwargs[k] for k in self.parameter_names if k in kwargs}

        try:
            cmd_with_bound_args = await self.bind(working_dir, **param_values)
        except KeyError as exc:
            raise QCrBoxCmdArgumentMismatch(exc.args[0]) from None

        self.proc = await asyncio.create_subprocess_shell(
            cmd_with_bound_args, stdin=_stdin, stdout=_stdout, stderr=_stderr, cwd=working_dir, preexec_fn=os.setsid
        )

        return CLICmdCalculation(self.proc, calculation_id=_calculation_id, calc_finished_event=calc_finished_event)
