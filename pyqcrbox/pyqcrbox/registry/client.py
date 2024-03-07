import json
import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, sql_models

from .base import QCrBoxFastStream
from .helpers import get_log_level_int


def create_client_faststream_app(
    broker: RabbitBroker,
    application_spec: sql_models.ApplicationCreate,
    private_queue_name: Optional[str] = None,
    log_level: Optional[int | str] = logging.INFO,
) -> QCrBoxFastStream:
    client_app = QCrBoxFastStream(broker, title="QCrBox Client", log_level=get_log_level_int(log_level))
    client_app.application_spec = application_spec
    private_queue = private_queue_name or "super-secret-private-client-queue"

    @client_app.after_startup
    async def register_application(logger: Logger) -> None:
        msg_debug = json.dumps(application_spec.model_dump())
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Sending registration request: {msg_debug_abbrev}")

        msg_register_application = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.RegisterApplication.Payload(
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

    @client_app.after_startup
    async def set_up_listener_on_private_queue(logger: Logger) -> None:
        # Temporarily suspend the broker in case it is running (otherwise
        # registering a new handler won't take effect until a restart).
        await broker.close()

        @broker.subscriber(private_queue)
        def on_incoming_private_mesage(msg: dict, logger: Logger):
            logger.debug(f"Received message on private queue: {msg=}")
            response = {
                "response_to": "incoming_private_message",
                "status": "success",
                "msg": "",
            }
            return response

        logger.debug(f"Set up listener on private queue: {private_queue!r}")

        @broker.subscriber(application_spec.routing_key_command_invocation)
        def on_command_invocation(msg: dict, logger: Logger):
            logger.debug(f"Received command invocation request: {msg=}")
            response = {
                "response_to": "command_invocation_request",
                "status": "success",
                "msg": "",
            }
            return response

        logger.debug(
            f"Set up listener for command invocation requests: {application_spec.routing_key_command_invocation!r}"
        )

        # Resume broker now that the new handler has been registered.
        await broker.start()

    return client_app


if __name__ == "__main__":  # pragma: no cover
    broker = RabbitBroker(graceful_timeout=10)
    application_spec = sql_models.ApplicationCreate(name="Foo", slug="foo", version="0.0.1")
    client_app = create_client_faststream_app(broker, application_spec=application_spec, log_level=logging.DEBUG)
    anyio.run(client_app.run, None, None)
