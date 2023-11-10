import sqlalchemy.exc
from sqlmodel import Session

from ....logging import logger
from ...msg_specs import msg_specs, sql_models
from ..database import engine, retrieve_command
from .msg_processing import process_message

__all__ = []


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


