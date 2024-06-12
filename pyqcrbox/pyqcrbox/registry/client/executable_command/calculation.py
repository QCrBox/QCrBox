# SPDX-License-Identifier: MPL-2.0

import multiprocessing.pool
from abc import ABCMeta, abstractmethod
from enum import Enum


class CalculationStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


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
    def __init__(self, result: multiprocessing.pool.ApplyResult):
        super().__init__()
        self._apply_result = result
        # self._status_details = None
        self.return_value = None

    @property
    def status(self) -> CalculationStatus:
        if self._apply_result.ready():
            if self._apply_result.successful():
                self.return_value = self._apply_result.get()
                return CalculationStatus.COMPLETED
            else:
                return CalculationStatus.FAILED
        else:
            return CalculationStatus.RUNNING

    # @property
    # async def status_details(self) -> dict:
    #     return self._status_details
