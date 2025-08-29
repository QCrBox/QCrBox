import asyncio
import os
from pathlib import Path
from typing import Any

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.data_management.data_manager import DataManager
from pyqcrbox.msg_specs.msg_types.client_side.command_execution_request import CommandExecutionRequestNATS
from pyqcrbox.registry.client.executable_command import BaseCommand
from pyqcrbox.registry.client.executable_command.cli_command import CLICommand
from pyqcrbox.registry.client.executable_command.error import PrepareCommandFailure, RunCommandFailure, error_dialog_box
from pyqcrbox.registry.client.executable_command.python_callable import PythonCallable
from pyqcrbox.sql_models import InteractiveSessionSpec
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfo
from pyqcrbox.sql_models.parameter_spec import parse_parameter_as_its_dtype
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import BaseParameter, CifDataFileParameter

from .interactive_session_calculation import InteractiveSessionCalculation

__all__ = ["InteractiveSession"]


class InteractiveSession(BaseCommand):
    def __init__(self, cmd_spec: InteractiveSessionSpec):
        assert cmd_spec.implemented_as == "interactive_session"
        super().__init__(cmd_spec)

        # specifications for interactive commands
        self.prepare_cmd_spec = cmd_spec.interactive_lifecycle.prepare
        self.run_cmd_spec = cmd_spec.interactive_lifecycle.run
        self.finalise_cmd_spec = cmd_spec.interactive_lifecycle.finalise
        # placeholders for interactive command objects
        self._prepare_cmd = None
        self._run_cmd = None
        self._finalise_cmd = None

    @staticmethod
    async def _execute_prepare_command(
        command: PythonCallable,
        working_directory: str | Path | None,
        session_calculation: InteractiveSessionCalculation,
        **param_values: dict[str, Any],
    ) -> None:
        """Launch and execute the prepare command for this interactive session.

        For the prepare command, only PythonCallable's are supported. This will
        launch the prepare command in the background and wait for execution to
        finish. The calculation object returned for the command is stored
        in the calculation object for the interactive session passed to this
        function.

        Parameters
        ----------
        command : PythonCallable
            A PythonCallable object containing the command instructions.
        working_directory : str | Path | None
            The working directory for the command to run in.
        session_calculation : InteractiveSessionCalculation
            The calculation object for the interactive session.
        param_values : dict[str, Any]
            Any keyword arguments which will be passed as parameters for the
            command to run.

        """
        logger.debug(f"Executing prepare command in background and waiting for it to finish: {command}")

        session_calculation.prepare_calc = await command.execute_in_background(
            _calculation_id=helpers.generate_calculation_id(),
            _cwd=working_directory,
            _num_processes=1,
            **param_values,
        )
        await session_calculation.prepare_calc.wait_until_finished()

        if session_calculation.prepare_calc.exception_raised:
            exception = session_calculation.prepare_calc.exception_raised
            session_calculation._error_dialog_process = error_dialog_box(
                f"An error occurred in the prepare command: {exception}"
            )
            # PrepareCommandFailure requires the original exception for better error
            # reporting upstream
            raise PrepareCommandFailure(
                "Prepare command failed", session_calculation.prepare_calc.exception_raised
            ) from exception

        logger.debug("Prepare command has finished")

    @staticmethod
    async def _execute_run_command(
        command: CLICommand | PythonCallable,
        working_directory: str | Path | None,
        session_calculation: InteractiveSessionCalculation,
        **param_values: dict[str, Any],
    ) -> None:
        """Launch and execute the run command for this interactive session.

        For the run command, CLICommand's and PythonCallable's are supported.
        This will launch the runcommand in the background and wait for execution
        to finish. The calculation object returned for the command is stored
        in the calculation object for the interactive session passed to this
        function.

        Parameters
        ----------
        command : CLICommand | PythonCallable
            A CLICommand or PythonCallable object containing the command
            instructions.
        working_directory : str | Path | None
            The working directory for the command to run in.
        session_calculation : InteractiveSessionCalculation
            The calculation object for the interactive session.
        param_values : dict[str, Any]
            Any keyword arguments which will be passed as parameters for the
            command to run.

        """
        logger.debug(f"Executing run command in background and waiting for it to finish: {command}")

        session_calculation.run_calc = await command.execute_in_background(
            _calculation_id=helpers.generate_calculation_id(),
            _cwd=working_directory,
            **param_values,
        )
        await session_calculation.run_calc.wait_until_finished()

        if session_calculation.run_calc.exception_raised:
            exception = session_calculation.run_calc.exception_raised
            session_calculation._error_dialog_process = error_dialog_box(
                f"An error occurred in the run command: {exception}"
            )
            # RunCommandFailure requires the original exception for better error
            # reporting upstream
            raise RunCommandFailure("Run command failed", exception) from exception

        logger.debug("Run command has finished")

    @staticmethod
    async def _launch_finalise_command(
        command: PythonCallable,
        working_directory: str | Path | None,
        session_calculation: InteractiveSessionCalculation,
        **param_values: dict[str, Any],
    ):
        """Launch the finalise command for this interactive session.

        For the finalise command, only PythonCallable's are supported. This will
        launch the finalise command in the background and DOES NOT wait for it
        to finish. The calculation object returned for the command is stored
        in the calculation object for the interactive session passed to this
        function.

        Parameters
        ----------
        command : CLICommand | PythonCallable
            A CLICommand or PythonCallable object containing the command
            instructions.
        working_directory : str | Path | None
            The working directory for the command to run in.
        session_calculation : InteractiveSessionCalculation
            The calculation object for the interactive session.
        param_values : dict[str, Any]
            Any keyword arguments which will be passed as parameters for the
            command to run.

        """
        logger.debug(f"Executing finalise command in background: {command}")

        session_calculation.finalise_calc = await command.execute_in_background(
            _calculation_id=helpers.generate_calculation_id(),
            _cwd=working_directory,
            **param_values,
        )

    async def prepare_params(
        self, working_dir: str | Path, command_arguments: dict[str, BaseParameter]
    ) -> dict[str, Any]:
        """Prepare and command parameters for execution for an interactive session.

        This method parses the provided command arguments  then merges them with
        any default values from the run, prepare, and finalise command specs.

        Parameters
        ----------
        working_dir : str | Path
            The working directory in which to prepare parameters, e.g. where files
            will be written to.
        command_arguments : dict[str, BaseParameter]
            A dictionary mapping parameter names to their provided values.

        Returns
        -------
        dict[str, Any]
            A dictionary mapping parameter names to their prepared values, ready for
            use in command execution.

        """
        # Create a mapping of the parameters, each item in the dict will be a QCrBox
        # object representation of the data type of that parameter -- see pyqcrbox.sql_models.parameter_spec
        parsed_params = {}
        for param_name, param_value in command_arguments.items():
            param_spec = self.cmd_spec.get_parameter_by_name(param_name)
            parsed_params[param_name] = parse_parameter_as_its_dtype(param_value, param_spec.dtype)

        # Now we have to create a mapping of the parameter names to the value of
        # the parameters. These will either by default values or be passed via the NATS
        # message to invoke the command (and then "prepared" for execution)
        param_values = self.run_cmd_spec.parameter_default_values | parsed_params
        if self.prepare_cmd_spec:
            param_values = param_values | self.prepare_cmd_spec.parameter_default_values
        if self.finalise_cmd_spec:
            param_values = param_values | self.finalise_cmd_spec.parameter_default_values

        # TODO: this is far from ideal
        parameters = {}
        for name, param in param_values.items():
            if isinstance(param, CifDataFileParameter):
                parameters[name] = await param.prepare_for_execution(
                    target_dir=str(working_dir),
                    to_specific_cif_format=True,
                    conversion_arguments={
                        "application_yaml_path": os.getenv("QCRBOX__APPLICATION__YAML"),
                        "command_name": self.cmd_spec.name,
                        "parameter_name": name,
                    },
                )
            else:
                parameters[name] = await param.prepare_for_execution(target_dir=str(working_dir))

        return parameters

    async def add_to_interactive_session_database(
        self,
        data_manager: DataManager,
        execute_request: CommandExecutionRequestNATS,
        executing_client_address: str,
    ) -> None:
        """Add this interactive session to the database.

        This adds an InteractiveSessionInfo object to the "interactive_sessions"
        bucket in the data manager.

        Parameters
        ----------
        data_manager: DataManager
            An instance of the DataManager.
        execute_request : CommandExecutionRequestNATS
            The execution request message, containing data about the calculation.
        executing_client_address : str
            The NATS address of the client executing the command.

        """
        session_info = InteractiveSessionInfo(
            session_id=execute_request.calculation_id,
            client_private_inbox=executing_client_address,
            cmd_execution_request=execute_request,
        )
        await data_manager.store_interactive_session(session_info)

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin_stream: asyncio.StreamWriter | None = None,
        _stdout_stream: asyncio.StreamReader | None = None,
        _stderr_stream: asyncio.StreamReader | None = None,
        _cwd: str | Path | None = None,
        **kwargs: dict[str, Any],
    ) -> InteractiveSessionCalculation:
        """Launch an interactive session calculation asynchronously.

        This method prepares and executes the prepare, run, and finalise commands (if defined)
        in strict sequence, each as a background task. The method returns immediately with an
        InteractiveSessionCalculation object, allowing the session to be monitored or
        terminated while it is running.

        Parameters
        ----------
        command_arguments : dict
            A dict containing the names of the arguments required for the function.
        _calculation_id : str
            The unique identifier for the interactive session calculation.
        _stdin_stream : asyncio.StreamWriter | None
            A stream for inputting stdin for commands (not currently used).
        _stdout_stream : asyncio.StreamReader | None
            A stream for outputting stdout for the commands (not currently used).
        _stderr_stream : asyncio.StreamReader  None
            A stream for outputting stderr for the commands (not currently used).
        _cwd : str | Path | None
            The working directory in which to execute the commands. Defaults to the current directory.
        **kwargs
            Additional keyword arguments to be passed as parameters to the commands.

        Returns
        -------
        InteractiveSessionCalculation
            An object representing the interactive session calculation, which can be monitored
            or terminated while the session is running.

        """
        from .executable_command import ExecutableCommand

        interactive_session_calc = InteractiveSessionCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=anyio.Event(),
            # the following will be set after the task begins
            async_task=None,  # type: ignore
            prepare_calc=None,
            run_calc=None,  # type: ignore
            finalise_calc=None,
        )

        run_cmd = ExecutableCommand(self.run_cmd_spec)
        prepare_cmd = ExecutableCommand(self.prepare_cmd_spec) if self.prepare_cmd_spec else None
        finalise_cmd = ExecutableCommand(self.finalise_cmd_spec) if self.finalise_cmd_spec else None

        # Create a task to run which will use asyncio.create_task to run asynchronously
        # in the background. By doing this we can return an InteractiveSessionCalculation
        # before the run_calc has finished and thus should be able to terminate the
        # calculation.
        async def background_task():
            nonlocal run_cmd, prepare_cmd, finalise_cmd

            if prepare_cmd:
                if not isinstance(prepare_cmd, PythonCallable):
                    raise TypeError("`prepare` command for interactive session must be PythonCallable")
                await self._execute_prepare_command(prepare_cmd, _cwd, interactive_session_calc, **kwargs)

            if not isinstance(run_cmd, PythonCallable | CLICommand):
                raise TypeError("`run_cmd` for interactive session must be PythonCallable or CLICommand")
            await self._execute_run_command(run_cmd, _cwd, interactive_session_calc, **kwargs)

            if finalise_cmd:
                if not isinstance(finalise_cmd, PythonCallable):
                    raise TypeError("`finalise` command for interactive session must be PythonCallable")
                await self._launch_finalise_command(finalise_cmd, _cwd, interactive_session_calc, **kwargs)

        interactive_session_calc.background_task = asyncio.create_task(background_task())

        return interactive_session_calc
