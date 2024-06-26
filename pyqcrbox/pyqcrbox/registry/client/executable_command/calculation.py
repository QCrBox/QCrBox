# SPDX-License-Identifier: MPL-2.0
import asyncio
import multiprocessing.pool
from abc import ABCMeta, abstractmethod

from pyqcrbox import logger

from ...shared.calculation_status import CalculationStatus


class BaseCalculation(metaclass=ABCMeta):
    @property
    @abstractmethod
    def status(self) -> CalculationStatus:
        pass

    @property
    async def status_details(self) -> dict:
        return {}


# class ExternalCmdCalculation(BaseCalculation):
#     def __init__(self, proc: anyio.abc.Process):
#         super().__init__()
#         self.proc = proc
#
#     @property
#     def status(self) -> CalculationStatus:
#         match self.proc.returncode:
#             case None:
#                 status = CalculationStatus.RUNNING
#             case 0:
#                 status = CalculationStatus.COMPLETED
#             case _:
#                 status = CalculationStatus.FAILED
#
#         return status
#
#     async def get_status_details(self) -> msg_specs.CalculationStatusDetails:
#         returncode = self.proc.returncode
#         status_details = msg_specs.CalculationStatusDetails(
#             returncode=returncode,
#             stdout="",
#             stderr="",
#         )
#
#         if returncode is not None:
#             async with self.proc as process:
#                 try:
#                     status_details.stdout = await TextReceiveStream(process.stdout).receive()
#                 except EndOfStream:
#                     status_details.stdout = ""
#
#                 try:
#                     status_details.stderr = await TextReceiveStream(process.stderr).receive()
#                 except EndOfStream:
#                     status_details.stderr = ""
#
#         return status_details


class PythonCallableCalculation(BaseCalculation):
    def __init__(
        self, result: multiprocessing.pool.ApplyResult, *, pool: multiprocessing.pool.Pool, calculation_id: str
    ):
        super().__init__()
        self._apply_result = result
        self.pool = pool
        self.calculaton_id = calculation_id
        # self._status_details = None
        self.return_value = None

    def __repr__(self):
        clsname = self.__class__.__name__
        return f"<{clsname}: calculation_id={self.calculaton_id}>"

    @property
    def status(self) -> CalculationStatus:
        if self._apply_result.ready():
            if self._apply_result.successful():
                self.return_value = self._apply_result.get()
                calc_status = CalculationStatus.COMPLETED
            else:
                calc_status = CalculationStatus.FAILED
            logger.debug("Calculation finished, closing multiprocessing pool.")
            self.pool.close()
            self.pool.join()
        else:
            calc_status = CalculationStatus.RUNNING

        return calc_status

    # @property
    # async def status_details(self) -> dict:
    #     return self._status_details

    async def terminate(self):
        logger.debug("Terminating multiprocessing pool (any running workers will be stopped immediately).")
        self.pool.terminate()
        self.pool.join()
        logger.trace("Multiprocessing pool terminated.")


class CLICmdCalculation(BaseCalculation):
    def __init__(self, proc: asyncio.subprocess.Process):
        super().__init__()
        self.proc = proc

    @property
    def status(self) -> CalculationStatus:
        match self.proc.returncode:
            case None:
                status = CalculationStatus.RUNNING
            case 0:
                status = CalculationStatus.COMPLETED
            case _:
                status = CalculationStatus.FAILED

        return status

    @property
    async def status_details(self):
        returncode = self.proc.returncode
        status_details = {
            "returncode": returncode,
        }
        if returncode is not None:
            stdout, stderr = await self.proc.communicate()
            status_details["stdout"] = stdout
            status_details["stderr"] = stderr
        return status_details
