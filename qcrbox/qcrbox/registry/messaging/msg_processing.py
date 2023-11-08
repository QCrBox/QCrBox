from functools import singledispatch

import sqlalchemy.exc
from sqlmodel import Session

from ...logging import logger
from ..database import sql_models, engine, retrieve_application, retrieve_command
from . import msg_specs


@singledispatch
def process_message(msg):
    """
    Fallback processing definition, in case none of the others match.
    """
    logger.warning("TODO: add a more informative error message here (and return a proper QCrBoxGenericResponse)!")
    raise NotImplementedError(f"Cannot process incoming message: {msg}")


@process_message.register
def _(msg: msg_specs.RegisterApplication) -> msg_specs.QCrBoxGenericResponse:
    """
    Register a new application and store it in the database
    """
    logger.info(f"Registering application: {msg}")
    data = msg.payload.dict()

    try:
        application_db = retrieve_application(name=data["name"], version=data["version"])
    except sqlalchemy.exc.NoResultFound:
        application_db = sql_models.QCrBoxApplicationDB(**data)
        with Session(engine) as session:
            session.add(application_db)
            session.commit()
            session.refresh(application_db)

    assigned_application_id = application_db.id

    container_db = sql_models.QCrBoxContainerDB(
        qcrbox_id=data["container_qcrbox_id"],
        application_id=application_db.id,
        routing_key__registry_to_application=data["routing_key__registry_to_application"],
        status=data["container_startup_status"],
    )

    try:
        with Session(engine) as session:
            session.add(container_db)
            session.commit()
            session.refresh(container_db)
    except sqlalchemy.exc.IntegrityError as exc:
        orig_error_msg = exc.args[0]
        error_msg = (
            f"Could not register container with qcrbox_id {container_db.qcrbox_id!r} "
            f"for application {msg.payload.name!r}. Original error message: {orig_error_msg!r}"
        )
        return msg_specs.RegisterApplicationResponse(response_to="register_application", status="error", msg=error_msg)

    logger.info(f"Successfully registered application {data['name']!r} (id: {assigned_application_id!r})")
    logger.info(
        f"Successfully registered container with qcrbox_id={data['container_qcrbox_id']!r} (id: {container_db.id!r})"
    )
    logger.debug(f"Routing key registry -> application: {data['routing_key__registry_to_application']!r}")
    return msg_specs.RegisterApplicationResponse(
        response_to="register_application",
        status="success",
        payload=msg_specs.RegisterApplicationPayload(
            application_id=assigned_application_id,
            container_id=container_db.id,
        ),
    )


@process_message.register
def _(msg: msg_specs.RegisterCommand) -> msg_specs.QCrBoxGenericResponse:
    """
    Register a new command
    """
    logger.info(f"Registering new command: {msg.payload}")
    logger.warning(f"FIXME: verify that the application_id refers to a valid, registered application")

    data = msg.payload.dict()
    try:
        cmd_db = retrieve_command(name=data["name"], parameters=data["parameters"], application_id=data["application_id"])
    except sqlalchemy.exc.NoResultFound:
        cmd_db = sql_models.QCrBoxCommandDB(**data)
        with Session(engine) as session:
            session.add(cmd_db)
            session.commit()
            session.refresh(cmd_db)

    assigned_command_id = cmd_db.id

    return msg_specs.QCrBoxGenericResponse(
        response_to="register_command", status="success", payload={"command_id": assigned_command_id}
    )
