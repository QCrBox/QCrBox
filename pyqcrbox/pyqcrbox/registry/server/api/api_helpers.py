from typing import Annotated

import sqlalchemy.exc
import svcs
from faststream.nats import NatsBroker
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body
from sqlalchemy.orm import joinedload
from sqlmodel import select

from pyqcrbox import QCRBOX_SVCS_REGISTRY, logger, msg_specs, settings, sql_models
from pyqcrbox.data_management import DatasetResponse
from pyqcrbox.data_management.data_file import DataFileMetadataResponse
from pyqcrbox.debug import eel_logging
from pyqcrbox.services import get_data_file_manager, get_nats_broker
from pyqcrbox.sql_models.calculation import CalculationNatsResponseModel


class CalculationNotFoundError(Exception):
    pass


class CommandNotFoundError(Exception):
    pass


@eel_logging
def _validate_arguments_against_command_parameters(cmd_spec_db: sql_models.CommandSpecDB, arguments: dict) -> None:
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


@eel_logging
def _verify_command_exists(
    application_slug: str, application_version: str | None, command_name: str | None
) -> sql_models.CommandSpecDB:
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


@eel_logging
async def close_interactive_session(session_id: str) -> msg_specs.CloseInteractiveSessionResponseNATS:
    nats_broker = await get_nats_broker()
    data_manager = await get_data_file_manager()
    session_info = await data_manager.get_interactive_session_info(session_id)

    msg = msg_specs.CloseInteractiveSessionNATS(session_id=session_id)
    response_json = await nats_broker.publish(
        msg,
        f"{session_info.client_private_inbox}.interactive_session.close",
        rpc=True,
    )
    response = msg_specs.CloseInteractiveSessionResponseNATS(**response_json)
    return response


@eel_logging
async def export_data_file(data_file_id: str) -> tuple[bytes, str]:
    # TODO: Create response model instead of Tuple
    data_file_manager = await get_data_file_manager()
    data_file = await data_file_manager.get_file_contents(data_file_id)
    file_name = (await data_file_manager.get_file_metadata(data_file_id)).filename

    return data_file, file_name


@eel_logging
async def export_dataset(dataset_id: str) -> tuple[bytes, str]:
    # TODO: Create response model instead of Tuple
    data_file_manager = await get_data_file_manager()
    dataset_info = await data_file_manager.get_dataset_info(dataset_id)

    if dataset_info.is_empty:
        msg = f"Dataset {dataset_id} is empty"
        raise ValueError(msg)

    if dataset_info.contains_multiple_files:
        msg = "Downloading datasets with multiple files is not supported yet"
        raise NotImplementedError(msg)
    else:
        data_file = dataset_info.first_data_file
        file_name = data_file.filename
        file_contents = await data_file_manager.get_file_contents(data_file.qcrbox_file_id)

    return file_contents, file_name


@eel_logging
async def delete_dataset(dataset_id: str) -> None:
    data_file_manager = await get_data_file_manager()
    await data_file_manager.delete_dataset(dataset_id)


@eel_logging
async def get_calculations() -> list[CalculationNatsResponseModel]:
    data_file_manager = await get_data_file_manager()
    calculations = await data_file_manager.get_calculations()

    return [c.to_response_model() for c in calculations]


@eel_logging
async def get_calculation_by_calculation_id(calculation_id: str) -> CalculationNatsResponseModel:
    data_file_manager = await get_data_file_manager()
    try:
        calculation = await data_file_manager.get_calculation_details(calculation_id)
    except KeyError as exc:
        raise CalculationNotFoundError from exc

    return calculation


@eel_logging
async def get_data_file_info(data_file_id: str) -> DataFileMetadataResponse:
    data_file_manager = await get_data_file_manager()
    data_file = await data_file_manager.get_file_metadata(data_file_id)
    return data_file.to_response_model()


@eel_logging
async def get_data_files() -> list[DataFileMetadataResponse]:
    data_file_manager = await get_data_file_manager()
    data_files = await data_file_manager.get_data_files()
    return [f.to_response_model() for f in data_files]


@eel_logging
async def get_dataset_info(dataset_id: str) -> DatasetResponse:
    data_file_manager = await get_data_file_manager()
    dataset_info = await data_file_manager.get_dataset_info(dataset_id)
    return dataset_info.to_response_model()


@eel_logging
async def get_datasets() -> list[DatasetResponse]:
    data_file_manager = await get_data_file_manager()
    datasets = await data_file_manager.get_datasets()
    return [d.to_response_model() for d in datasets]


@eel_logging
async def get_interactive_session_info(session_id: str):
    data_file_manager = await get_data_file_manager()
    session_info = await data_file_manager.get_interactive_session_info(session_id)
    return session_info.to_response_model()


@eel_logging
async def get_interactive_sessions():
    data_file_manager = await get_data_file_manager()
    session_info = await data_file_manager.get_interactive_sessions()
    return [s.to_response_model() for s in session_info]


@eel_logging
async def import_data_file(data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]) -> str:
    data_file_manager = await get_data_file_manager()
    qcrbox_data_file_id = await data_file_manager.import_bytes(await data.read(), filename=data.filename)
    logger.info(f"Data file imported: filename={data.filename!r} id={qcrbox_data_file_id!r}")
    return qcrbox_data_file_id


@eel_logging
async def import_dataset(data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]) -> str:
    data_file_manager = await get_data_file_manager()
    qcrbox_data_file_id = await data_file_manager.import_bytes(await data.read(), filename=data.filename)
    qcrbox_dataset_id = await data_file_manager.create_dataset_from_data_file(qcrbox_data_file_id)
    logger.info(f"Dataset imported: id={qcrbox_dataset_id}, files=[id={qcrbox_data_file_id} filename={data.filename}]")
    return qcrbox_dataset_id


@eel_logging
async def invoke_command(data: sql_models.CommandInvocationCreate) -> dict:
    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        nats_broker = await con.aget(NatsBroker)

    cmd_spec_db = _verify_command_exists(data.application_slug, data.application_version, data.command_name)
    _validate_arguments_against_command_parameters(cmd_spec_db, data.arguments)

    msg = msg_specs.InvokeCommandNATS(
        application_slug=cmd_spec_db.application.slug,
        application_version=cmd_spec_db.application.version,
        command_name=cmd_spec_db.name,
        arguments=data.arguments,
    )
    response_json = await nats_broker.publish(msg, "server.cmd.handle_command_invocation_by_user", rpc=True)

    if not response_json:
        exc_msg = "No response from server when trying to invoke command"
        raise ValueError(exc_msg)

    return response_json


@eel_logging
def retrieve_applications() -> list[sql_models.ApplicationSpecWithCommands]:
    model_cls = sql_models.ApplicationSpecDB
    with settings.db.get_session() as session:
        applications = session.scalars(select(model_cls)).all()
        applications_response_models = [app.to_response_model() for app in applications]
    return applications_response_models


@eel_logging
def retrieve_command_by_id(cmd_id: int, raise_if_not_found: bool = True) -> sql_models.CommandSpecWithParameters | None:
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


@eel_logging
def retrieve_commands() -> list[sql_models.CommandSpecWithParameters]:
    stmt = select(
        sql_models.CommandSpecDB, sql_models.ApplicationSpecDB.slug, sql_models.ApplicationSpecDB.version
    ).join(
        sql_models.CommandSpecDB.application,
    )
    with settings.db.get_session() as session:
        commands = session.scalars(stmt).all()
        commands = [cmd.to_response_model() for cmd in commands]
    return commands
