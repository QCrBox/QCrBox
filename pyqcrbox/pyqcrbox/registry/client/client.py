import json
import logging
from typing import Optional

import anyio
from faststream import Logger
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, settings, sql_models

from ..base import QCrBoxFastStream
from .command_execution import instantiate_command_from_spec

__all__ = ["create_client_faststream_app"]


def create_client_faststream_app(
    broker: RabbitBroker,
    application_spec: sql_models.ApplicationSpecCreate,
    private_routing_key: Optional[str] = None,
    log_level: Optional[int | str] = logging.INFO,
) -> QCrBoxFastStream:
    client_app = QCrBoxFastStream(broker, title="QCrBox Client", log_level=log_level)
    client_app.application_spec = application_spec
    client_app.calculations = {}
    private_routing_key = private_routing_key or "super-secret-private-client-queue"

    @client_app.after_startup
    async def register_application(logger: Logger) -> None:
        msg_debug = json.dumps(application_spec.model_dump())
        msg_debug_abbrev = msg_debug[:800] + " ..."
        logger.info(f"Sending registration request: {msg_debug_abbrev}")

        msg_register_application = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.PayloadForRegisterApplication(
                application_spec=application_spec,
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
        client_app.increment_processed_message_counter(private_routing_key)
        if isinstance(response, dict):
            # TODO: ensure that all handlers return an instance of QCrBoxGenericResponse rather than a plain dict
            response = msg_specs.QCrBoxGenericResponse(**response)
        assert isinstance(response, msg_specs.QCrBoxGenericResponse)

        if response.status != "success":
            raise RuntimeError(f"Something went wrong, bailing out.\nResponse from server: {response!r}")

    @client_app.after_startup
    async def set_up_listeners(logger: Logger) -> None:
        # Temporarily suspend the broker in case it is running (otherwise
        # registering a new handler won't take effect until a restart).
        await broker.close()

        @broker.subscriber(private_routing_key)
        async def on_incoming_private_message(msg: msg_specs.ExecuteCommand, logger: Logger):
            logger.debug(f"Received message on private queue: {msg=}")

            cmd = instantiate_command_from_spec(application_spec, msg.payload.command_name)
            calculation = await cmd.execute_in_background(**msg.payload.arguments)
            # TODO: deal with the execution request!

            client_app.calculations[msg.payload.correlation_id] = calculation
            client_app.increment_processed_message_counter(private_routing_key)

        logger.debug(f"Set up listener on private queue: {private_routing_key!r}")

        @broker.subscriber(application_spec.routing_key_command_invocation)
        async def on_command_invocation_request(msg: sql_models.CommandInvocationCreate, logger: Logger):
            logger.debug(f"Received command invocation request: {msg=}")

            # TODO: if the client is currently busy or otherwise unable to execute the command,
            # send a response to reject the invocation request

            msg_response = msg_specs.CommandInvocationRequestAccepted(
                action="command_invocation_request_accepted",
                payload=msg_specs.PayloadForCommandInvocationRequestAccepted(
                    private_routing_key=private_routing_key,
                    **msg.model_dump(),
                ),
            )

            logger.debug(f"Accepting command invocation request (correlation_id: {msg.correlation_id})")
            await broker.publish(
                msg_response,
                routing_key=settings.rabbitmq.routing_key_qcrbox_registry,
            )
            client_app.increment_processed_message_counter(application_spec.routing_key_command_invocation)

        logger.debug(
            f"Set up listener for command invocation requests: {application_spec.routing_key_command_invocation!r}"
        )

        # Resume broker now that the new handler has been registered.
        await broker.start()

    return client_app


if __name__ == "__main__":  # pragma: no cover
    broker = RabbitBroker(graceful_timeout=10)
    application_spec = sql_models.ApplicationSpecCreate(name="Foo", slug="foo", version="0.0.1")
    client_app = create_client_faststream_app(broker, application_spec=application_spec, log_level=logging.DEBUG)
    anyio.run(client_app.run, None, None)
