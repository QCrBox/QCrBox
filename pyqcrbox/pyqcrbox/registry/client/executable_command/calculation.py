# SPDX-License-Identifier: MPL-2.0
import asyncio
import multiprocessing.pool
from abc import ABCMeta, abstractmethod

import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models_NEW_v2 import CalculationStatusDetails, CalculationStatusEnum


class BaseCalculation(metaclass=ABCMeta):
    def __init__(self, *, calculation_id: str, calc_finished_event: anyio.Event):
        self.calculation_id = calculation_id
        self.calc_finished_event = calc_finished_event

    @abstractmethod
    async def wait_until_finished(self):
        pass

    @property
    @abstractmethod
    def status(self) -> CalculationStatusEnum:
        pass

    async def get_status_details(self) -> CalculationStatusDetails:
        return CalculationStatusDetails(
            calculation_id=self.calculation_id,
            status=self.status,
            stdout=await self.stdout,
            stderr=await self.stderr,
            extra_info=self._get_status_details_extra_info(),
        )

    def _get_status_details_extra_info(self):
        return {}

    @property
    @abstractmethod
    async def stdout(self) -> str | None:
        pass

    @property
    @abstractmethod
    async def stderr(self) -> str | None:
        pass


class PythonCallableCalculation(BaseCalculation):
    def __init__(
        self,
        result: multiprocessing.pool.ApplyResult,
        *,
        pool: multiprocessing.pool.Pool,
        calculation_id: str,
        calc_finished_event: anyio.Event,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self._apply_result = result
        self.pool = pool
        # self._status_details = None
        self.return_value = None

    def __repr__(self):
        clsname = self.__class__.__name__
        return f"<{clsname}: calculation_id={self.calculation_id}>"

    async def wait_until_finished(self):
        logger.debug(f"Waiting for calculation to finish: {self.calculation_id!r}")
        await self.calc_finished_event.wait()
        logger.debug(f"Calculation finished: {self.calculation_id!r}")

    @property
    def status(self) -> CalculationStatusEnum:
        if self._apply_result.ready():
            if self._apply_result.successful():
                self.return_value = self._apply_result.get()
                calc_status = CalculationStatusEnum.SUCCESSFUL
            else:
                calc_status = CalculationStatusEnum.FAILED
            logger.debug("Calculation finished, closing multiprocessing pool.")
            self.pool.close()
            self.pool.join()
        else:
            calc_status = CalculationStatusEnum.RUNNING

        return calc_status

    @property
    async def stdout(self) -> str | None:
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDOUT not implemented yet for PythonCallableCalculation"

    @property
    async def stderr(self) -> str | None:
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDERR not implemented yet for PythonCallableCalculation"

    async def terminate(self):
        logger.debug("Terminating multiprocessing pool (any running workers will be stopped immediately).")
        self.pool.terminate()
        self.pool.join()
        logger.trace("Multiprocessing pool terminated.")


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
