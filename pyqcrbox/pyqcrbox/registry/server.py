import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker
from sqlmodel import create_engine

from pyqcrbox import settings
from pyqcrbox.sql_models import QCrBoxBaseSQLModel

from .base import QCrBoxFastStream


def create_server_faststream_app(
    broker: RabbitBroker, log_level: Optional[int | str] = logging.INFO
) -> QCrBoxFastStream:
    server_app = QCrBoxFastStream(broker, title="QCrBox Server", log_level=log_level)
    public_queue = "qcrbox-registry-v5b"

    @server_app.on_startup
    async def init_database(logger: Logger) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        engine = create_engine(settings.db.url, echo=True, connect_args=settings.db.connect_args)
        QCrBoxBaseSQLModel.metadata.create_all(engine)
        logger.info("Finished initialising database...")

    @broker.subscriber(public_queue)
    async def on_qcrbox_registry(msg: dict, logger: Logger) -> dict:
        logger.info(f"Incoming message: {msg}")
        if msg["action"] == "register_application":
            response = {
                "response_to": "register_application",
                "status": "success",
                "msg": f"Successfully registered application {msg['payload']['application_config']['name']!r}",
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
