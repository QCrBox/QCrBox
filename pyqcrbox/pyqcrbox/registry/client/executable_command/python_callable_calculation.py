# SPDX-License-Identifier: MPL-2.0
import multiprocessing.pool

import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation


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
