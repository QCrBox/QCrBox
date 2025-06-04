import anyio

from pyqcrbox import logger
from pyqcrbox.debug import eel_logging
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
    ) -> None:
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

    @eel_logging
    async def wait_until_finished(self) -> None:
        """Asynchronously wait for all calculation phases to complete.

        This method sequentially waits for the 'prepare', 'run', and 'finalise'
        calculation commands to finish, if they are present. It also waits for
        the 'calc_finished' event to be set, indicating that the calculation
        has terminated. Upon successful completion of the 'finalise' phase, it
        imports the output file into the data store and create a dataset from
        it. The method sets the session as closed and signals the session
        closure event.

        Raises
        ------
        AssertionError
            If 'prepare_calc' or 'finalise_calc' are not instances of PythonCallableCalculation.
        FileNotFoundError
            If the output file from the 'finalise' command cannot be found during import.
        """
        if self.prepare_calc:
            assert isinstance(
                self.prepare_calc, PythonCallableCalculation
            ), "Only Python callables are supported for 'prepare_command' at the moment"
            logger.debug(f"Waiting for 'prepare' command to finish: {self.prepare_calc.calculation_id!r}")
            await self.prepare_calc.wait_until_finished()
            logger.debug(f"Prepare command finished: {self.prepare_calc.calculation_id!r}")

        logger.debug("Waiting for 'run' command to finish")
        await self.run_calc.wait_until_finished()

        # We wait for this event flag to be set (in terminate) before we run
        # the finalise calculation and import the output into the data store
        logger.debug("Waiting for 'calc_finished' event to be set upon calculation termination")
        await self.calc_finished_event.wait()

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

    @eel_logging
    async def terminate(self) -> None:
        """Terminate the interactive session.

        If the calculation is already finished, logs the session state and
        returns. Otherwise, it signals the calculation to finish, waits for
        session closure.
        """
        if self.calc_finished_event.is_set():
            if self.is_closed:
                logger.warning(f"Interactive session {self.calculation_id!r} already closed")
            else:
                logger.warning(f"Interactive session {self.calculation_id!r} is already being closed.")
            return

        logger.debug("Closing interactive session")

        # Sending 'calc_finished' event to run_cal, this will cause run_calc.wait_until_finished()
        # to exit
        self.run_calc.calc_finished_event.set()

        # When the run calc is finished, this flag is used to communicate with the interactive
        # session wait_until_finished() that the finalise command can be run
        self.calc_finished_event.set()

        # Keep waiting until the finalise calculation has finished and the output has been added to
        # the data store
        await self.session_closed_event.wait()
