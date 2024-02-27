import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker

from .base import QCrBoxFastStream


def create_client_faststream_app(
    broker: RabbitBroker,
    application_spec: dict,
    private_queue_name: Optional[str] = None,
    log_level: Optional[int | str] = logging.INFO,
) -> QCrBoxFastStream:
    client_app = QCrBoxFastStream(broker, title="QCrBox Client", log_level=log_level)
    client_app.application_spec = application_spec
    private_queue = private_queue_name or "super-secret-private-client-queue"

    @client_app.after_startup
    async def register_application(logger: Logger) -> None:
        logger.info(f"Sending registration request: {application_spec}")

        msg_register_application = dict(
            action="register_application",
            payload=dict(
                application_config=application_spec,
                routing_key__registry_to_application=private_queue,
            ),
        )

        response = await broker.publish(
            msg_register_application,
            queue="qcrbox-registry-v5b",
            rpc=True,
            raise_timeout=True,
        )
        logger.info(f"Received response: {response!r}")

        client_app.request_shutdown()

    return client_app


if __name__ == "__main__":  # pragma: no cover
    broker = RabbitBroker(graceful_timeout=10)
    application_spec = dict(name="Foo", slug="foo", version="0.0.1")
    client_app = create_client_faststream_app(broker, application_spec=application_spec, log_level=logging.DEBUG)
    anyio.run(client_app.run, None, None)
