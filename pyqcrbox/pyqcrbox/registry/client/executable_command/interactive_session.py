import asyncio
import os
from pathlib import Path
from typing import Any

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.registry.client.executable_command import BaseCommand
from pyqcrbox.registry.client.executable_command.cli_command import CLICommand
from pyqcrbox.registry.client.executable_command.error import PrepareCommandFailure, RunCommandFailure, error_dialog_box
from pyqcrbox.registry.client.executable_command.python_callable import PythonCallable
from pyqcrbox.sql_models import InteractiveSessionSpec

from .interactive_session_calculation import InteractiveSessionCalculation

__all__ = ["InteractiveSession"]


class InteractiveSession(BaseCommand):
    def __init__(self, cmd_spec: InteractiveSessionSpec):
        assert cmd_spec.implemented_as == "interactive_session"
        super().__init__(cmd_spec)
        self.prepare_cmd_spec = cmd_spec.interactive_lifecycle.prepare
        self.run_cmd_spec = cmd_spec.interactive_lifecycle.run
        self.finalise_cmd_spec = cmd_spec.interactive_lifecycle.finalise

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
        if not isinstance(command, PythonCallable):
            raise TypeError("Only `PythonCallable` is supported for 'prepare_cmd'")
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
        if not isinstance(command, CLICommand | PythonCallable):
            raise TypeError("Only `CLICommand` or `PythonCallable` are supported for 'run_cmd'")
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
        if not isinstance(command, PythonCallable):
            raise TypeError("Only `PythonCallable` is supported for 'finalise_cmd'")
        logger.debug(f"Executing finalise command in background: {command}")

        session_calculation.finalise_calc = await command.execute_in_background(
            _calculation_id=helpers.generate_calculation_id(),
            _cwd=working_directory,
            **param_values,
        )

    async def prepare_parameters_for_command_execution(
        self, working_dir: str | Path, **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare the parameters to be used by the commands in the session.

        Parameters
        ----------
        working_dir : str | Path
            A path-like object to the working directory for command execution.
        kwargs : dict[str, Any]
            Additional parameter values passed via keyword arguments.

        Returns
        -------
        dict[str, Any]
            A dict with the parameters names as the dict keys and the values of
            the parameters as the dict values.

        """
        # It is mandatory to have a run command defined, but optional to have a prepare or finalise command. So
        # we have to be careful here and add their parameters only if they are defined.
        param_values = self.run_cmd_spec.parameter_default_values
        if self.prepare_cmd_spec:
            param_values = param_values | self.prepare_cmd_spec.parameter_default_values
        if self.finalise_cmd_spec:
            param_values = param_values | self.finalise_cmd_spec.parameter_default_values
        param_values = param_values | kwargs
        param_values = {
            name: await param.prepare_for_execution(target_dir=working_dir) for name, param in param_values.items()
        }

        return param_values

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin_stream: asyncio.StreamWriter | None = None,
        _stdout_stream: asyncio.StreamReader | None = None,
        _stderr_stream: asyncio.StreamReader | None = None,
        _cwd: str | Path | None = None,
        **kwargs,
    ) -> InteractiveSessionCalculation:
        """Launch an interactive session calculation asynchronously.

        This method prepares and executes the prepare, run, and finalise commands (if defined)
        in strict sequence, each as a background task. The method returns immediately with an
        InteractiveSessionCalculation object, allowing the session to be monitored or
        terminated while it is running.

        Parameters
        ----------
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

        working_dir = _cwd or os.getcwd()
        calc_finished_event = anyio.Event()
        param_values = await self.prepare_parameters_for_command_execution(working_dir, **kwargs)

        interactive_session_calc = InteractiveSessionCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            # the following will be set after the task begins
            async_task=None,
            prepare_calc=None,
            run_calc=None,
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
                await self._execute_prepare_command(prepare_cmd, _cwd, interactive_session_calc, **param_values)
            await self._execute_run_command(run_cmd, _cwd, interactive_session_calc, **param_values)
            if finalise_cmd:
                await self._launch_finalise_command(finalise_cmd, _cwd, interactive_session_calc, **param_values)

        interactive_session_calc.background_task = asyncio.create_task(background_task())

        return interactive_session_calc
