import json

import nats.js.errors
from sqlmodel import select

from pyqcrbox import settings, sql_models
from pyqcrbox.svcs import get_nats_key_value


class CalculationNotFoundError(Exception):
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
