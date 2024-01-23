import sqlalchemy.exc
from sqlmodel import Session, select

from ....logging import logger
from qcrbox.common import msg_specs, sql_models
from ..router import router
from ..database import engine
from .base import process_message

__all__ = []


@process_message.register
async def _(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    """
    Invoke a registered command with given arguments.
    """
    # Note: the reason why the implementation is in a separate function is so
    # that we can re-use it in the API handler for the /invoke_command endpoint.
    return await _invoke_command_impl(msg)


async def _invoke_command_impl(msg: msg_specs.InvokeCommand) -> msg_specs.QCrBoxGenericResponse:
    logger.info(f"Invoking command: {msg}")

    msg_payload = msg.payload.copy(deep=True)

    with Session(engine) as session:
        try:
            command = session.exec(
                select(sql_models.QCrBoxCommandDB).where(sql_models.QCrBoxCommandDB.id == msg_payload.command_id)
            ).one()
        except sqlalchemy.exc.NoResultFound:
            error_msg = f"No command found with command_id={msg_payload.command_id}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="invoke_command", status="error", msg=error_msg)

        logger.debug(f"Found {command=}")
        logger.debug(f"{command.application=}")

        logger.debug(f"{msg_payload.container_qcrbox_id=}")

        # TODO: look up default parameters and merge them with the dict passed as 'with_args' in `msg_payload`
        #       return an error if there are any parameters for which neither a default value exists nor an explicit
        #       value was provided.
        #       Currently this check only happens once the "execute_calculation" message has been sent below
        #       and it is processed in qcrbox/qcrbox/registry/client/message_processing/execute_calculation.py, but this
        #       should happen here so that we can return an appropriate error message (currently we return "success",
        #       which is highly misleading).

        if msg_payload.container_qcrbox_id is None:
            # If no container is explicitly specified, grab the first available one.
            # FIXME: this is a hack just to get things working for now; we should
            #        handle this in a smarter way in the future.
            container_to_use = session.exec(
                select(sql_models.QCrBoxContainerDB).where(
                    sql_models.QCrBoxContainerDB.application == command.application,
                    sql_models.QCrBoxContainerDB.status == sql_models.qcrbox_container.ContainerStatus.IDLE,
                )
            ).first()
            logger.debug(f"{container_to_use=}")
            logger.debug(
                f"FIXME: ensure that the selected container is up and running (qcrbox_id={container_to_use.qcrbox_id})"
            )
            msg_payload.container_qcrbox_id = container_to_use.qcrbox_id

        new_calculation_db = sql_models.QCrBoxCalculationDB(**msg_payload.dict())
        session.add(new_calculation_db)
        session.commit()
        session.refresh(new_calculation_db)
        assigned_calculation_id = new_calculation_db.id

        routing_key = new_calculation_db.container.routing_key__registry_to_application
        logger.debug(f"{routing_key=}")

        msg_execute_calculation = msg_specs.ExecuteCalculation(
            action="execute_calculation",
            payload=msg_specs.ExecuteCalculationPayload(
                command_id=msg_payload.command_id,
                calculation_id=assigned_calculation_id,
                arguments=msg_payload.arguments,
                container_qcrbox_id=msg_payload.container_qcrbox_id,
            ),
        )
        logger.debug(f"{msg_execute_calculation=}")

        try:
            response = await router.broker.publish(
                msg_execute_calculation,
                routing_key=routing_key,
                callback=True,
                callback_timeout=60.0,
                raise_timeout=True,
            )
            logger.debug(f"Response for command invocation: {response=}")
        except TimeoutError:
            return msg_specs.QCrBoxGenericResponse(
                response_to="invoke_command",
                status="error",
                payload={
                    "msg_execute_calculation": msg_execute_calculation,
                    "routing_key": routing_key,
                },
            )

    return msg_specs.QCrBoxGenericResponse(
        response_to="invoke_command", status="success", payload={"calculation_id": assigned_calculation_id}
    )
