# SPDX-License-Identifier: MPL-2.0
from abc import ABCMeta, abstractmethod

import anyio

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
