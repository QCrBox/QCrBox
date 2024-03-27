import json
import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, settings
from pyqcrbox.msg_specs import process_message_sync_or_async

from ..base import QCrBoxFastStream


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
    async def on_qcrbox_registry(msg: dict, logger: Logger) -> Optional[msg_specs.QCrBoxGenericResponse]:
        msg_debug = json.dumps(msg)
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Received message: {msg_debug_abbrev} (type: {type(msg).__name__})")

        # Process the message - it will be passed to the correct processing function based on
        # its type/structure (the heavy lifting is done by `functools.singledispatch`).
        response = await process_message_sync_or_async(msg)

        server_app.increment_processed_message_counter(public_queue)
        return response

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
    #                     select(sql_models.ApplicationSpecDB).where(
    #                         sql_models.ApplicationSpecDB.id == cmd_invocation_db.application_id
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


async def main_async(max_messages=None, shutdown_delay: Optional[float] = None) -> None:
    broker = RabbitBroker(url=settings.rabbitmq.url)
    server_app = create_server_faststream_app(broker, log_level="DEBUG")
    await server_app.run(max_messages=max_messages, shutdown_delay=shutdown_delay)


def main(max_messages=None, shutdown_delay: Optional[float] = None) -> None:
    anyio.run(main_async, max_messages, shutdown_delay)


if __name__ == "__main__":
    max_messages = 1
    shutdown_delay = 60

    main(max_messages, shutdown_delay)
