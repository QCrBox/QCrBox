import json
import logging
from typing import Optional

import anyio
import pydantic
from faststream import Logger
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, settings
from pyqcrbox.msg_specs import InvalidQCrBoxAction, look_up_action_class

from ..base import QCrBoxFastStream
from .message_processing import process_message_sync_or_async


def create_server_faststream_app(
    broker: RabbitBroker,
    log_level: Optional[int | str] = logging.INFO,
    purge_existing_db_tables: bool = False,
) -> QCrBoxFastStream:
    server_app = QCrBoxFastStream(broker, title="QCrBox Server", log_level=log_level)
    public_queue = settings.rabbitmq.routing_key_qcrbox_registry

    @server_app.on_startup
    async def init_database(logger: Logger) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")

    @broker.subscriber(public_queue)
    async def on_qcrbox_registry(msg: dict, logger: Logger) -> msg_specs.QCrBoxGenericResponse:
        msg_debug = json.dumps(msg)
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Received message: {msg_debug_abbrev} (type: {type(msg).__name__})")

        if isinstance(msg, (str, bytes)):
            try:
                msg = json.loads(msg)
            except Exception as exc:
                error_msg = (
                    f"Incoming message does not represent a valid JSON structure: {msg}.\n"
                    f"The original error was: {exc}"
                )
                logger.error(error_msg)
                return msg_specs.QCrBoxGenericResponse(
                    response_to="incoming_message", status="error", msg=error_msg, payload=None
                )

        if "action" not in msg:
            error_msg = "Invalid message structure: message must have an 'action' field"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        try:
            action_cls = look_up_action_class(msg["action"])
        except InvalidQCrBoxAction:
            error_msg = f"Invalid action: {msg['action']!r}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        try:
            msg_obj = action_cls(**msg)
        except pydantic.ValidationError as exc:
            error_msg = f"Invalid message structure for action {msg['action']!r}. Errors: {exc.errors()}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        # Process the message - it will be passed to the correct processing function based on
        # its type/structure (the heavy lifting is done by `functools.singledispatch`).
        return await process_message_sync_or_async(msg_obj)

    # @broker.subscriber(public_queue)
    # async def on_qcrbox_registry(msg: dict, logger: Logger) -> dict:
    #     msg_specs.QCrBoxBaseAction.model_validate(msg)
    #
    #     msg_debug = json.dumps(msg)
    #     msg_debug_abbrev = msg_debug[:800] + " ..."
    #     logger.debug(f"Incoming message: {msg_debug_abbrev}")
    #     if msg["action"] == "register_application":
    #         app_cfg = sql_models.ApplicationCreate(**msg["payload"]["application_config"])
    #         app_db = app_cfg.save_to_db(private_routing_key=msg["payload"]["private_routing_key"])
    #         response = {
    #             "response_to": "register_application",
    #             "status": "success",
    #             "msg": f"Successfully registered application {app_db.name!r} (id: {app_db.id})",
    #         }
    #     elif msg["action"] == "invoke_command":
    #         cmd_invocation = sql_models.CommandInvocationCreate(**msg["payload"])
    #         cmd_invocation_db = cmd_invocation.save_to_db()
    #         if cmd_invocation_db.application_id and cmd_invocation_db.command_id:
    #             response = {
    #                 "response_to": "invoke_command",
    #                 "status": "ok",
    #                 "msg": "Received command invocation request.",
    #             }
    #             with settings.db.get_session() as session:
    #                 application = session.exec(
    #                     select(sql_models.ApplicationDB).where(
    #                         sql_models.ApplicationDB.id == cmd_invocation_db.application_id
    #                     )
    #                 ).one()
    #                 logger.debug(
    #                     f"Sending command invocation request to queue for {application.slug!r}, "
    #                     f"version {application.version!r}"
    #                 )
    #                 await broker.publish(
    #                     cmd_invocation.model_dump(),
    #                     routing_key=application.routing_key_command_invocation,
    #                 )
    #         else:
    #             response = {
    #                 "response_to": "invoke_command",
    #                 "status": "error",
    #                 "msg": "Could not proceed with command invocation request (TODO: add reason).",
    #             }
    #     elif msg["action"] == "accept_command_invocation":
    #         logger.debug(
    #             f"Application accepted command invocation with correlation_id={msg['payload']['correlation_id']}"
    #         )
    #         msg_execute_cmd = {
    #             "action": "execute_command",
    #             "payload": {
    #                 "arguments": "TODO",
    #             },
    #         }
    #         await broker.publish(msg_execute_cmd, routing_key=msg["payload"]["private_routing_key"])
    #         response = {
    #             "response_to": "accept_command_invocation",
    #             "status": "successful",
    #             "msg": "Submitted command execution request to client application.",
    #         }
    #     else:
    #         response = {
    #             "response_to": "register_application",
    #             "status": "failed",
    #             "msg": f"Invalid action: {msg['action']!r}",
    #         }
    #
    #     server_app.increment_processed_message_counter(public_queue)
    #     return response

    server_app.on_qcrbox_registry = on_qcrbox_registry

    return server_app


if __name__ == "__main__":
    broker = RabbitBroker(graceful_timeout=10)
    server_app = create_server_faststream_app(broker, log_level=logging.DEBUG)
    anyio.run(server_app.run, 1, 60)
