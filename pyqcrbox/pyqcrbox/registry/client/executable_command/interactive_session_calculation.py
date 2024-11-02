import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation


class InteractiveSessionCalculation(BaseCalculation):
    def __init__(
        self,
        *,
        calculation_id: str,
        calc_finished_event: anyio.Event,
        # prepare_calc: BaseCalculation | None,
        run_calc: BaseCalculation,
        finalise_calc: BaseCalculation | None,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        # self.prepare_calc = prepare_calc
        self.run_calc = run_calc
        self.finalise_calc = finalise_calc
        self.is_closed = False

    @property
    def status(self) -> CalculationStatusEnum:
        if not self.is_closed:
            return CalculationStatusEnum.RUNNING
        else:
            return CalculationStatusEnum.SUCCESSFUL

    @property
    async def stdout(self) -> None:
        return None

    @property
    async def stderr(self) -> None:
        return None

    async def wait_until_finished(self):
        # if self.prepare_calc:
        #     logger.debug("Running 'prepare' command")
        #     await self.prepare_calc.wait_until_finished()

        logger.debug("Running the main interactive command")
        await self.run_calc.wait_until_finished()

        logger.debug(f"Waiting for interactive session to complete: {self.calculation_id!r}")
        await self.calc_finished_event.wait()

        if self.finalise_calc:
            logger.debug("Running the 'finalise' command")
            await self.finalise_calc.wait_until_finished()

        self.is_closed = True
        logger.debug(f"Interactive session finished: {self.calculation_id!r}")

    async def close_interactive_session(self):
        logger.debug("Closing interactive session")
        logger.debug("Sending 'calc_finished' event to run_calc")

        # TODO: should we set the calc_finished_event for the run command?
        #       might be safer in case it doesn't terminate on its own.
        # self.run_calc.calc_finished_event.set()

        self.calc_finished_event.set()
        logger.debug("Done. The session should finish now.")
