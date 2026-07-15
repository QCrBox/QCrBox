import asyncio
from pathlib import Path

import anyio

from pyqcrbox import logger
from pyqcrbox.debug import log_eel
from pyqcrbox.registry.client.executable_command.error import (
    FinaliseCommandFailure,
    PrepareCommandFailure,
    RunCommandFailure,
)
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation
from .python_callable_calculation import PythonCallableCalculation


class InteractiveSessionCalculation(BaseCalculation):
    def __init__(
        self,
        *,
        calculation_id: str,
        calc_finished_event: anyio.Event,
        async_task: asyncio.Task,
        prepare_calc: BaseCalculation | None,
        run_calc: BaseCalculation,
        finalise_calc: BaseCalculation | None,
    ) -> None:
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.prepare_calc = prepare_calc
        self.run_calc = run_calc
        self.finalise_calc = finalise_calc
        self.background_task = async_task
        self.is_closed = False
        self.session_closed_event = anyio.Event()

        # for keeping track of error pop ups
        self._error_dialog_process = None

    @property
    def status(self) -> CalculationStatusEnum:
        if not self.is_closed:
            return CalculationStatusEnum.RUNNING
        elif self.exception_raised:
            return CalculationStatusEnum.FAILED
        else:
            return CalculationStatusEnum.SUCCESSFUL

    @property
    async def stdout(self) -> None:
        return None

    @property
    async def stderr(self) -> None:
        return None

    def _get_returned_output_file(self) -> str | Path | None:
        """Return the finalise command's return value as the session's (primary) output file."""
        if self.finalise_calc is None:
            logger.warning("The interactive session has no finalise calculation, no returned output file")
            return None
        if not isinstance(self.finalise_calc, PythonCallableCalculation):
            raise RuntimeError("Finalise calculation in InteractiveSession not a PythonCallable")

        output_file = self.finalise_calc.return_value
        if not output_file:
            logger.warning("The finalise calculation for the interactive session does not return an output file")
            return None
        return output_file

    @log_eel
    async def wait_until_finished(self) -> None:
        """Asynchronously wait for all calculation phases to complete.

        This method sequentially waits for the 'prepare', 'run', and 'finalise'
        calculation commands to finish, if they are present. It also waits for
        the 'calc_finished' event to be set, indicating that the calculation
        has terminated. Upon successful completion of the 'finalise' phase, it
        imports the output file into the data store and create a dataset from
        it. The method sets the session as closed and signals the session
        closure event.

        Raises
        ------
        AssertionError
            If 'prepare_calc' or 'finalise_calc' are not instances of PythonCallableCalculation.
        FileNotFoundError
            If the output file from the 'finalise' command cannot be found during import.

        """
        if not self.background_task:
            raise RuntimeError("There is no background task(s) to wait to finish")

        # await the background task so we can capture any exceptions which were raised
        # in it and re-raise them to propagate them back up
        try:
            await self.background_task
        except Exception as exc:
            self.exception = exc
            raise

        # We have to wait for the "calc_finished" event to be set, which only can happen
        # when we try and close the interactive session. If we didn't wait then due to
        # how this is set up, we would run the finalise command before we've finished
        # interacting with the main run command. If we did everything in the foreground,
        # then we wouldn't have to wait because the run_calc would be blocking.
        logger.debug("Waiting for 'calc_finished' event to be set upon calculation termination")
        await self.calc_finished_event.wait()

    @log_eel
    async def terminate(self) -> None:
        """Terminate the interactive session.

        If the calculation is already finished, logs the session state and
        returns. Otherwise, it signals the calculation to finish, waits for
        session closure.
        """
        self.terminated_manually = True
        if self.calc_finished_event.is_set():
            if self.is_closed:
                logger.warning(f"Interactive session {self} already closed")
            else:
                logger.warning(f"Interactive session {self} is already being closed.")
            return
        logger.debug(f"Closing interactive session {self}")

        # Terminate the prepare and run calculation if still running. Then we need to set the 'calc_finished'
        # event which *should* cause run_calc.wait_until_finished() to exit. If this flag isn't set, then
        # execution will hang
        if self.prepare_calc and self.prepare_calc.status == CalculationStatusEnum.RUNNING:
            await self.prepare_calc.terminate()

        if self.run_calc.status == CalculationStatusEnum.RUNNING:
            await self.run_calc.terminate()

        self.run_calc.calc_finished_event.set()

        # When the run calc is finished, this flag is used to communicate with the interactive
        # session wait_until_finished() that the finalise command can be run
        self.calc_finished_event.set()

        # Keep waiting until the finalise calculation has finished and the output has been added to
        # the data store
        await self.session_closed_event.wait()

        # Close any error dialog we have open, otherwise it gets confusing
        if self._error_dialog_process:
            self._error_dialog_process.terminate()
            self._error_dialog_process.join()

    @log_eel
    def get_error_message(self) -> str:
        """Get the last error message for this interactive session.

        Returns
        -------
        str
            The error message returned. This could be an empty string.

        """
        if self.exception_raised:
            if isinstance(self.exception_raised, PrepareCommandFailure):
                error_msg = f"Prepare step failed: {self.exception_raised.original_exception}"
            elif isinstance(self.exception_raised, RunCommandFailure):
                error_msg = f"Run step failed: {self.exception_raised.original_exception}"
            elif isinstance(self.exception_raised, FinaliseCommandFailure):
                error_msg = f"Fianalise step failed: {self.exception_raised.original_exception}"
            else:
                error_msg = f"Command failed: {self.exception_raised}"
        else:
            error_msg = ""

        return error_msg
