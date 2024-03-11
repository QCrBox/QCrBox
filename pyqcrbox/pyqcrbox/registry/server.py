import json
import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker
from sqlmodel import select

from pyqcrbox import msg_specs, settings, sql_models

from .base import QCrBoxFastStream
from .helpers import get_log_level_int


def create_server_faststream_app(
    broker: RabbitBroker,
    log_level: Optional[int | str] = logging.INFO,
    purge_existing_db_tables: bool = False,
) -> QCrBoxFastStream:
    server_app = QCrBoxFastStream(broker, title="QCrBox Server", log_level=get_log_level_int(log_level))
    public_queue = settings.rabbitmq.routing_key_qcrbox_registry

    @server_app.on_startup
    async def init_database(logger: Logger) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")

    @broker.subscriber(public_queue)
    async def on_qcrbox_registry(msg: dict, logger: Logger) -> dict:
        msg_specs.QCrBoxBaseAction.model_validate(msg)

        msg_debug = json.dumps(msg)
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.debug(f"Incoming message: {msg_debug_abbrev}")
        if msg["action"] == "register_application":
            app_cfg = sql_models.ApplicationCreate(**msg["payload"]["application_config"])
            app_db = app_cfg.save_to_db(private_routing_key=msg["payload"]["private_routing_key"])
            response = {
                "response_to": "register_application",
                "status": "success",
                "msg": f"Successfully registered application {app_db.name!r} (id: {app_db.id})",
            }
        elif msg["action"] == "invoke_command":
            cmd_invocation = sql_models.CommandInvocationCreate(**msg["payload"])
            cmd_invocation_db = cmd_invocation.save_to_db()
            if cmd_invocation_db.application_id and cmd_invocation_db.command_id:
                response = {
                    "response_to": "invoke_command",
                    "status": "ok",
                    "msg": "Received command invocation request.",
                }
                with settings.db.get_session() as session:
                    application = session.exec(
                        select(sql_models.ApplicationDB).where(
                            sql_models.ApplicationDB.id == cmd_invocation_db.application_id
                        )
                    ).one()
                    logger.debug(
                        f"Sending command invocation request to queue for {application.slug!r}, "
                        f"version {application.version!r}"
                    )
                    await broker.publish(cmd_invocation.model_dump(), routing_key=application.private_routing_key)
            else:
                response = {
                    "response_to": "invoke_command",
                    "status": "error",
                    "msg": "Could not proceed with command invocation request (TODO: add reason).",
                }
        else:
            response = {
                "response_to": "register_application",
                "status": "failed",
                "msg": f"Invalid action: {msg['action']!r}",
            }

        server_app.increment_processed_message_counter(public_queue)
        return response

    server_app.on_qcrbox_registry = on_qcrbox_registry

    return server_app


if __name__ == "__main__":
    broker = RabbitBroker(graceful_timeout=10)
    server_app = create_server_faststream_app(broker, log_level=logging.DEBUG)
    anyio.run(server_app.run, 1, 60)
