"""
QCrBox-specific client functionality.

This module contains all QCrBox API-specific code for uploading datasets,
running commands, and retrieving results.
"""

import io
import time
from dataclasses import dataclass

from qcrboxapiclient.api.calculations import get_calculation_by_id, stop_running_calculation
from qcrboxapiclient.api.commands import invoke_command
from qcrboxapiclient.api.datasets import (
    append_to_dataset,
    create_dataset,
    delete_dataset_by_id,
    download_dataset_by_id,
)
from qcrboxapiclient.client import Client
from qcrboxapiclient.models import (
    AppendToDatasetBody,
    CreateDatasetBody,
    InvokeCommandParameters,
    InvokeCommandParametersCommandArguments,
    QCrBoxErrorResponse,
)
from qcrboxapiclient.types import File


@dataclass
class CommandRunResult:
    """Result of running a QCrBox command."""

    status: str
    result_cif: str | None
    status_events: list  # List of CalculationStatusDetails


def upload_file_as_dataset(client: Client, file_text: str, file_name: str) -> tuple[str, str]:
    """
    Upload a CIF file to QCrBox and create a dataset.

    Args:
        client: The QCrBox API client
        file_text: The file content as a string
        file_name: The name for the uploaded file

    Returns
    -------
        Tuple of (dataset_id, data_file_id)

    Raises
    ------
        TypeError: If the upload fails

    """
    fileb = file_text.encode("utf-8")
    file = File(io.BytesIO(fileb), file_name)
    upload_payload = CreateDatasetBody(file)

    response = create_dataset.sync(client=client, body=upload_payload)
    if isinstance(response, QCrBoxErrorResponse) or response is None:
        raise TypeError("Failed to upload file", response)

    dataset_id = response.payload.datasets[0].qcrbox_dataset_id
    data_file_id = response.payload.datasets[0].data_files[file_name].qcrbox_file_id

    return dataset_id, data_file_id


def append_file_to_dataset(client: Client, dataset_id: str, file_text: str, file_name: str) -> str:
    """
    Append a CIF file to an existing QCrBox dataset.

    Args:
        client: The QCrBox API client
        dataset_id: The ID of the dataset to append to
        file_text: The file content as a string
        file_name: The name for the uploaded file

    Returns
    -------
        The data_file_id of the appended file

    Raises
    ------
        TypeError: If the upload fails

    """
    fileb = file_text.encode("utf-8")
    file = File(io.BytesIO(fileb), file_name)
    upload_payload = AppendToDatasetBody(file)

    response = append_to_dataset.sync(client=client, id=dataset_id, body=upload_payload)
    if isinstance(response, QCrBoxErrorResponse) or response is None:
        raise TypeError("Failed to append file", response)

    return response.payload.appended_file.qcrbox_file_id


def run_qcrbox_command(
    client: Client,
    command_name: str,
    application_slug: str,
    application_version: str,
    command_parameters: list,
    timeout_seconds: float,
) -> CommandRunResult:
    """
    Run a QCrBox command and wait for completion.

    Args:
        client: The QCrBox API client
        command_name: Name of the command to run
        application_slug: Slug of the QCrBox application
        application_version: Version of the application
        command_parameters: List of command parameters

    Returns
    -------
        CommandRunResult with status and output

    """
    parameter_dict, input_file_dataset_ids = prepare_qcrbox_parameters(client, command_parameters)

    parameters = InvokeCommandParametersCommandArguments.from_dict(parameter_dict)
    response = invoke_command.sync(
        client=client,
        body=InvokeCommandParameters(
            application_slug=application_slug,
            application_version=application_version,
            command_name=command_name,
            command_arguments=parameters,
        ),
    )

    if isinstance(response, QCrBoxErrorResponse) or response is None:
        raise TypeError("Failed to invoke command", response)

    calculation_id = response.payload.calculation_id
    try:
        # Poll until completion
        final_response = None
        start_time = time.time()
        while final_response is None:
            calc_response = get_calculation_by_id.sync(id=calculation_id, client=client)
            if isinstance(calc_response, QCrBoxErrorResponse) or calc_response is None:
                raise TypeError("Failed to get calculation status", calc_response)

            try:
                final_response = next(
                    resp for resp in calc_response.payload.calculations if resp.status in ("successful", "failed")
                )
            except StopIteration:
                final_response = None
            if start_time + timeout_seconds < time.time():
                stop_running_calculation.sync(id=calculation_id, client=client)
                if final_response is None:
                    return_events = [f"Command execution exceeded timeout of {timeout_seconds} seconds."]
                else:
                    return_events = final_response.status_events + [
                        f"Command execution exceeded timeout of {timeout_seconds} seconds."
                    ]
                return CommandRunResult(
                    status="timeout",
                    result_cif=None,
                    status_events=return_events,
                )
            time.sleep(1)
    except KeyboardInterrupt as e:
        stop_running_calculation.sync(id=calculation_id, client=client)
        raise e
    finally:
        for dataset_id in input_file_dataset_ids:
            delete_dataset_by_id.sync(id=dataset_id, client=client)

    if final_response.status == "successful":
        output_dataset_id = final_response.output_dataset_id
        if not output_dataset_id:
            return CommandRunResult(status="failed", result_cif=None, status_events=final_response.status_events)

        dataset_bytes = download_dataset_by_id.sync(id=output_dataset_id, client=client)
        delete_dataset_by_id.sync(id=output_dataset_id, client=client)

        if isinstance(dataset_bytes, (QCrBoxErrorResponse, type(None), str)):
            raise TypeError("Unexpected dataset bytes type", type(dataset_bytes))

        return CommandRunResult(
            status="successful",
            result_cif=dataset_bytes.decode("utf-8"),
            status_events=final_response.status_events,
        )
    else:
        return CommandRunResult(status="failed", result_cif=None, status_events=final_response.status_events)


def prepare_qcrbox_parameters(client: Client, parameters: list) -> dict[str, object]:
    """
    Prepare QCrBox command parameters, uploading files as needed.

    Args:
        client: The QCrBox API client
        parameters: List of QCrBoxParameter or QCrBoxFileParameter objects

    Returns
    -------
        Dictionary of parameter names to values (with file parameters
        converted to {'data_file_id': file_id})

    """
    from .models import QCrBoxFileParameter

    # Separate file and non-file parameters
    dataset_params = [param for param in parameters if isinstance(param, QCrBoxFileParameter)]

    # Upload files and get their IDs
    data_file_ids = {}
    dataset_ids = []

    if dataset_params:
        # Create dataset with the first file
        first_param = dataset_params[0]
        cif_text = first_param.file_content
        filename = first_param.upload_filename if first_param.upload_filename else f"{first_param.name}.cif"

        dataset_id, data_file_id = upload_file_as_dataset(client, cif_text, filename)
        data_file_ids[first_param.name] = data_file_id
        dataset_ids.append(dataset_id)

        # Append remaining files to the same dataset
        for param in dataset_params[1:]:
            cif_text = param.file_content
            filename = param.upload_filename if param.upload_filename else f"{param.name}.cif"

            data_file_id = append_file_to_dataset(client, dataset_id, cif_text, filename)
            data_file_ids[param.name] = data_file_id

    # Build parameter dictionary
    parameter_dict = {
        param.name: ({"data_file_id": data_file_ids[param.name]} if param.name in data_file_ids else param.value)
        for param in parameters
    }

    return parameter_dict, dataset_ids
