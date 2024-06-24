from typing import Any

from pydantic import BaseModel

from pyqcrbox import helpers, logger, msg_specs, settings

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_server_asgi_server


class ExecutingClientDetails(BaseModel):
    client_id: str
    private_inbox_prefix: str


class CalculationDetails(BaseModel):
    calculation_id: str
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]
    executing_client: ExecutingClientDetails | None = None


class QCrBoxServer(QCrBoxServerClientBase):
    # def _set_up_rabbitmq_broker(self) -> None:
    #     # self.set_up_message_dispatcher(
    #     #     queue_name=settings.rabbitmq.routing_key_qcrbox_registry,
    #     #     message_dispatcher=server_side_message_dispatcher,
    #     #     exchange_type=ExchangeType.DIRECT,
    #     #     routing_key="",
    #     # )
    #     pass

    def _set_up_nats_broker(self) -> None:
        self.nats_broker.subscriber("register-application")(self.handle_application_registration)
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_by_user")(
            self.handle_command_invocation_by_user
        )

    async def handle_application_registration(self, msg: msg_specs.RegisterApplication):
        logger.info(
            f"Received registration for application: {msg.payload.application_spec.slug!r} "
            f"(version: {msg.payload.application_spec.version!r})"
        )
        from .message_processing.register_application import handle_application_registration_request

        return handle_application_registration_request(msg)

    async def handle_command_invocation_by_user(self, msg: msg_specs.InvokeCommandNATS):
        logger.info(f"Received command invocation from user: {msg!r}")

        calculation_id = helpers.generate_calculation_id()
        calculation_details = CalculationDetails(
            calculation_id=calculation_id,
            **msg.model_dump(),
        )
        logger.debug(f"[DDD] {calculation_id=}")
        logger.debug(f"[DDD] {calculation_details=}")
        self.calculations[calculation_id] = calculation_details

        msg_to_client = msg_specs.CommandInvocationRequestNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            command_name=msg.command_name,
            arguments=msg.arguments,
            calculation_id=calculation_id,
        )

        await self.nats_broker.publish(
            msg_to_client,
            subject=f"client.cmd.handle_invocation_request.{msg_to_client.nats_subject_parts}",
            reply_to="server.cmd.handle_command_invocation_client_response",
        )
        return {"calculation_id": calculation_id}

    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_server_asgi_server(self.lifespan_context)

    @on_qcrbox_startup
    async def init_database(self, purge_existing_db_tables: bool) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")

    #
    # async def publish(self, queue, msg):
    #     await self.broker.publish(msg, queue)


class TestQCrBoxServer(TestQCrBoxServerClientBase, QCrBoxServer):
    pass


def main():
    qcrbox_server = QCrBoxServer()
    qcrbox_server.run(
        host=settings.registry.server.host,
        port=settings.registry.server.port,
        purge_existing_db_tables=False,
    )


if __name__ == "__main__":
    main()
