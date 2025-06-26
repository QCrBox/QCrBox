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
    ) -> None:
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self.prepare_calc = prepare_calc
        self.run_calc = run_calc
        self.finalise_calc = finalise_calc
        self.is_closed = False
        self.output_dataset_id = None
        self.session_closed_event = anyio.Event()
        logger.debug(
            f"Created new InteractiveSessionCalculation: {self!r}",
        )

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
        # We have to wait for the "calc_finished" event to be set, which only can happen
        # when we try and close the interactive session
        logger.debug("Waiting for 'calc_finished' event to be set upon calculation termination")
        await self.calc_finished_event.wait()

        if self.finalise_calc:
            assert isinstance(self.finalise_calc, PythonCallableCalculation)
            logger.debug(f"Waiting for 'finalise' command to finish: {self.finalise_calc!r}")
            await self.finalise_calc.wait_until_finished()

            output_file = self.finalise_calc.return_value
            if not output_file:
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
        logger.debug(f"InteractiveSessionCalculation: interactive session finished: {self}")

    async def terminate(self) -> None:
        """Terminate the interactive session.

        If the calculation is already finished, logs the session state and
        returns. Otherwise, it signals the calculation to finish, waits for
        session closure.
        """
        if self.calc_finished_event.is_set():
            if self.is_closed:
                logger.warning(f"Interactive session {self} already closed")
            else:
                logger.warning(f"Interactive session {self} is already being closed.")
            return
        logger.debug(f"Closing interactive session {self}")

        # Terminate the prepare and run calculation if still running. Then we need to set the 'calc_finished'
        # event which *should* cause run_calc.wait_until_finished() to exit. If this flag isn't set, then
        # execution will hang
        if self.prepare_calc == CalculationStatusEnum.RUNNING:
            logger.debug("Terminating prepare command")
            await self.prepare_calc.terminate()
        if self.run_calc.status == CalculationStatusEnum.RUNNING:
            logger.debug("Terminating run command")
            await self.run_calc.terminate()
        self.run_calc.calc_finished_event.set()

        # When the run calc is finished, this flag is used to communicate with the interactive
        # session wait_until_finished() that the finalise command can be run
        self.calc_finished_event.set()

        # Keep waiting until the finalise calculation has finished and the output has been added to
        # the data store
        await self.session_closed_event.wait()
