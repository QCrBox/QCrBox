import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models_NEW_v2 import CalculationStatusEnum
from .base_calculation import BaseCalculation


class InteractiveCmdCalculation(BaseCalculation):
    def __init__(
        self,
        *,
        calculation_id: str,
        calc_finished_event: anyio.Event,
        prepare_calc: BaseCalculation | None,
        run_calc: BaseCalculation,
        finalise_calc: BaseCalculation | None,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.prepare_calc = prepare_calc
        self.run_calc = run_calc
        self.finalise_calc = finalise_calc

    @property
    def status(self) -> CalculationStatusEnum:
        return CalculationStatusEnum.RUNNING

    @property
    async def stdout(self) -> None:
        return None

    @property
    async def stderr(self) -> None:
        return None

    async def wait_until_finished(self):
        if self.prepare_calc:
            logger.debug("Running 'prepare' command")
            await self.prepare_calc.wait_until_finished()

        logger.debug("Running the main interactive command")
        await self.run_calc.wait_until_finished()

        if self.finalise_calc:
            logger.debug("Running the 'finalise' command")
            await self.finalise_calc.wait_until_finished()
