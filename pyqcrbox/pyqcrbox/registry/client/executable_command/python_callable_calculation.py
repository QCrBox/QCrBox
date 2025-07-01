# SPDX-License-Identifier: MPL-2.0
import multiprocessing.pool

import anyio
import psutil

from pyqcrbox import logger
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation


class PythonCallableCalculation(BaseCalculation):
    """Calculation class for tracking the status of a Python callable execution.

    Parameters
    ----------
    result : multiprocessing.pool.ApplyResult
        The result object for the asynchronous callable execution.
    pool : multiprocessing.pool.Pool
        The multiprocessing pool used for execution.
    calculation_id : str
        Unique identifier for the calculation.
    calc_finished_event : anyio.Event
        Event that signals when the calculation is finished.

    """

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
        self.return_value = None
        self._terminated = False

    async def wait_until_finished(self):
        """Wait until the calculation is finished."""
        await self.calc_finished_event.wait()
        _ = self.status  # FIXME: This is a workaround to ensure the return value is set.

    @property
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """
        if self._terminated:
            return CalculationStatusEnum.SUCCESSFUL

        if self._apply_result.ready():
            if self._apply_result.successful():
                self.return_value = self._apply_result.get()
                calc_status = CalculationStatusEnum.SUCCESSFUL
            else:
                calc_status = CalculationStatusEnum.FAILED
                # This is less than ideal, but seems to be the only way to get the exception
                # that was raised inside the pool.
                try:
                    self._apply_result.get()
                except Exception as exc:
                    self.exception_raised = exc
            # When the result is ready, we can close the pool normally without
            # having to forcefully terminate the process and child processes
            # by hand
            logger.debug(
                f"Calculation {self.calculation_id} finished with status {calc_status}, closing multiprocessing pool",
            )
            self.pool.close()
            self.pool.join()
        else:
            calc_status = CalculationStatusEnum.RUNNING

        return calc_status

    @property
    async def stdout(self) -> str | None:
        """Retrieve the standard output of the calculation.

        Returns
        -------
        str or None
            The standard output, or None if not available.

        """
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDOUT not implemented yet for PythonCallableCalculation"

    @property
    async def stderr(self) -> str | None:
        """Retrieve the standard error of the calculation.

        Returns
        -------
        str or None
            The standard error, or None if not available.

        """
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDERR not implemented yet for PythonCallableCalculation"

    async def terminate(self):
        """Terminate the calculation."""
        logger.debug(
            "Terminating multiprocessing pool (any running workers will be stopped immediately).",
        )
        # If this launched an app with a GUI, it probably has other processes it
        # spawned which need to be killed. Unfortunately pool.terminate() doesn't
        # do this, so we have to find the parent processes in the pool and kill their
        # child processes too
        processes = [psutil.Process(worker.pid) for worker in self.pool._pool if worker.is_alive()]
        for process in processes:
            child_processes = process.children(recursive=True)
            for child in child_processes:
                child.terminate()
            process.terminate()
        self._terminated = True
        logger.debug("Multiprocessing pool terminated.")
