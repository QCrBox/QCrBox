import time

import json
import textwrap
import urllib.request
from pyqcrbox.sql_models_NEW_v2 import CalculationStatusEnum, CalculationStatusDetails
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qcrbox_wrapper.qcrbox_wrapper import QCrBoxCommand


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

    def __init__(self, calc_id: int, parent_command: "QCrBoxCommand") -> None:
        """
        Initializes the QCrBoxCalculation instance.

        Parameters
        ----------
        calc_id : int
            Unique identifier for the calculation.
        parent_command : QCrBoxCommand
            Parent command object that instantiated the calculation.
        """
        self.id = calc_id
        self.parent_command = parent_command
        self._server_url = parent_command._server_url

    def __repr__(self):
        clsname = self.__class__.__name__
        return f"<{clsname}: {self.id!r}>"

    @property
    def status_details(self) -> CalculationStatusDetails:
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

    @property
    def status(self) -> CalculationStatusEnum:
        return self.status_details.status

    def is_running(self) -> bool:
        return self.status in [CalculationStatusEnum.SUBMITTED, CalculationStatusEnum.RUNNING]

    def wait_while_running(self, sleep_time: float) -> None:
        """
        Periodically checks the calculation's status and blocks until it is no longer running.

        Parameters
        ----------
        sleep_time : float
            The interval, in seconds, between status checks.

        Raises
        ------
        RuntimeError
            If the calculation finishes with a status other than 'completed'.
        """
        while self.is_running():
            time.sleep(sleep_time)
        if self.status != CalculationStatusEnum.SUCCESSFUL:
            raise UnsuccessfulCalculationError(self.status)
