import sqlalchemy.exc
from sqlmodel import Session, select

from ...logging import logger
from ..database import sql_models, engine
from ..api import router
from .msg_processing import process_message
from . import msg_specs

__all__ = []


@process_message.register
async def _(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    """
    Invoke a registered command with given arguments.
    """
    return await _invoke_command_impl(msg)


async def _invoke_command_impl(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    logger.info(f"Invoking command: {msg}")

    with Session(engine) as session:
        try:
            command = session.exec(
                select(sql_models.QCrBoxCommandDB).where(sql_models.QCrBoxCommandDB.id == msg.payload.command_id)
            ).one()
        except sqlalchemy.exc.NoResultFound:
            error_msg = f"No command found with command_id={msg.payload.command_id}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="invoke_command", status="error", msg=error_msg)

        logger.debug(f"Found {command=}")
        logger.debug(f"{command.application=}")

        new_calculation_db = sql_models.QCrBoxCalculationDB(**msg.payload.dict())
        session.add(new_calculation_db)
        session.commit()
        session.refresh(new_calculation_db)
        assigned_calculation_id = new_calculation_db.id

        routing_key = new_calculation_db.container.routing_key__registry_to_application
        logger.debug(f"{routing_key=}")

        msg_execute_calculation = msg_specs.ExecuteCalculation(
            action="execute_calculation",
            payload=msg_specs.ExecuteCalculationPayload(
                command_id=msg.payload.command_id,
                calculation_id=assigned_calculation_id,
                arguments=msg.payload.arguments,
                container_qcrbox_id=msg.payload.container_qcrbox_id,
            ),
        )

        response = await router.broker.publish(
            msg_execute_calculation,
            routing_key=routing_key,
            callback=True,
            callback_timeout=2.0,
            raise_timeout=True,
        )
        logger.debug(f"Response for command invocation: {response=}")

    return msg_specs.QCrBoxGenericResponse(
        response_to="invoke_command", status="success", payload={"calculation_id": assigned_calculation_id}
    )
