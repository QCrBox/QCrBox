import asyncio
import os
from pathlib import Path
from typing import Any

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.registry.client.executable_command import BaseCommand
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
            async_task=None,  # the following will be set after the task begins
            prepare_calc=None,
            run_calc=None,
            finalise_calc=None,
        )

        run_cmd = ExecutableCommand(self.run_cmd_spec)
        prepare_cmd = ExecutableCommand(self.prepare_cmd_spec) if self.prepare_cmd_spec else None
        finalise_cmd = ExecutableCommand(self.finalise_cmd_spec) if self.finalise_cmd_spec else None

        # Bit of a terrible hack to do this, but it seems to be OK. Essentially we are
        # creating a task to run which we then use anyio.create_task to run asynchronously
        # in the background. By doing this we can return an InteractiveSessionCalculation
        # before the run_calc has finished and thus should be able to terminate the
        # calculation.
        async def session_tasks():
            nonlocal run_cmd, prepare_cmd, finalise_cmd

            # Run prepare command, wait for it to finish, and handle errors
            if prepare_cmd:
                if not isinstance(prepare_cmd, PythonCallable):
                    raise TypeError("Only `PythonCallable` is supported for 'prepare_cmd'")
                logger.debug(f"Executing prepare command in background and waiting for it to finish: {prepare_cmd}")
                interactive_session_calc.prepare_calc = await prepare_cmd.execute_in_background(
                    _calculation_id=helpers.generate_calculation_id(),
                    _cwd=_cwd,
                    **param_values,
                )
                await interactive_session_calc.prepare_calc.wait_until_finished()
                if interactive_session_calc.prepare_calc.exception:
                    calc_status = interactive_session_calc.prepare_calc.status
                    raised_exception = interactive_session_calc.prepare_calc.exception
                    logger.error(
                        f"Exception raised by prepare_cmd (calc status {calc_status}): {raised_exception}",
                    )
                    error_dialog_box(f"An error occurred in the prepare command: {raised_exception}")
                    raise PrepareCommandFailure(
                        "Prepare command failed"
                    ) from interactive_session_calc.prepare_calc.exception
                logger.debug("Prepare command has finished executing")

            # Run the main interactive command (run command), wait for it to finish
            # and handle errors
            logger.debug(f"Executing run command in background and waiting for it to finish: {run_cmd}")
            interactive_session_calc.run_calc = await run_cmd.execute_in_background(
                _calculation_id=helpers.generate_calculation_id(),
                _cwd=_cwd,
                **param_values,
            )
            await interactive_session_calc.run_calc.wait_until_finished()
            if interactive_session_calc.run_calc.exception:
                calc_status = interactive_session_calc.run_calc.status
                raised_exception = interactive_session_calc.run_calc.exception
                logger.error(
                    f"Exception raised by run_cmd (calc status {calc_status}): {raised_exception}",
                )
                error_dialog_box(f"An error occurred in the run command: {raised_exception}")
                raise RunCommandFailure("Run command failed") from interactive_session_calc.run_calc.exception
            logger.debug("Run command has finished executing")

            # Launch finalise command, but don't wait for it to finish. We wait for this
            # to finish in the interactive session calculation
            if finalise_cmd:
                if not isinstance(finalise_cmd, PythonCallable):
                    raise TypeError("Only `PythonCallable` is supported for 'finalise_cmd'")
                logger.debug(f"Executing finalise command in background: {finalise_cmd}")
                interactive_session_calc.finalise_calc = await finalise_cmd.execute_in_background(
                    _calculation_id=helpers.generate_calculation_id(),
                    _cwd=_cwd,
                    **param_values,
                )

        interactive_session_calc.background_task = asyncio.create_task(session_tasks())

        return interactive_session_calc
