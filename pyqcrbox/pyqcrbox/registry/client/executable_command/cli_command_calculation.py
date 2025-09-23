# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import signal

import anyio

from pyqcrbox import logger
from pyqcrbox.data_management import DataManager
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation


class CLICmdCalculation(BaseCalculation):
    """Calculation class for tracking the status of a CLI command execution.

    Parameters
    ----------
    proc : asyncio.subprocess.Process
        The process object for the running CLI command.
    calculation_id : str
        Unique identifier for the calculation.
    calc_finished_event : anyio.Event
        Event that signals when the calculation is finished.

    """

    def __init__(self, proc: asyncio.subprocess.Process, calculation_id: str, calc_finished_event: anyio.Event):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.proc = proc
        self.calculation_id = calculation_id
        self._stdout = ""
        self._stderr = ""
        self._terminated = False
        self.retrieved_stdout_stderr = False
        self.calc_finished_event = calc_finished_event

    async def save_output_to_data_manager(self, data_manager: DataManager) -> None:
        """Save the output of the CLI Command to the Data File Manager.

        This is a dummy method, as getting data from a CLI command is not
        supported.

        Parameters
        ----------
        data_manager : DataManager
            An instance of the DataFile Manager.

        """
        logger.warning("Saving the output from a CLI Command is not supported!")

    async def wait_until_finished(self):
        """Wait until the calculation is finished."""
        await self.proc.wait()

        # Check the return status of the CLI command once the process has either
        # finished naturally or if it was terminated early
        if self.status == CalculationStatusEnum.FAILED:
            logger.error(
                f"CLI Command failed:\nStdout:\n\n{await self.stdout}\n\nStderr:\n\n{await self.stderr}",
            )
            self.exception = RuntimeError(
                f"CLI command failed with return code {self.proc.returncode}: {await self.stderr}"
            )

        self.calc_finished_event.set()

    @property
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """
        # Short-circuit to return SUCCESS when user terminated command
        if self._terminated:
            return CalculationStatusEnum.SUCCESSFUL

        # Match status when command is still running, or when it exited normally
        match self.proc.returncode:
            case None:
                status = CalculationStatusEnum.RUNNING
            case 0:
                status = CalculationStatusEnum.SUCCESSFUL
            case _:
                status = CalculationStatusEnum.FAILED

        return status

    def _get_status_details_extra_info(self):
        """Get additional information for status details.

        Returns
        -------
        dict
            Extra information as a dictionary.

        """
        return {"returncode": self.returncode}

    @property
    def returncode(self) -> int | None:
        """Get the return code of the CLI command process.

        Returns
        -------
        int | None
            The return code of the process. If the process is still running, the
            return code will be None.

        """
        return self.proc.returncode

    @property
    async def stdout(self) -> str:
        """Retrieve the standard output of the calculation.

        Returns
        -------
        str
            The standard output of the calculation.

        """
        await self.retrieve_stdout_stderr()
        return self._stdout

    @property
    async def stderr(self) -> str:
        """Retrieve the standard error of the calculation.

        Returns
        -------
        str
            The standard error of the calculation.

        """
        await self.retrieve_stdout_stderr()
        return self._stderr

    async def retrieve_stdout_stderr(self):
        """Retrieve and decode the standard output and error from the process."""
        if self.status != CalculationStatusEnum.RUNNING and not self.retrieved_stdout_stderr:
            stdout, stderr = await self.proc.communicate()
            self._stdout = stdout.decode()
            self._stderr = stderr.decode()
            self.retrieved_stdout_stderr = True

    async def terminate(self):
        """Terminate the calculation.

        Once the process has been terminated, self.proc.wait() will no longer be
        blocking. This means that in `self.wait_until_finished()`, the return code
        of the process will be used to determine if it failed or not. This is why
        self._terminated exists. It allows us to short-circuit looking up the
        process status to return SUCCESSFUL if the user chooses to terminate. Before
        doing this, the return code may by -15 (SIGTERM) which would (falsely)
        flag the process as failing.
        """
        if self.proc:
            os.killpg(self.proc.pid, signal.SIGTERM)
            self._terminated = True
            logger.debug(f"Terminated process for calculation {self!r}")
        else:
            logger.debug(f"No process running for calculation {self!r} - nothing to terminate.")
