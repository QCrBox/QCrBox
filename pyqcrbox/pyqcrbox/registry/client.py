import json
import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, settings, sql_models

from .base import QCrBoxFastStream
from .helpers import get_log_level_int


def create_client_faststream_app(
    broker: RabbitBroker,
    application_spec: sql_models.ApplicationCreate,
    private_routing_key: Optional[str] = None,
    log_level: Optional[int | str] = logging.INFO,
) -> QCrBoxFastStream:
    client_app = QCrBoxFastStream(broker, title="QCrBox Client", log_level=get_log_level_int(log_level))
    client_app.application_spec = application_spec
    private_routing_key = private_routing_key or "super-secret-private-client-queue"

    @client_app.after_startup
    async def register_application(logger: Logger) -> None:
        msg_debug = json.dumps(application_spec.model_dump())
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Sending registration request: {msg_debug_abbrev}")

        msg_register_application = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.RegisterApplication.Payload(
                application_config=application_spec,
                private_routing_key=private_routing_key,
            ),
        )

        response = await broker.publish(
            msg_register_application,
            queue=settings.rabbitmq.routing_key_qcrbox_registry,
            rpc=True,
            raise_timeout=True,
        )
        logger.info(f"Received response: {response!r}")

    @client_app.after_startup
    async def set_up_listener_on_private_queue(logger: Logger) -> None:
        # Temporarily suspend the broker in case it is running (otherwise
        # registering a new handler won't take effect until a restart).
        await broker.close()

        @broker.subscriber(private_routing_key)
        def on_incoming_private_message(msg: dict, logger: Logger):
            logger.debug(f"Received message on private queue: {msg=}")
            response = {
                "response_to": "incoming_private_message",
                "status": "success",
                "msg": "",
            }
            client_app.increment_processed_message_counter(private_routing_key)
            return response

        logger.debug(f"Set up listener on private queue: {private_routing_key!r}")

        @broker.subscriber(application_spec.routing_key_command_invocation)
        def on_command_invocation(msg: dict, logger: Logger):
            logger.debug(f"Received command invocation request: {msg=}")
            response = {
                "response_to": "command_invocation_request",
                "status": "success",
                "msg": "",
            }
            client_app.increment_processed_message_counter(application_spec.routing_key_command_invocation)
            return response

        logger.debug(
            f"Set up listener for command invocation requests: {application_spec.routing_key_command_invocation!r}"
        )

        # Resume broker now that the new handler has been registered.
        await broker.start()

    @client_app.after_startup
    async def shut_down_client_if_max_messages_is_zero(logger: Logger) -> None:
        if client_app.max_messages == 0:
            logger.debug("Shutting down client app because max_messages was set to zero.")
            client_app.request_shutdown()

    return client_app


if __name__ == "__main__":  # pragma: no cover
    broker = RabbitBroker(graceful_timeout=10)
    application_spec = sql_models.ApplicationCreate(name="Foo", slug="foo", version="0.0.1")
    client_app = create_client_faststream_app(broker, application_spec=application_spec, log_level=logging.DEBUG)
    anyio.run(client_app.run, None, None)
