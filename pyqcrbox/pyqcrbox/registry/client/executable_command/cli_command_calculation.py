# SPDX-License-Identifier: MPL-2.0
import asyncio

import anyio

from pyqcrbox import logger
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

    async def wait_until_finished(self):
        logger.debug(f"Waiting for calculation to finish: {self.calculation_id!r}")
        # logger.debug("Waiting for process to exit...")
        await self.proc.wait()
        # logger.debug("Process finished.")
        self.calc_finished_event.set()
        logger.debug(f"Calculation finished: {self.calculation_id!r} (status: {self.status!r})")
        if self.status == CalculationStatusEnum.FAILED:
            logger.debug(f"\nStdout:\n\n{await self.stdout}\n\nStderr:\n\n{await self.stderr}")

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

    async def retrieve_stdout_stderr(self):
        if self.status != CalculationStatusEnum.RUNNING and not self.retrieved_stdout_stderr:
            stdout, stderr = await self.proc.communicate()
            self._stdout = stdout.decode()
            self._stderr = stderr.decode()
            self.retrieved_stdout_stderr = True
