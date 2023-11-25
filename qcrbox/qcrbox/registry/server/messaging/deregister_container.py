import sqlalchemy.exc
from sqlmodel import Session

from ....logging import logger
from qcrbox.common import msg_specs, sql_models
from ..database import engine, retrieve_container
from .msg_processing import process_message

__all__ = []


@process_message.register
def _(msg: msg_specs.DeregisterContainer) -> msg_specs.QCrBoxGenericResponse:
    """
    Deregister a previouly registered container (usually because it was shut down).
    """
    logger.info(f"Deregistering container: {msg}")
    data = msg.payload.dict()

    try:
        container_db = retrieve_container(qcrbox_id=data["container_qcrbox_id"])
    except sqlalchemy.exc.NoResultFound:
        raise RuntimeError("TODO: handle this case properly")

    with Session(engine) as session:
        session.delete(container_db)
        session.commit()

    logger.info(f"Successfully deregistered container with qcrbox_id={data['container_qcrbox_id']!r}  (id: {container_db.id!r})"")
    return msg_specs.DeegisterContainerResponse(
        response_to="register_application",
        status="success",
        payload=msg_specs.RegisterApplicationPayload(
            application_id=assigned_application_id,
            container_id=container_db.id,
        ),
    )
