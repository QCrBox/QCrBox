from typing import Annotated

import sqlalchemy.exc
from faststream.nats import NatsBroker
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body
from sqlalchemy.orm import joinedload
from sqlmodel import select

from pyqcrbox import logger, msg_specs, settings, sql_models
from pyqcrbox.data_management import DataManager, DatasetResponse
from pyqcrbox.data_management.data_file import DataFileResponse
from pyqcrbox.sql_models.calculation import CalculationResponse


class CalculationNotFoundError(Exception):
    """Exception raised when a calculation is not found."""


class CommandNotFoundError(Exception):
    """Exception raised when a command is not found."""


def _validate_arguments_against_command_parameters(cmd_spec_db: sql_models.CommandSpecDB, arguments: dict) -> None:
    """Validate that the provided arguments match the command's parameter specification.

    Parameters
    ----------
    cmd_spec_db : sql_models.CommandSpecDB
        The command specification from the database.
    arguments : dict
        The arguments provided for the command invocation.

    """
    params = list(cmd_spec_db.parameters.values())
    required_param_names = set(p["name"] for p in params if p["required"] is True)
    all_param_names = set(cmd_spec_db.parameters.keys())
    arg_names = set(arguments.keys())

    if not required_param_names.issubset(arg_names):
        params_not_supplied = required_param_names.difference(arg_names)
        missing_args = ", ".join(repr(name) for name in params_not_supplied)
        error_msg = f"The following required arguments are missing: {missing_args}"
        logger.error(error_msg)
        raise ClientException(error_msg)

    if not arg_names.issubset(all_param_names):
        invalid_args = arg_names.difference(all_param_names)
        invalid_args_str = ", ".join(repr(name) for name in invalid_args)
        error_msg = f"Invalid arguments: {invalid_args_str}"
        logger.error(error_msg)
        raise ClientException(error_msg)


def _verify_command_exists(
    application_slug: str, application_version: str | None, command_name: str | None
) -> sql_models.CommandSpecDB:
    """Verify that a command exists for the given application slug, version, and command name.

    Parameters
    ----------
    application_slug : str
        The slug of the application.
    application_version : str | None
        The version of the application (optional).
    command_name : str | None
        The name of the command.

    Returns
    -------
    sql_models.CommandSpecDB
        The command specification from the database.

    """
    with settings.db.get_session() as session:
        try:
            cmd_spec_db = session.exec(
                select(sql_models.CommandSpecDB)
                .join(sql_models.ApplicationSpecDB)
                .options(joinedload(sql_models.CommandSpecDB.application))
                .where(
                    application_slug is None or (sql_models.ApplicationSpecDB.slug == application_slug),
                    application_version is None or (sql_models.ApplicationSpecDB.version == application_version),
                    sql_models.CommandSpecDB.name == command_name,
                )
            ).one()
        except sqlalchemy.exc.NoResultFound as exc:
            error_msg = (
                f"Command or application not found: "
                f"command={command_name!r}, "
                f"application: {application_slug!r}, "
                f"version: {application_version!r}"
            )
            logger.error(error_msg)
            raise ClientException(error_msg) from exc
        except sqlalchemy.exc.MultipleResultsFound as exc:
            error_msg = (
                f"Found multiple candidates for command: {command_name}. "
                f"Please supply the application's slug (and version if needed) "
                f"to disambiguate between the matching commands."
            )
            logger.error(error_msg)
            raise ClientException(error_msg) from exc

    return cmd_spec_db


async def close_interactive_session(
    session_id: str, *, nats_broker: NatsBroker, data_manager: DataManager
) -> msg_specs.CloseInteractiveSessionResponse:
    """Close an interactive session by sending a close request via NATS.

    Parameters
    ----------
    session_id : str
        The ID of the interactive session to close.
    nats_broker : NatsBroker
        The NATS broker instance.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    msg_specs.CloseInteractiveSessionResponse
        The response from the client after closing the session.

    """
    session_info = await data_manager.get_interactive_session(session_id)

    msg = msg_specs.CloseInteractiveSessionNATS(session_id=session_id)
    response_json = await nats_broker.publish(
        msg,
        f"{session_info.client_private_inbox}.interactive_session.close",
        rpc=True,
    )

    response = msg_specs.CloseInteractiveSessionResponse(**response_json)
    return response


async def export_data_file(data_file_id: str, *, data_manager: DataManager) -> tuple[bytes, str]:
    """Export a data file's contents and filename by its ID.

    Parameters
    ----------
    data_file_id : str
        The ID of the data file to export.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    tuple[bytes, str]
        The file contents and the filename.

    """
    data_file = await data_manager.get_data_file_contents(data_file_id)
    file_name = (await data_manager.get_data_file(data_file_id)).filename

    return data_file, file_name


async def export_dataset(dataset_id: str, *, data_manager: DataManager) -> tuple[bytes, str]:
    """Export a dataset's contents and filename by its ID.

    This currently only supports exporting datasets which contain only a single
    data file.

    Parameters
    ----------
    dataset_id : str
        The ID of the dataset to export.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    tuple[bytes, str]
        The file contents and the filename.

    """
    dataset_info = await data_manager.get_dataset(dataset_id)

    if dataset_info.is_empty:
        msg = f"Dataset {dataset_id} is empty"
        raise ValueError(msg)

    if dataset_info.contains_multiple_files:
        msg = "Downloading datasets with multiple files is not supported yet"
        raise NotImplementedError(msg)
    else:
        data_file = dataset_info.first_data_file
        file_name = data_file.filename
        file_contents = await data_manager.get_data_file_contents(data_file.qcrbox_file_id)

    return file_contents, file_name


async def delete_dataset(dataset_id: str, *, data_manager: DataManager) -> None:
    """Delete a dataset by its ID.

    Parameters
    ----------
    dataset_id : str
        The ID of the dataset to delete.
    data_manager : DataManager
        The data file manager instance.

    """
    await data_manager.delete_dataset(dataset_id)


async def get_calculations(*, data_manager: DataManager) -> list[CalculationResponse]:
    """Get all calculations from the data file manager.

    Parameters
    ----------
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    list[CalculationResponse]
        A list of calculation response models.

    """
    calculations = await data_manager.get_calculations()
    return [c.to_response_model() for c in calculations]


async def get_calculation_by_calculation_id(calculation_id: str, *, data_manager: DataManager) -> CalculationResponse:
    """Get a calculation by its calculation ID.

    Parameters
    ----------
    calculation_id : str
        The ID of the calculation to retrieve.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    CalculationResponse
        The calculation response model.

    """
    try:
        calculation = await data_manager.get_calculation(calculation_id)
    except KeyError as exc:
        raise CalculationNotFoundError from exc

    return calculation.to_response_model()


async def get_data_file_info(data_file_id: str, *, data_manager: DataManager) -> DataFileResponse:
    """Get metadata for a data file by its ID.

    Parameters
    ----------
    data_file_id : str
        The ID of the data file.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    DataFileResponse
        The data file info response model.

    """
    data_file = await data_manager.get_data_file(data_file_id)
    return data_file.to_response_model()


async def get_data_files(*, data_manager: DataManager) -> list[DataFileResponse]:
    """Get all data files in the data file manager.

    Parameters
    ----------
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    list[DataFileResponse]
        A list of data file info response models.

    """
    data_files = await data_manager.get_data_files()
    return [f.to_response_model() for f in data_files]


async def get_dataset_info(dataset_id: str, *, data_manager: DataManager) -> DatasetResponse:
    """Get metadata for a dataset by its ID.

    Parameters
    ----------
    dataset_id : str
        The ID of the dataset.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    DatasetInfoResponse
        The dataset info response model.

    """
    dataset_info = await data_manager.get_dataset(dataset_id)
    return dataset_info.to_response_model()


async def get_datasets(*, data_manager: DataManager) -> list[DatasetResponse]:
    """Get all datasets in the data file manager.

    Parameters
    ----------
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    list[DatasetInfoResponse]
        A list of dataset info response models.

    """
    datasets = await data_manager.get_datasets()
    return [d.to_response_model() for d in datasets]


async def get_interactive_session_info(session_id: str, *, data_manager: DataManager):
    """Get interactive session info by its ID.

    Parameters
    ----------
    session_id : str
        The ID of the interactive session.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    Any
        The interactive session info response model.

    """
    session_info = await data_manager.get_interactive_session(session_id)
    return session_info.to_response_model()


async def get_interactive_sessions(*, data_manager: DataManager):
    """Get all interactive sessions in the data file manager.

    Parameters
    ----------
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    list
        A list of interactive session info response models.

    """
    session_info = await data_manager.get_interactive_sessions()
    return [s.to_response_model() for s in session_info]


async def import_data_file(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)], *, data_manager: DataManager
) -> str:
    """Import a data file from an uploaded file into the data file manager.

    Parameters
    ----------
    data : UploadFile
        The uploaded file to import.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    str
        The ID of the imported data file.

    """
    qcrbox_data_file_id = await data_manager._import_bytes(await data.read(), filename=data.filename)
    return qcrbox_data_file_id


async def import_dataset(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)], *, data_manager: DataManager
) -> str:
    """Import a data file into a dataset from an uploaded file.

    Parameters
    ----------
    data : UploadFile
        The uploaded file to import as a dataset.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    str
        The ID of the imported dataset.

    """
    qcrbox_data_file_id = await data_manager._import_bytes(await data.read(), filename=data.filename)
    qcrbox_dataset_id = await data_manager.create_dataset_from_data_file(qcrbox_data_file_id)
    return qcrbox_dataset_id


async def invoke_command(data: sql_models.CommandInvocationCreate, *, nats_broker: NatsBroker) -> dict:
    """Invoke a command by sending a request via NATS.

    Parameters
    ----------
    data : sql_models.CommandInvocationCreate
        The command invocation creation data.
    nats_broker : NatsBroker
        The NATS broker instance.

    Returns
    -------
    dict
        The response from the server after invoking the command.

    """
    cmd_spec_db = _verify_command_exists(data.application_slug, data.application_version, data.command_name)
    _validate_arguments_against_command_parameters(cmd_spec_db, data.arguments)

    msg = msg_specs.InvokeCommandNATS(
        application_slug=cmd_spec_db.application.slug,
        application_version=cmd_spec_db.application.version,
        command_name=cmd_spec_db.name,
        command_arguments=data.arguments,
    )
    response_json = await nats_broker.publish(msg, "server.cmd.handle_command_invocation_by_user", rpc=True)

    if not response_json:
        exc_msg = f"No response from server when trying to invoke command: response_json {response_json}"
        logger.error(f"{exc_msg}")
        raise ValueError(exc_msg)

    return response_json


async def stop_running_calculation(
    calculation_id: str, *, nats_broker: NatsBroker, data_manager: DataManager
) -> msg_specs.StoppedCalculationResponse:
    """Stop a running calculation by sending a stop request via NATS.

    Parameters
    ----------
    calculation_id : str
        The ID of the calculation to stop.
    nats_broker : NatsBroker
        The NATS broker instance.
    data_manager : DataManager
        The data file manager instance.

    Returns
    -------
    msg_specs.StoppedCalculationResponse
        The response from the client after stopping the calculation.

    """
    calculation = await data_manager.get_calculation(calculation_id)

    msg = msg_specs.StopRunningCalculationMsg(calculation_id=calculation_id)
    response_json = await nats_broker.publish(
        msg,
        f"{calculation.client_private_inbox}.cmd.stop",
        rpc=True,
    )

    return msg_specs.StoppedCalculationResponse(**response_json)


def retrieve_applications() -> list[sql_models.ApplicationSpecWithCommandsResponse]:
    """Retrieve all registered applications from the SQL database.

    Returns
    -------
    list[sql_models.ApplicationSpecWithCommandsResponse]
        A list of application response models with commands.

    """
    model_cls = sql_models.ApplicationSpecDB
    with settings.db.get_session() as session:
        applications = session.scalars(select(model_cls)).all()
        applications_response_models = [app.to_response_model() for app in applications]
    return applications_response_models


def retrieve_command_by_id(
    cmd_id: int, raise_if_not_found: bool = True
) -> sql_models.CommandSpecWithParametersResponse | None:
    """Retrieve a command by its ID from the database.

    Parameters
    ----------
    cmd_id : int
        The ID of the command to retrieve.
    raise_if_not_found : bool, optional
        Whether to raise an exception if the command is not found (default: True).

    Returns
    -------
    sql_models.CommandSpecWithParametersResponse | None
        The command response model, or None if not found and not raising.

    Raises
    ------
    CommandNotFoundError
        If the command is not found and raise_if_not_found is True.

    """
    query = select(sql_models.CommandSpecDB).where(sql_models.CommandSpecDB.id == cmd_id)
    with settings.db.get_session() as session:
        try:
            cmd = session.scalars(query).one()
        except sqlalchemy.exc.NoResultFound as exc:
            if raise_if_not_found:
                raise CommandNotFoundError(cmd_id) from exc
            else:
                return None
        cmd_response_model = cmd.to_response_model()
    return cmd_response_model


def retrieve_commands() -> list[sql_models.CommandSpecWithParametersResponse]:
    """Retrieve all commands for registered applications in the SQL database.

    Returns
    -------
    list[sql_models.CommandSpecWithParametersResponse]
        A list of command response models with parameters.

    """
    stmt = select(
        sql_models.CommandSpecDB, sql_models.ApplicationSpecDB.slug, sql_models.ApplicationSpecDB.version
    ).join(
        sql_models.CommandSpecDB.application,
    )
    with settings.db.get_session() as session:
        commands = session.scalars(stmt).all()
        commands = [cmd.to_response_model() for cmd in commands]
    return commands
