# SPDX-License-Identifier: MPL-2.0

import asyncio
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


class ExternalCmdCalculation(BaseCalculation):
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


class PythonCallableCalculation(BaseCalculation):
    def __init__(self, future: asyncio.Future):
        super().__init__()
        self.future = future
        self._status_details = None

    @property
    def status(self) -> CalculationStatus:
        try:
            if self.future.running():
                status = CalculationStatus.RUNNING
            elif self.future.done():
                # TODO: this branch will also be executed if the future has been cancelled! We should handle this.
                self._status_details = self.future.result()
                status = CalculationStatus.COMPLETED
            else:
                status = CalculationStatus.UNKNOWN
        except Exception as exc:
            self._status_details = {
                "msg": f"An error occurred when trying to determine the status of the future: {exc}"
            }
            status = CalculationStatus.UNKNOWN

        return status

    @property
    async def status_details(self) -> dict:
        return self._status_details
