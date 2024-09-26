import json

import nats.js.errors
import sqlalchemy.exc
import svcs
from faststream.nats import NatsBroker
from litestar.exceptions import ClientException
from sqlalchemy.orm import joinedload
from sqlmodel import select

from pyqcrbox import QCRBOX_SVCS_REGISTRY, logger, msg_specs, settings, sql_models
from pyqcrbox.svcs import get_nats_key_value


class CalculationNotFoundError(Exception):
    pass


class CommandNotFoundError(Exception):
    pass


def _retrieve_applications() -> list[sql_models.ApplicationSpecWithCommands]:
    """
    Retrieves list of registered applications from the database.
    """
    model_cls = sql_models.ApplicationSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, slug=slug, version=version)

    with settings.db.get_session() as session:
        # applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        applications = session.scalars(select(model_cls)).all()
        applications_response_models = [app.to_response_model() for app in applications]

    return applications_response_models


def _retrieve_commands() -> list[sql_models.CommandSpecWithParameters]:
    """
    Retrieves list of commands from the database.
    """
    # model_cls = sql_models.CommandSpecDB
    # filter_clauses = [
    #     (name is None) or (model_cls.name == name),
    #     (application_slug is None) or (sql_models.ApplicationSpecDB.slug == application_slug),
    #     (application_version is None) or (sql_models.ApplicationSpecDB.version == application_version),
    # ]
    stmt = select(
        sql_models.CommandSpecDB, sql_models.ApplicationSpecDB.slug, sql_models.ApplicationSpecDB.version
    ).join(
        sql_models.CommandSpecDB.application,
    )

    with settings.db.get_session() as session:
        # commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        commands = session.scalars(stmt).all()
        commands = [cmd.to_response_model() for cmd in commands]

    return commands


def _retrieve_command_by_id(
    cmd_id: int, raise_if_not_found: bool = True
) -> sql_models.CommandSpecWithParameters | None:
    """
    Retrieves details of a command from the database.
    """
    query = select(sql_models.CommandSpecDB).where(sql_models.CommandSpecDB.id == cmd_id)

    with settings.db.get_session() as session:
        try:
            cmd = session.scalars(query).one()
        except sqlalchemy.exc.NoResultFound:
            if raise_if_not_found:
                raise CommandNotFoundError(cmd_id)
            else:
                return None
        cmd_response_model = cmd.to_response_model()

    return cmd_response_model


def verify_command_exists(
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
        except sqlalchemy.exc.NoResultFound:
            error_msg = (
                f"Command not found: {command_name} "
                f"(application: {application_slug!r}, "
                f"version: {application_version!r})"
            )
            logger.error(error_msg)
            raise ClientException(error_msg)
        except sqlalchemy.exc.MultipleResultsFound:
            error_msg = (
                f"Found multiple candidates for command: {command_name}. "
                f"Please supply the application's slug (and version if needed) "
                f"to disambiguate between the matching commands."
            )
            logger.error(error_msg)
            raise ClientException(error_msg)

    return cmd_spec_db


def validate_arguments_against_command_parameters(cmd_spec_db: sql_models.CommandSpecDB, arguments: dict) -> None:
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


async def _invoke_command(data: sql_models.CommandInvocationCreate) -> dict:
    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        nats_broker = await con.aget(NatsBroker)

    cmd_spec_db = verify_command_exists(data.application_slug, data.application_version, data.command_name)
    validate_arguments_against_command_parameters(cmd_spec_db, data.arguments)

    msg = msg_specs.InvokeCommandNATS(
        application_slug=cmd_spec_db.application.slug,
        application_version=cmd_spec_db.application.version,
        command_name=cmd_spec_db.name,
        arguments=data.arguments,
    )

    response_json = await nats_broker.publish(msg, "server.cmd.handle_command_invocation_by_user", rpc=True)
    return response_json


def _get_calculation_info() -> list[sql_models.CalculationResponseModel]:
    with settings.db.get_session() as session:
        calculations_db = session.exec(select(sql_models.CalculationDB)).all()
        return [c.to_response_model() for c in calculations_db]


async def _get_calculation_info_by_calculation_id(calculation_id: str) -> dict:
    # with settings.db.get_session() as session:
    #     try:
    #         calc = session.exec(
    #             select(sql_models.CalculationDB).where(sql_models.CalculationDB.calculation_id == calculation_id)
    #         ).one()
    #         pass
    #     except sqlalchemy.orm.exc.NoResultFound:
    #         return Response(
    #             {"msg": f"No calculation exists with id={calculation_id}"},
    #             status_code=404)

    try:
        kv_calculation_status = await get_nats_key_value(bucket="calculation_status")
        calc_status_info_str = (await kv_calculation_status.get(calculation_id)).value
        return json.loads(calc_status_info_str)
    except nats.js.errors.KeyNotFoundError:
        raise CalculationNotFoundError(calculation_id)
