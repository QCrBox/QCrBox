# SPDX-License-Identifier: MPL-2.0
import multiprocessing.pool
from pathlib import Path

import anyio
import psutil

from pyqcrbox import logger
from pyqcrbox.data_management.data_manager import DataManager
from pyqcrbox.debug import log_eel
from pyqcrbox.sql_models import CalculationStatusEnum
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import Cif2CifOptions, CifDataFileParameter

from .base_calculation import BaseCalculation


class PythonCallableCalculation(BaseCalculation):
    """Calculation class for tracking the status of a Python callable execution.

    Parameters
    ----------
    result : multiprocessing.pool.ApplyResult
        The result object for the asynchronous callable execution.
    pool : multiprocessing.pool.Pool
        The multiprocessing pool used for execution.
    calculation_id : str
        Unique identifier for the calculation.
    calc_finished_event : anyio.Event
        Event that signals when the calculation is finished.

    """

    def __init__(
        self,
        result: multiprocessing.pool.ApplyResult,
        *,
        pool: multiprocessing.pool.Pool,
        calculation_id: str,
        calc_finished_event: anyio.Event,
    ):
        super().__init__(calculation_id=calculation_id, calc_finished_event=calc_finished_event)
        self._apply_result = result
        self.pool = pool
        self.return_value = None
        self._terminated = False

    @log_eel
    async def save_output_to_data_manager(
        self,
        data_manager: DataManager,
        *,
        merge_options: Cif2CifOptions | None = None,
        input_cif: CifDataFileParameter | None = None,
    ) -> str | None:
        """Save the output of the calculation to the Data File Manager.

        It is assumed that the return value of the PythonCallable is the data to
        be stored in the Data File Manager, and that only a single file is
        returned.

        Parameters
        ----------
        data_manager : DataManager
            An instance of the data manager.
        merge_options : Cif2CifOptions | None
            Options which will be used to create a unified CIF.
        input_cif: CifDataFileParameter | None
            The original CIF prior to being transformed to a new CIF format.

        Returns
        -------
        str | None
            The dataset ID created to store the output.


        """
        if not self.return_value:
            logger.info("This calculation has no return value, nothing to store in the data manager")
            return None
        if not isinstance(self.return_value, str):
            exc_msg = f"The return value from the calculation must be an str, not type {type(self.return_value)}"
            logger.error(f"Unable to save output of calculation {self.calculation_id}: '{exc_msg}'")
            raise ValueError(exc_msg)

        output_file = Path(self.return_value)
        if not output_file.exists() or not output_file.is_file():
            exc_msg = f"The return value '{output_file}' from the calculation is not a file"
            logger.error(f"Unable to save output of calculation {self.calculation_id}: '{exc_msg}'")
            raise ValueError(exc_msg)

        if input_cif and merge_options:
            logger.debug("Merging to unified format in PythonCallableCalculation")
            output_file = await input_cif.to_unified_format(output_file, merge_options)

        try:
            data_file_id = await data_manager.import_file(output_file)
            self.output_dataset_id = await data_manager.create_dataset_from_data_files(data_file_id)
        except FileNotFoundError:
            logger.error(f"Failed to add data file and create dataset for {output_file}")
            raise

        logger.info(f"Created Dataset {self.output_dataset_id} containing data file {data_file_id}")

        return self.output_dataset_id

    @log_eel
    async def wait_until_finished(self):
        """Wait until the calculation is finished."""
        await self.calc_finished_event.wait()
        _ = self.status  # FIXME: This is a workaround to ensure the return value is set.

    @property
    @log_eel
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """
        # Short-circuit to return SUCCESS when user terminated command
        if self._terminated:
            return CalculationStatusEnum.SUCCESSFUL

        if self._apply_result.ready():
            if self._apply_result.successful():
                self.return_value = self._apply_result.get()
                calc_status = CalculationStatusEnum.SUCCESSFUL
            else:
                calc_status = CalculationStatusEnum.FAILED
                # This is less than ideal, but seems to be the only way to get the exception
                # that was raised inside the pool.
                try:
                    self._apply_result.get()
                except Exception as exc:
                    self.exception_raised = exc
            logger.debug(
                f"Calculation {self.calculation_id} finished with status {calc_status}, closing multiprocessing pool",
            )
            # When the result is ready, we can close the pool normally without having to forcefully
            # terminate the process and child processes by hand
            self.pool.close()
            self.pool.join()
        else:
            calc_status = CalculationStatusEnum.RUNNING

        return calc_status

    @property
    @log_eel
    async def stdout(self) -> str | None:
        """Retrieve the standard output of the calculation.

        Returns
        -------
        str or None
            The standard output, or None if not available.

        """
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDOUT not implemented yet for PythonCallableCalculation"

    @property
    @log_eel
    async def stderr(self) -> str | None:
        """Retrieve the standard error of the calculation.

        Returns
        -------
        str or None
            The standard error, or None if not available.

        """
        if self.status == CalculationStatusEnum.RUNNING:
            return None
        else:
            return "Retrieval of STDERR not implemented yet for PythonCallableCalculation"

    @log_eel
    async def terminate(self):
        """Terminate the calculation."""
        logger.debug(
            "Terminating multiprocessing pool (any running workers will be stopped immediately).",
        )
        # If this launched an app with a GUI, it probably has other processes it
        # spawned which need to be killed. Unfortunately pool.terminate() doesn't
        # do this, so we have to find the parent processes in the pool and kill their
        # child processes too
        processes = [psutil.Process(worker.pid) for worker in self.pool._pool if worker.is_alive()]  # type: ignore
        for process in processes:
            child_processes = process.children(recursive=True)
            for child in child_processes:
                child.terminate()
            process.terminate()
        self._terminated = True
        logger.debug("Multiprocessing pool terminated.")

    @log_eel
    def get_error_message(self) -> str:
        return ""
