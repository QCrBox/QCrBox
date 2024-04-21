import json
import logging
from typing import Optional

import anyio
from faststream import Logger, apply_types
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
    @apply_types
    async def on_qcrbox_registry(msg: dict, logger: Logger) -> Optional[msg_specs.QCrBoxGenericResponse]:
        msg_debug = json.dumps(msg)
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Received message: {msg_debug_abbrev} (type: {type(msg).__name__})")

        # Process the message - it will be passed to the correct processing function based on
        # its type/structure (the heavy lifting is done by `functools.singledispatch`).
        response = await process_message_sync_or_async(msg)

        server_app.increment_processed_message_counter(public_queue)
        return response

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
