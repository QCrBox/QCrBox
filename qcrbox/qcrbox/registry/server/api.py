import sqlalchemy.exc

from fastapi import Request, HTTPException
from sqlalchemy import select
from sqlmodel import Session

from .database import engine
from .messaging.invoke_command import _invoke_command_impl
from .router import router
from ..msg_specs import msg_specs, sql_models

__all__ = []


@router.get("/")
async def hello_http(_: Request):
    return "Hello from QCrBox!"


@router.get("/ping")
async def ping(_: Request):
    return {"status": "success", "message": "pong"}


@router.get("/applications/", response_model=list[
    sql_models.QCrBoxApplicationRead])
def get_registered_applications():
    with Session(engine) as session:
        applications = session.scalars(select(
            sql_models.QCrBoxApplicationDB)).all()
        return applications


@router.get("/commands/", response_model=list[sql_models.QCrBoxCommandRead])
def get_registered_commands():
    with Session(engine) as session:
        commands = session.exec(select(sql_models.QCrBoxCommandDB)).all()
        return commands


@router.get("/containers/", response_model=list[sql_models.QCrBoxContainerRead])
def get_registered_containers():
    with Session(engine) as session:
        commands = session.exec(select(sql_models.QCrBoxContainerDB)).all()
        return commands


@router.get("/calculations/", response_model=list[
    sql_models.QCrBoxCalculationRead])
def get_all_calculations():
    with Session(engine) as session:
        calculations = session.scalars(select(
            sql_models.QCrBoxCalculationDB)).all()
        return calculations


@router.get("/calculations/{calculation_id}/", response_model=sql_models.QCrBoxCalculationRead)
async def get_single_calculation(calculation_id: int):
    with Session(engine) as session:
        statement = select(sql_models.QCrBoxCalculationDB).where(
            sql_models.QCrBoxCalculationDB.id == calculation_id)
        try:
            calc = session.exec(statement).one()
        except sqlalchemy.exc.NoResultFound:
            error_response = dict(status="error", msg=f"Calculation not found")
            raise HTTPException(status_code=404, detail=error_response)

        routing_key = calc.container.routing_key__registry_to_application
        msg = msg_specs.GetCalculationStatusDetails(
            action="get_calculation_status_details",
            payload=msg_specs.GetCalculationStatusDetailsPayload(calculation_id=calculation_id),
        )
        response = await router.broker.publish(
            msg, routing_key=routing_key, callback=True, callback_timeout=60.0, raise_timeout=True
        )
        calc_with_status_details = sql_models.QCrBoxCalculationRead(**calc.dict(), status_details=response["payload"])
        return calc_with_status_details


@router.post("/invoke_command/")
async def invoke_command(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    return await _invoke_command_impl(msg)
