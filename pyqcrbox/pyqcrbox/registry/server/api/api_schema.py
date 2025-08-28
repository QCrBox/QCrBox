from typing import Any, Generic, TypeVar

from litestar.openapi.datastructures import ResponseSpec
from pydantic import BaseModel

from pyqcrbox.data_management.data_file import DataFileResponse
from pyqcrbox.data_management.dataset import DatasetResponse
from pyqcrbox.msg_specs.msg_types.client_side.get_calculation_status import CloseInteractiveSessionResponse
from pyqcrbox.msg_specs.msg_types.client_side.stop_calculation import StoppedCalculationResponse
from pyqcrbox.sql_models.application_spec import ApplicationSpecWithCommandsResponse
from pyqcrbox.sql_models.calculation import CalculationResponse
from pyqcrbox.sql_models.command_spec import CommandSpecWithParametersResponse
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfoResponse

T = TypeVar("T")

# Request bodies


class CreateInteractiveSessionParameters(BaseModel):
    """Request body for invoking an interactive session.

    Attributes
    ----------
    application_slug : str
        The slug of the application to invoke, as defined in the application
        specification.
    application_version : str
        The version number of the application to invoke, as defined in the application
        specification.
    arguments : dict
        Arguments required to invoke the interactive session for the application
        requested.

    """

    application_slug: str
    application_version: str
    command_arguments: dict[str, Any]


class InvokeCommandParameters(BaseModel):
    """Request body for invoke a command.

    Attributes
    ----------
    application_slug : str
        The slug of the application to invoke, as defined in the application
        specification.
    application_version : str
        The version number of the application to invoke, as defined in the application
        specification.
    command_name : str
        The name of the command to invoke, as defined in the application specification.
    arguments : dict
        Arguments required to invoke the interactive session for the application
        requested.

    """

    application_slug: str
    application_version: str
    command_name: str
    command_arguments: dict[str, Any]


# Success responses


class QCrBoxHealthResponse(BaseModel):
    """Response model for health check endpoint.

    Attributes
    ----------
    status : str
        The health status of the QCrBox registry (e.g., 'ok').

    """

    status: str


class QCrBoxResponse(BaseModel, Generic[T]):
    """Generic response model for QCrBox API endpoints.

    Attributes
    ----------
    status : str
        The status of the response (e.g., 'success', 'error').
    message : str
        A human-readable message describing the response.
    timestamp : str
        The timestamp when the response was generated.
    payload : T
        The main data payload of the response, type varies by endpoint.

    """

    status: str
    message: str
    timestamp: str
    payload: T


class ApplicationsResponse(BaseModel):
    """Response model for a list of registered applications.

    Attributes
    ----------
    applications : list[ApplicationSpecWithCommands]
        A list of applications with their command specifications.

    """

    applications: list[ApplicationSpecWithCommandsResponse]


class CalculationsResponse(BaseModel):
    """Response model for a list of calculations.

    Attributes
    ----------
    calculations : list[CalculationNatsResponseModel]
        A list of calculations.

    """

    calculations: list[CalculationResponse]


class CommandsResponse(BaseModel):
    """Response model for a list of commands.

    Attributes
    ----------
    commands : list[CommandSpecWithParameters]
        A list of command specifications with their parameters.

    """

    commands: list[CommandSpecWithParametersResponse]


class DataFilesResponse(BaseModel):
    """Response model for a list of data files.

    Attributes
    ----------
    data_files : list[DataFileMetadataResponse]
        A list of data file metadata.

    """

    data_files: list[DataFileResponse]


class DatasetsResponse(BaseModel):
    """Response model for a list of datasets.

    Attributes
    ----------
    datasets : list[DatasetResponse]
        A list of dataset metadata.

    """

    datasets: list[DatasetResponse]


class DatasetsWithDataFilesResponse(BaseModel):
    """Response model for a dataset with its data files.

    Attributes
    ----------
    datasets : list[DatasetResponse]
        A list of dataset metadata.
    data_files : list[DataFileResponse]
        A list of data file metadata.

    """

    datasets: list[DatasetResponse]
    data_files: list[DataFileResponse]


class DatasetAppendResponse(BaseModel):
    """Response model for appending a file to a dataset.

    Attributes
    ----------
    datasets : list[DatasetResponse]
        A list of dataset metadata.
    data_files : list[DataFileResponse]
        A list of data file metadata.

    """

    datasets: list[DatasetResponse]
    data_files: list[DataFileResponse]
    appended_file: DataFileResponse


class InvokeCommandResponse(BaseModel):
    """Response model for a calculation ID after invoking a command.

    Attributes
    ----------
    calculation_id : str
        The generated calculation identifier of the invoked command.

    """

    calculation_id: str


class InteractiveSessionsResponse(BaseModel):
    """Response model for a list of interactive sessions.

    Attributes
    ----------
    interactive_sessions : list[InteractiveSessionInfoResponse]
        A list of interactive sessions.

    """

    interactive_sessions: list[InteractiveSessionInfoResponse]


class InteractiveSessionIDResponse(BaseModel):
    """Response model containing the ID of a created interactive session.

    Attributes
    ----------
    interactive_session_id : str
        The generated identifier of the created interactive session.

    """

    interactive_session_id: str


class InteractiveSessionClosedResponse(BaseModel):
    """Response model for a closed interactive session.

    Attributes
    ----------
    interactive_sessions : list[CloseInteractiveSessionResponseNATS]
        A list of closed interactive sessions.

    """

    interactive_sessions: list[CloseInteractiveSessionResponse]


class CalculationStoppedResponse(BaseModel):
    """Response model for a command which was stopped.

    Attributes
    ----------
    commands : list[EndCommandResponseNATS]
        A list of ended commands.

    """

    calculations: list[StoppedCalculationResponse]


# Error responses


class ErrorResponse(BaseModel):
    """Model for error details in error responses.

    Attributes
    ----------
    code : int
        The error code (usually an HTTP status code).
    message : str
        A human-readable error message.
    details : str or list[str]
        Additional details about the error.

    """

    code: int
    message: str
    details: str | list[str]


class QCrBoxErrorResponse(BaseModel):
    """Response model for API error responses.

    Attributes
    ----------
    status : str
        The status of the response (always 'error').
    error : ErrorResponse
        The error details.

    """

    status: str
    error: ErrorResponse


INTERNAL_SERVER_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Internal server error")
BAD_REQUEST_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Bad request syntax")
NOT_FOUND_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Object not found")
