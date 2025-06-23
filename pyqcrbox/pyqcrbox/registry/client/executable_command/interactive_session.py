import asyncio
import os
from pathlib import Path
from typing import Any

import anyio

from pyqcrbox import helpers, logger
from pyqcrbox.debug import eel_logging
from pyqcrbox.registry.client.executable_command import BaseCommand
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

    @eel_logging
    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin_stream: asyncio.StreamWriter | None = None,
        _stdout_stream: asyncio.StreamReader | None = None,
        _stderr_stream: asyncio.StreamReader | None = None,
        _cwd: str | Path = None,
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
        working_dir = _cwd or os.getcwd()
        calc_finished_event = anyio.Event()
        param_values = await self.prepare_parameters_for_command_execution(working_dir, **kwargs)
        calculation = InteractiveSessionCalculation(
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
            prepare_calc=None,  # the following three will be set after the task begins
            run_calc=None,
            finalise_calc=None,
        )

        # Bit of a terrible hack to do this, but it seems to be OK. Essentially we are
        # creating a task to run which we then use anyio.create_task to run asynchronously
        # in the background. By doing this we can return an InteractiveSessionCalculation
        # before the run_calc has finished and thus should be able to terminate the
        # calculation.
        async def session_tasks():
            from .executable_command import ExecutableCommand

            if self.prepare_cmd_spec:
                prepare_cmd = ExecutableCommand(self.prepare_cmd_spec)
                assert isinstance(
                    prepare_cmd, PythonCallable
                ), "Only Python callables are supported for 'prepare_command' at the moment"
                prepare_calc_id = helpers.generate_calculation_id()
                logger.debug("Running 'prepare' command")
                prepare_calc = await prepare_cmd.execute_in_background(
                    _calculation_id=prepare_calc_id, _cwd=_cwd, **param_values
                )
                calculation.prepare_calc = prepare_calc
                await prepare_calc.wait_until_finished()
            else:
                prepare_calc = None

            run_cmd = ExecutableCommand(self.run_cmd_spec)
            run_calc_id = helpers.generate_calculation_id()
            logger.debug("Running the main interactive command")
            run_calc = await run_cmd.execute_in_background(_calculation_id=run_calc_id, _cwd=_cwd, **param_values)
            calculation.run_calc = run_calc
            await run_calc.wait_until_finished()

            if self.finalise_cmd_spec:
                finalise_cmd = ExecutableCommand(self.finalise_cmd_spec)
                assert isinstance(
                    finalise_cmd, PythonCallable
                ), "Only Python callables are supported for 'finalise_command' at the moment"
                finalise_calc_id = helpers.generate_calculation_id()
                logger.debug("Running the 'finalise' command")
                finalise_calc = await finalise_cmd.execute_in_background(
                    _calculation_id=finalise_calc_id, _cwd=_cwd, **param_values
                )
                calculation.finalise_calc = finalise_calc
            else:
                finalise_calc = None

        asyncio.create_task(session_tasks())

        return calculation

    @eel_logging
    def terminate(self) -> None:
        """Terminate the interactive session command."""
        raise NotImplementedError("TODO: implement terminate() for interactive commands")
