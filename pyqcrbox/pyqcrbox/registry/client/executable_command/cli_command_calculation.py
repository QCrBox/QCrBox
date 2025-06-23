# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import signal

import anyio

from pyqcrbox import logger
from pyqcrbox.debug import eel_logging
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation


class CLICmdCalculation(BaseCalculation):
    def __init__(self, proc: asyncio.subprocess.Process, calculation_id: str, calc_finished_event: anyio.Event):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.proc = proc
        self.calculation_id = calculation_id
        self._stdout = ""
        self._stderr = ""
        self.retrieved_stdout_stderr = False
        self.calc_finished_event = calc_finished_event

    @eel_logging
    async def wait_until_finished(self):
        logger.debug(f"Waiting for calculation to finish: {self!r}")
        # await self.proc.wait()
        logger.debug(f"Process finished running: {self!r}")
        await self.calc_finished_event.wait()
        logger.debug(f"calc_finished_event has been set: {self!r}")
        if self.status == CalculationStatusEnum.FAILED:
            logger.error(f"CLI Command failed:\nStdout:\n\n{await self.stdout}\n\nStderr:\n\n{await self.stderr}")

    @property
    def status(self) -> CalculationStatusEnum:
        match self.proc.returncode:
            case None:
                status = CalculationStatusEnum.RUNNING
            case 0:
                status = CalculationStatusEnum.SUCCESSFUL
            case _:
                status = CalculationStatusEnum.FAILED

        return status

    @eel_logging
    def _get_status_details_extra_info(self):
        return {"returncode": self.returncode}

    @property
    def returncode(self) -> int:
        return self.proc.returncode

    @property
    async def stdout(self) -> str:
        await self.retrieve_stdout_stderr()
        return self._stdout

    @property
    async def stderr(self) -> str:
        await self.retrieve_stdout_stderr()
        return self._stderr

    @eel_logging
    async def retrieve_stdout_stderr(self):
        if self.status != CalculationStatusEnum.RUNNING and not self.retrieved_stdout_stderr:
            stdout, stderr = await self.proc.communicate()
            self._stdout = stdout.decode()
            self._stderr = stderr.decode()
            self.retrieved_stdout_stderr = True

    @eel_logging
    async def terminate(self):
        if self.proc:
            # self.proc.terminate()
            os.killpg(self.proc.pid, signal.SIGTERM)
            logger.info(f"Terminated process for calculation {self!r}")
        else:
            logger.error(f"No process running for calculation {self!r} - nothing to terminate.")
