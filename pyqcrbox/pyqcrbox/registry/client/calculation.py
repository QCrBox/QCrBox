# SPDX-License-Identifier: MPL-2.0

import asyncio
from abc import ABCMeta, abstractmethod
from enum import Enum

import anyio.abc
from anyio import EndOfStream
from anyio.streams.text import TextReceiveStream

from pyqcrbox import msg_specs


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
    def __init__(self, proc: anyio.abc.Process):
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

    async def get_status_details(self) -> msg_specs.CalculationStatusDetails:
        returncode = self.proc.returncode
        status_details = msg_specs.CalculationStatusDetails(
            returncode=returncode,
            stdout="",
            stderr="",
        )

        if returncode is not None:
            async with self.proc as process:
                try:
                    status_details.stdout = await TextReceiveStream(process.stdout).receive()
                except EndOfStream:
                    status_details.stdout = ""

                try:
                    status_details.stderr = await TextReceiveStream(process.stderr).receive()
                except EndOfStream:
                    status_details.stderr = ""

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
