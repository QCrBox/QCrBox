import anyio

from pyqcrbox import logger
from pyqcrbox.services import get_data_file_manager
from pyqcrbox.sql_models import CalculationStatusEnum

from .base_calculation import BaseCalculation
from .python_callable_calculation import PythonCallableCalculation


class InteractiveSessionCalculation(BaseCalculation):
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
        self.is_closed = False
        self.output_dataset_id = None
        self.session_closed_event = anyio.Event()

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
        logger.debug("InteractiveSessionCalculation: entered wait_until_finished()")

        if self.prepare_calc:
            assert isinstance(
                self.prepare_calc, PythonCallableCalculation
            ), "Only Python callables are supported for 'prepare_command' at the moment"
            logger.debug(f"Waiting for 'prepare' command to finish: {self.prepare_calc.calculation_id!r}")
            await self.prepare_calc.wait_until_finished()
            logger.debug(f"Prepare command finished: {self.prepare_calc.calculation_id!r}")

        logger.debug("Waiting for 'run' command to finish")
        await self.run_calc.wait_until_finished()
        logger.debug(f"Run command finished: {self.run_calc.calculation_id!r}")

        logger.debug("Waiting for 'calc_finished' event to be set")
        await self.calc_finished_event.wait()
        logger.debug(f"Waiting for 'calc_finished' event to be set: {self.calc_finished_event}")

        if self.finalise_calc:
            assert isinstance(
                self.finalise_calc, PythonCallableCalculation
            ), "Only Python callables are supported for 'finalise_command' at the moment"
            logger.debug(f"Waiting for 'finalise' command to finish: {self.finalise_calc.calculation_id!r}")
            await self.finalise_calc.wait_until_finished()

            output_file = self.finalise_calc.return_value
            if output_file is None:
                logger.info("No output file from interactive session")
            else:
                data_manager = await get_data_file_manager()
                try:
                    output_data_file_id = await data_manager.import_local_file(output_file)
                    self.output_dataset_id = await data_manager.create_dataset_from_data_file(output_data_file_id)
                except FileNotFoundError:
                    logger.error(f"Failed to create dataset for output from 'finalise' command, {output_file=!r}")
                    raise
                logger.info(
                    "The output from the interactive session has been placed into dataset %s", self.output_dataset_id
                )

        self.is_closed = True
        self.session_closed_event.set()
        logger.debug(f"InteractiveSessionCalculation: interactive session finished: {self.calculation_id!r}")

    async def close_interactive_session(self):
        if self.calc_finished_event.is_set():
            if self.is_closed:
                logger.debug("Interactive session already closed")
            else:
                logger.warning("Interactive session is being closed.")
            return

        logger.debug("Closing interactive session")

        # TODO: should we set the calc_finished_event for the run command?
        #       might be safer in case it doesn't terminate on its own.
        logger.debug("Sending 'calc_finished' event to run_cal, this will wait for the finalise command to finish")
        self.run_calc.calc_finished_event.set()

        # Todo: terminate run_calc

        logger.debug("Sending 'calc_finished' event to interactive session calculation")
        self.calc_finished_event.set()
        await self.session_closed_event.wait()
        logger.debug("Done. The session should finish now.")
