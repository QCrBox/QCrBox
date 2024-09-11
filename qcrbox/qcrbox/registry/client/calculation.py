# SPDX-License-Identifier: MPL-2.0

import asyncio
from abc import ABCMeta, abstractmethod

from pyqcrbox.sql_models import CalculationStatusEnum


class BaseCalculation(metaclass=ABCMeta):
    @property
    @abstractmethod
    def status(self) -> CalculationStatusEnum:
        pass

    @property
    async def status_details(self) -> dict:
        return {}


class ExternalCmdCalculation(BaseCalculation):
    def __init__(self, proc: asyncio.subprocess.Process):
        super().__init__()
        self.proc = proc

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
    def status(self) -> CalculationStatusEnum:
        try:
            if self.future.running():
                status = CalculationStatusEnum.RUNNING
            elif self.future.done():
                # TODO: this branch will also be executed if the future has been cancelled! We should handle this.
                self._status_details = self.future.result()
                status = CalculationStatusEnum.SUCCESSFUL
            else:
                status = CalculationStatusEnum.UNKNOWN
        except Exception as exc:
            self._status_details = {
                "msg": f"An error occurred when trying to determine the status of the future: {exc}"
            }
            status = CalculationStatusEnum.UNKNOWN

        return status

    @property
    async def status_details(self) -> dict:
        return self._status_details
