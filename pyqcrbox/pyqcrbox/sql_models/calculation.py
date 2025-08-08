from datetime import datetime
from typing import Any

from pydantic import Field, computed_field

from pyqcrbox.sql_models.base import QCrBoxPydanticBaseModel
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusDetails, CalculationStatusEnum


class CalculationBase(QCrBoxPydanticBaseModel):
    """Base dataclass for calculation metadata."""

    calculation_id: str
    client_private_inbox: str
    application_slug: str
    application_version: str
    command_name: str
    command_arguments: dict[str, Any]


class CalculationResponse(CalculationBase):
    """Calculation response model, for API responses."""

    status: str
    client_private_inbox: str
    output_dataset_id: str | None


class CalculationDB(CalculationBase):
    """Dataclass containing metadata about a calculation, used for NATS."""

    timestamp: datetime = Field(default_factory=datetime.now)
    status_events: list[CalculationStatusDetails] = []
    application_id: int | None = None
    command_id: int | None = None

    @computed_field(return_type=str)
    @property
    def status(self) -> str:
        """Get the current status of the calculation.

        Uses the latest status update event from the list of status events.

        Returns
        -------
        str
            The current status of the calculation, derived from a CalculationStatusEnum.

        """
        if len(self.status_events) == 0:
            return CalculationStatusEnum.UNKNOWN
        return self.status_events[-1].status

    @computed_field(return_type=str)
    @property
    def output_dataset_id(self) -> str | None:
        """Get the dataset ID of the output of the calculation.

        Returns
        -------
        str | None
            The QCrBox Dataset ID or None if there has been no output yet

        """
        if len(self.status_events) == 0:
            return None

        # returns either the last dataset id, or the dataset id for the calculation
        # success event
        return next(
            (e.output_dataset_id for e in self.status_events if e.status == CalculationStatusEnum.SUCCESSFUL),
            self.status_events[-1].output_dataset_id,
        )

    def to_response_model(self) -> CalculationResponse:
        """Convert this instance into a response model.

        Returns
        -------
        CalculationNatsResponseModel
            The Pydanatic model used for API responses.

        """
        data = self.model_dump(
            include=[
                "calculation_id",
                "client_private_inbox",
                "status",
                "output_dataset_id",
                "application_slug",
                "application_version",
                "command_name",
                "command_arguments",
            ],  # type: ignore
        )

        return CalculationResponse(**data)
