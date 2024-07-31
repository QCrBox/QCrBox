import time

import json
import textwrap
import urllib.request
from pyqcrbox.registry.shared.calculation_status import CalculationStatusDetails
from pyqcrbox.sql_models_NEW_v2.calculation_status_event import CalculationStatusEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qcrbox_wrapper.qcrbox_wrapper_new import QCrBoxCommand


class UnsuccessfulCalculationError(Exception):
    def __init__(self, status: "CalculationStatusDetails"):
        try:
            error_message = status.extra_info["msg"]
        except KeyError:
            error_message = "No error message available"

        msg = textwrap.dedent(
            f"""\
            Calculation with id {status.calculation_id} does not have the status completed but {status.status}.

            Potential error message:
            {error_message}

            Command stdout:
            {status.stdout}

            Command stderr:
            {status.stderr}
        """
        ).strip()

        super().__init__(msg)


class QCrBoxCalculation:
    """
    Represents a calculation performed on the QCrBox server.
    """

    def __init__(self, calc_id: int, calculation_parent: "QCrBoxCommand") -> None:
        """
        Initializes the QCrBoxCalculation instance.

        Parameters
        ----------
        calc_id : int
            Unique identifier for the calculation.
        calculation_parent : QCrBoxCommand
            Parent command object that instantiated the calculation.
        """
        self.id = calc_id
        self.calculation_parent = calculation_parent
        self._server_url = calculation_parent._server_url

    @property
    def status(self) -> CalculationStatusDetails:
        """
        Fetches and returns the current status of the calculation from the server.

        Returns
        -------
        CalculationSatusDetails
            A pydantic model containing detailed status information of the calculation.
        """
        with urllib.request.urlopen(f"{self._server_url}/calculations/{self.id}") as r:
            response_data = json.loads(r.read().decode("UTF-8"))

        return CalculationStatusDetails(**response_data)

    def wait_while_running(self, sleep_time: float) -> None:
        """
        Periodically checks the calculation's status and blocks until it is no longer 'running'.

        Parameters
        ----------
        sleep_time : float
            The interval, in seconds, between status checks.

        Raises
        ------
        RuntimeError
            If the calculation finishes with a status other than 'completed'.
        """
        while self.status.status == CalculationStatusEnum.RUNNING:
            time.sleep(sleep_time)
        if self.status.status != CalculationStatusEnum.COMPLETED:
            raise UnsuccessfulCalculationError(self.status)
