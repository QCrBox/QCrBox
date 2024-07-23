import json
from typing import Any

from faststream import Context
from pydantic import BaseModel
from sqlmodel import select

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models_NEW_v2
from pyqcrbox.registry.shared.calculation_status import (
    CalculationStatusDetails,
    update_calculation_status_in_nats_kv_NEW,
)

from ..shared import CalculationStatusEnum, QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
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
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_client_response")(
            self.handle_command_invocation_client_response
        )
        self.nats_broker.subscriber("server.calc.get_status")(self.get_calculation_status)
        self.nats_broker.subscriber("*", kv_watch="calculation_status")(self.update_calculation_status_in_db)

    async def handle_application_registration(self, msg: msg_specs.RegisterApplication):
        logger.info(
            f"Received registration for application: {msg.payload.application_spec.slug!r} "
            f"(version: {msg.payload.application_spec.version!r})"
        )
        await self.nats_persistence_adapter.save_application_spec(msg.payload.application_spec)
        await self.sqlite_persistence_adapter.save_application_spec(msg.payload.application_spec)

    async def handle_command_invocation_by_user(self, msg: msg_specs.InvokeCommandNATS):
        logger.info(f"Received command invocation from user: {msg!r}")

        calculation_id = helpers.generate_calculation_id()
        calculation_details = CalculationDetails(
            calculation_id=calculation_id,
            **msg.model_dump(),
        )
        self.calculations[calculation_id] = calculation_details

        calculation_db = sql_models_NEW_v2.CalculationDB(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            command_name=msg.command_name,
            arguments=msg.arguments,
            calculation_id=calculation_id,
        )
        try:
            calculation_db.save_to_db()
        except sql_models_NEW_v2.QCrBoxDBError as exc:
            return msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=exc.message)

        msg_to_client = msg_specs.CommandInvocationRequestNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            command_name=msg.command_name,
            arguments=msg.arguments,
            calculation_id=calculation_id,
        )

        status_details = CalculationStatusDetails(
            calculation_id=calculation_id,
            status=CalculationStatusEnum.SUBMITTED,
            stdout="",
            stderr="",
            extra_info={},
        )
        await update_calculation_status_in_nats_kv_NEW(status_details)
        # await self.kv_calculation_status.put(calculation_id, CalculationStatusEnum.SUBMITTED.encode())
        await self.nats_broker.publish(
            msg_to_client,
            subject=f"client.cmd.handle_invocation_request.{msg_to_client.nats_subject_parts}",
            reply_to="server.cmd.handle_command_invocation_client_response",
        )
        return msg_specs.QCrBoxGenericResponse(
            response_to="server.cmd.handle_command_invocation_by_user",
            status=CalculationStatusEnum.SUBMITTED,
            payload={"calculation_id": calculation_id},
        )

    async def handle_command_invocation_client_response(self, msg: msg_specs.CommandInvocationClientResponseNATS):
        logger.info(f"Received client response: {msg!r}")
        if not msg.client_is_available:
            logger.debug(f"Client is not available: {msg.client_id}")
            return

        logger.debug(f"Retrieving details for calculation: {msg.calculation_id!r}")
        try:
            calc = self.calculations[msg.calculation_id]
        except KeyError:
            error_msg = f"Calculation not found: {msg.calculation_id!r}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if calc.executing_client is None:
            response_to_client = msg_specs.CommandExecutionRequestNATS(
                application_slug=calc.application_slug,
                application_version=calc.application_version,
                command_name=calc.command_name,
                arguments=calc.arguments,
                calculation_id=msg.calculation_id,
            )
            subject = f"{msg.private_inbox_prefix}.cmd.execute"
            await self.nats_broker.publish(response_to_client, subject=subject)

            logger.debug(
                f"Sending command execution request to client {msg.client_id!r} "
                f"(private inbox prefix: {msg.private_inbox_prefix!r})"
            )
            calc.executing_client = ExecutingClientDetails(
                client_id=msg.client_id,
                private_inbox_prefix=msg.private_inbox_prefix,
            )
        else:
            subject = f"{msg.private_inbox_prefix}.cmd.discard"
            response_to_client = msg_specs.DiscardCommandInvocationNATS(calculation_id=msg.calculation_id)
            logger.debug(
                f"Telling client {msg.client_id!r} to discard the invocation request "
                f"(private inbox prefix: {msg.private_inbox_prefix!r})"
            )
            await self.nats_broker.publish(response_to_client, subject=subject)

    async def get_calculation_status(self, msg: msg_specs.GetCalculationStatusNATS):
        logger.debug(f"Retrieving status for {msg.calculation_id!r}")
        executing_client = self.calculations[msg.calculation_id].executing_client
        client_inbox_prefix = executing_client.private_inbox_prefix
        subject = f"{client_inbox_prefix}.calc.status"
        response = await self.nats_broker.publish(msg, subject, rpc=True)
        logger.debug(f"{executing_client.client_id} responded with {response=!r}")
        # status = response["status"]
        status_nats_kv = json.loads((await self.kv_calculation_status.get(msg.calculation_id)).value)
        logger.debug(f"Calculation status in nats KV store is: {status_nats_kv!r}")
        return response

    async def update_calculation_status_in_db(
        self, status_details: CalculationStatusDetails, calculation_id: str = Context("message.raw_message.key")
    ):
        logger.debug(
            f"Received NATS notification about calculation status update: {status_details!r} ({calculation_id=!r})"
        )
        with settings.db.get_session() as session:
            calculation_db: sql_models_NEW_v2.CalculationDB = session.exec(
                select(sql_models_NEW_v2.CalculationDB).where(
                    sql_models_NEW_v2.CalculationDB.calculation_id == calculation_id
                )
            ).one()
            calculation_db.update_status(status_details.status, comment="NATS notification")
            logger.debug("Updated calculation status in the database.")

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
