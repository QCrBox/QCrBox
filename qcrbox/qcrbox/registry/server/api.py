# SPDX-License-Identifier: MPL-2.0

from typing import Optional

import sqlalchemy.exc
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlmodel import Session

from qcrbox.common import msg_specs, sql_models

from ...logging import logger
from .database import engine
from .message_processing.invoke_command import _invoke_command_impl
from .router import router
from .status_checks import update_status_of_all_containers

__all__ = []


fastapi_app = FastAPI(lifespan=router.lifespan_context, logger=logger)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@router.get("/")
async def hello_http(_: Request):
    return "Hello from QCrBox!"


@router.get("/ping")
async def ping(_: Request):
    return {"status": "success", "message": "pong"}


def construct_filter_clauses(model_cls, **kwargs):
    filter_clauses = []
    for name, value in kwargs.items():
        if value is not None:
            filter_clauses.append(getattr(model_cls, name) == value)
    return filter_clauses


@router.get("/applications/", response_model=list[sql_models.QCrBoxApplicationRead])
def get_registered_applications(name: Optional[str] = None, version: Optional[str] = None):
    model_cls = sql_models.QCrBoxApplicationDB
    filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with Session(engine) as session:
        applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        return applications


@router.get("/commands/", response_model=list[sql_models.QCrBoxCommandRead])
def get_registered_commands(name: Optional[str] = None, application_id: Optional[int] = None):
    model_cls = sql_models.QCrBoxCommandDB
    filter_clauses = construct_filter_clauses(model_cls, name=name, application_id=application_id)

    with Session(engine) as session:
        commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        return commands


@router.get("/containers/", response_model=list[sql_models.QCrBoxContainerRead])
def get_registered_containers(application_id: Optional[int] = None):
    model_cls = sql_models.QCrBoxContainerDB
    filter_clauses = construct_filter_clauses(model_cls, application_id=application_id)

    with Session(engine) as session:
        containers = session.scalars(select(model_cls).where(*filter_clauses)).all()
        return containers


@router.post("/containers/status_update")
async def run_containers_status_update(timeout: float = 1.0):
    await update_status_of_all_containers(callback_timeout=timeout)


@router.get("/calculations/", response_model=list[sql_models.QCrBoxCalculationRead])
def get_all_calculations():
    with Session(engine) as session:
        calculations = session.scalars(select(sql_models.QCrBoxCalculationDB)).all()
        return calculations


@router.get("/calculations/{calculation_id}/", response_model=sql_models.QCrBoxCalculationRead)
async def get_single_calculation(calculation_id: int):
    with Session(engine) as session:
        statement = select(sql_models.QCrBoxCalculationDB).where(sql_models.QCrBoxCalculationDB.id == calculation_id)
        try:
            calc = session.exec(statement).scalar_one()
        except sqlalchemy.exc.NoResultFound:
            error_response = dict(status="error", msg="Calculation not found")
            raise HTTPException(status_code=404, detail=error_response)

        routing_key = calc.container.routing_key__registry_to_application
        msg = msg_specs.GetCalculationStatusDetails(
            action="get_calculation_status_details",
            payload=msg_specs.GetCalculationStatusDetailsPayload(calculation_id=calculation_id),
        )
        try:
            response = await router.broker.publish(
                msg, routing_key=routing_key, callback=True, callback_timeout=5.0, raise_timeout=True
            )
            status_details = response["payload"]
        except TimeoutError:
            status_details = sql_models.QCrBoxCalculationStatusDetails(
                status="error",
                details={
                    "message": (
                        f"Connection to the container which executed the calculation "
                        f"timed out (routing key: {routing_key!r}."
                    )
                },
            )
        calc_with_status_details = sql_models.QCrBoxCalculationRead(**calc.dict(), status_details=status_details)
        return calc_with_status_details


@router.post("/invoke_command/")
async def invoke_command(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    return await _invoke_command_impl(msg)
