# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import signal

import anyio

from pyqcrbox import logger
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
        self.retrieved_stdout_stderr = False
        self.calc_finished_event = calc_finished_event

    async def wait_until_finished(self):
        """Wait until the calculation is finished."""
        # await self.proc.wait()
        await self.calc_finished_event.wait()
        if self.status == CalculationStatusEnum.FAILED:
            logger.error(f"CLI Command failed:\nStdout:\n\n{await self.stdout}\n\nStderr:\n\n{await self.stderr}")

    @property
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """
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
    def returncode(self) -> int:
        """Get the return code of the CLI command process.

        Returns
        -------
        int
            The return code of the process.

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
        """Terminate the calculation."""
        if self.proc:
            os.killpg(self.proc.pid, signal.SIGTERM)
            logger.debug(f"Terminated process for calculation {self!r}")
        else:
            logger.debug(f"No process running for calculation {self!r} - nothing to terminate.")
