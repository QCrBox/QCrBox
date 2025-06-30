# SPDX-License-Identifier: MPL-2.0
from abc import ABCMeta, abstractmethod

import anyio

from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum


class BaseCalculation(metaclass=ABCMeta):
    """Abstract base class for calculation status tracking.

    Parameters
    ----------
    calculation_id : str
        Unique identifier for the calculation.
    calc_finished_event : anyio.Event
        Event that signals when the calculation is finished.

    """

    def __init__(self, *, calculation_id: str, calc_finished_event: anyio.Event) -> None:
        self.calculation_id = calculation_id
        self.calc_finished_event = calc_finished_event
        self.exception = None

    def __repr__(self):
        """Return a string representation of the calculation instance.

        Returns
        -------
        str
            String representation of the object.

        """
        clsname = self.__class__.__name__
        return f"<{clsname}: calculation_id={self.calculation_id}>"

    @abstractmethod
    async def wait_until_finished(self) -> None:
        """Wait until the calculation is finished."""
        pass

    @property
    @abstractmethod
    def status(self) -> CalculationStatusEnum:
        """Get the current status of the calculation.

        Returns
        -------
        CalculationStatusEnum
            The current status of the calculation.

        """
        pass

    async def get_status_details(self) -> CalculationStatusDetails:
        """Retrieve detailed status information for the calculation.

        Returns
        -------
        CalculationStatusDetails
            Detailed status information including stdout, stderr, and extra info.

        """
        return CalculationStatusDetails(
            calculation_id=self.calculation_id,
            status=self.status,
            stdout=await self.stdout,
            stderr=await self.stderr,
            extra_info=self._get_status_details_extra_info(),
        )

    def _get_status_details_extra_info(self):
        """Get additional information for status details.

        Returns
        -------
        dict
            Extra information as a dictionary.

        """
        return {}

    @property
    @abstractmethod
    async def stdout(self) -> str | None:
        """Retrieve the standard output of the calculation.

        Returns
        -------
        str or None
            The standard output, or None if not available.

        """
        pass

    @property
    @abstractmethod
    async def stderr(self) -> str | None:
        """Retrieve the standard error of the calculation.

        Returns
        -------
        str or None
            The standard error, or None if not available.

        """
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Terminate the calculation."""
        pass
