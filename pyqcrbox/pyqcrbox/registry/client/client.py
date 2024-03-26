import json
import logging
import multiprocessing
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
    num_worker_processes: Optional[int] = None,
) -> QCrBoxFastStream:
    client_app = QCrBoxFastStream(broker, title="QCrBox Client", log_level=log_level)
    client_app.application_spec = application_spec
    client_app.calculations = {}
    private_routing_key = private_routing_key or "super-secret-private-client-queue"
    client_app.worker_pool: Optional[multiprocessing.Pool] = None

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
    async def set_up_worker_process_pool(logger: Logger) -> None:
        logger.debug(f"Setting up worker pool with {num_worker_processes} processes.")
        client_app.worker_pool = multiprocessing.Pool(num_worker_processes)

    @client_app.after_startup
    async def set_up_listeners(logger: Logger) -> None:
        # Temporarily suspend the broker in case it is running (otherwise
        # registering a new handler won't take effect until a restart).
        await broker.close()

        async def process_incoming_private_message(msg: dict, logger: Logger):
            logger.debug(f"Received message on private queue: {msg=}")

            if msg["action"] == "execute_command":
                msg = msg_specs.ExecuteCommand(**msg)
                try:
                    cmd_spec = application_spec.get_command_spec(msg.payload.command_name)
                except ValueError:
                    return msg_specs.QCrBoxGenericResponse(
                        response_to=msg.action,
                        status="error",
                        msg=f"Invalid command name: {msg.payload.command_name!r}",
                    )

                cmd = instantiate_command_from_spec(cmd_spec)
                calculation = await cmd.execute_in_background(**msg.payload.arguments)
                client_app.calculations[msg.payload.correlation_id] = calculation
                return msg_specs.ExecuteCommandResponse(
                    response_to=msg.action,
                    status="ok",
                    payload=msg_specs.PayloadForExecuteCommandResponse(correlation_id=msg.payload.correlation_id),
                )
            elif msg["action"] == "poll_calculation_status":
                msg = msg_specs.PollCalculationStatus(**msg)
                try:
                    calculation = client_app.calculations[msg.payload.correlation_id]
                except KeyError:
                    return msg_specs.QCrBoxGenericResponse(
                        response_to=msg.action,
                        status="error",
                        msg=f"No calculation could be found for correlation_id={msg.payload.correlation_id!r}",
                    )

                status_details = await calculation.get_status_details()
                return msg_specs.ReportCalculationStatusDetails(
                    response_to=msg.action,
                    status="ok",
                    payload=msg_specs.PayloadForReportCalculationStatusDetails(
                        correlation_id=msg.payload.correlation_id,
                        calculation_status=status_details,
                    ),
                )
            else:
                return msg_specs.QCrBoxGenericResponse(
                    response_to=msg.action,
                    status="error",
                    msg=f"Invalid action: {msg['action']!r}",
                )

        @broker.subscriber(private_routing_key)
        async def on_incoming_private_message(msg: dict, logger: Logger):
            msg_response = await process_incoming_private_message(msg, logger)
            logger.debug(f"Sending response to server: {msg_response!r}")
            # await broker.publish(
            #     msg_response,
            #     routing_key=settings.rabbitmq.routing_key_qcrbox_registry,
            # )
            client_app.increment_processed_message_counter(private_routing_key)
            return msg_response

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

    @client_app.after_shutdown
    async def terminate_worker_process_pool(logger: Logger) -> None:
        logger.debug("Closing worker process pool.")
        client_app.worker_pool.close()
        logger.debug("Waiting for worker processes to exit.")
        client_app.worker_pool.join()

    return client_app


if __name__ == "__main__":  # pragma: no cover
    broker = RabbitBroker(graceful_timeout=10)
    application_spec = sql_models.ApplicationSpecCreate(name="Foo", slug="foo", version="0.0.1")
    client_app = create_client_faststream_app(broker, application_spec=application_spec, log_level=logging.DEBUG)
    anyio.run(client_app.run, None, None)