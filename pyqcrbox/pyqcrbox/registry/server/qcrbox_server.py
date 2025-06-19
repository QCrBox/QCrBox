from typing import Any

from faststream import Context
from litestar import Litestar
from litestar.exceptions import (
    HTTPException,
    ImproperlyConfiguredException,
    InternalServerException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
    ValidationException,
)
from litestar.openapi import OpenAPIConfig
from pydantic import BaseModel

from pyqcrbox import helpers, logger, msg_specs, settings
from pyqcrbox.debug import eel_logging
from pyqcrbox.msg_specs.base import QCrBoxGenericResponse
from pyqcrbox.registry.server.api.api_endpoints import handle_exception
from pyqcrbox.registry.shared.calculation_status import (
    NatsCalculationAlreadyExists,
    add_calculation_to_nats_kv,
    update_calculation_status_in_nats_kv,
)
from pyqcrbox.sql_models import CalculationStatusDetails, CalculationStatusEnum
from pyqcrbox.sql_models.calculation import CalculationNatsDB

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup, structlog_plugin
from .api import api_router


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
    @eel_logging
    def _set_up_nats_broker(self) -> None:
        self.nats_broker.subscriber("register-application")(self.handle_application_registration)
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_by_user")(
            self.handle_command_invocation_by_user
        )
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_client_response")(
            self.handle_command_invocation_client_response
        )
        self.nats_broker.subscriber("server.calc.get_status")(self.get_calculation_status_from_client)
        self.nats_broker.subscriber("*", kv_watch="calculation_status")(self.update_calculation_status_in_db)

    @eel_logging
    async def handle_application_registration(self, msg: msg_specs.RegisterApplication) -> None:
        """Handle application registration requests.

        This is a handler for the `register-application` inbox in the NATS broker.
        For an application to be available to a user, it must register itself and
        its commands using this handler.

        Applications are added to the in-memory SQL database and were historically
        also added into NATS.

        Parameters
        ----------
        msg : msg_specs.RegisterApplication
            The NATS message sent by the application requesting to be registered.

        """
        logger.info(
            f"Received registration for application: {msg.payload.application_spec.slug!r} "
            f"(version: {msg.payload.application_spec.version!r})"
        )
        # await self.nats_persistence_adapter.save_application_spec(msg.payload.application_spec)
        await self.sqlite_persistence_adapter.save_application_spec(msg.payload.application_spec)

    @eel_logging
    async def handle_command_invocation_by_user(self, msg: msg_specs.InvokeCommandNATS) -> QCrBoxGenericResponse:
        logger.info(f"Received command invocation from user: {msg!r}")

        calculation_id = helpers.generate_calculation_id()
        calculation_details = CalculationDetails(calculation_id=calculation_id, **msg.model_dump())
        self.calculations[calculation_id] = calculation_details

        msg_to_client = msg_specs.CommandInvocationRequestNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            command_name=msg.command_name,
            arguments=msg.arguments,
            calculation_id=calculation_id,
        )

        msg_from_client = await self.nats_broker.publish(
            message=msg_to_client,
            subject=f"client.cmd.handle_invocation_request.{msg_to_client.nats_subject_parts}",
            rpc=True,
        )
        msg_from_client = msg_specs.CommandInvocationClientResponseNATS(**msg_from_client)
        await self.nats_broker.publish(
            message=msg_from_client, subject="server.cmd.handle_command_invocation_client_response"
        )

        command_status = await self.add_command_request_to_calculation_db(msg_to_client, msg_from_client)
        logger.debug(f"Command invocation final status: {command_status}")

        return command_status

    @eel_logging
    async def handle_command_invocation_client_response(self, msg: msg_specs.CommandInvocationClientResponseNATS):
        logger.info(f"Received client response: {msg!r}")

        if not msg.client_is_available:
            logger.debug(
                "Client is not available, telling client to discard the invocation request:"
                + " client_id={msg.client_id} calculation_id={msg.calculation_id}"
            )
            subject = f"{msg.private_inbox_prefix}.cmd.discard"
            response_to_client = msg_specs.DiscardCommandInvocationNATS(calculation_id=msg.calculation_id)
            logger.debug(
                f"Telling client {msg.client_id!r} to discard the invocation request "
                f"(private inbox prefix: {msg.private_inbox_prefix!r})"
            )
            await self.nats_broker.publish(response_to_client, subject=subject)
            return

        logger.debug(f"Retrieving details for calculation: {msg.calculation_id!r}")
        try:
            calc = self.calculations[msg.calculation_id]
        except KeyError as exc:
            error_msg = f"Calculation not found: {msg.calculation_id!r}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from exc

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

    @eel_logging
    async def get_calculation_status_from_client(self, msg: msg_specs.GetCalculationStatusNATS):
        logger.debug(f"Retrieving status for {msg.calculation_id!r}")
        client = self.calculations[msg.calculation_id].executing_client
        client_inbox_prefix = client.private_inbox_prefix
        response = await self.nats_broker.publish(
            msg,
            f"{client_inbox_prefix}.calc.status",
            rpc=True,
        )
        logger.debug(f"{client.client_id} responded with {response=!r}")

        return response

    async def add_command_request_to_calculation_db(
        self,
        msg_to_client: msg_specs.CommandInvocationRequestNATS,
        msg_from_client: msg_specs.CommandInvocationClientResponseNATS,
    ):
        if not msg_from_client.client_is_available:
            logger.error("Requested a client which is not available")
            return msg_specs.QCrBoxGenericResponse(
                response_to="server.cmd.handle_command_invocation_by_user",
                status=CalculationStatusEnum.FAILED,
                payload={"error": f"Chosen client {msg_from_client.client_id!r} is not available"},
            )

        calculation_nats = CalculationNatsDB(
            calculation_id=msg_to_client.calculation_id,
            application_slug=msg_to_client.application_slug,
            application_version=msg_to_client.application_version,
            command_name=msg_to_client.command_name,
            arguments=msg_to_client.arguments,
        )

        try:
            await add_calculation_to_nats_kv(calculation_nats)
        except NatsCalculationAlreadyExists:
            return msg_specs.QCrBoxGenericResponse(
                response_to="server.cmd.handle_command_invocation_by_user",
                status=CalculationStatusEnum.FAILED,
                payload={"error": "Tried to add a new calculation to one which already exists"},
            )

        status_details = CalculationStatusDetails(
            calculation_id=msg_to_client.calculation_id,
            status=CalculationStatusEnum.SUBMITTED,
            stdout="",
            stderr="",
            extra_info={},
        )
        await update_calculation_status_in_nats_kv(status_details)

        return msg_specs.QCrBoxGenericResponse(
            response_to="server.cmd.handle_command_invocation_by_user",
            status=CalculationStatusEnum.SUBMITTED,
            payload={"calculation_id": msg_to_client.calculation_id},
        )

    @eel_logging
    async def update_calculation_status_in_db(
        self, status_details: CalculationStatusDetails, _calculation_id: str = Context("message.raw_message.key")
    ):
        logger.debug(f"Received NATS notification about calculation status update: {status_details!r}")
        await update_calculation_status_in_nats_kv(status_details)

    @eel_logging
    def _set_up_asgi_server(self) -> None:
        self.asgi_server = Litestar(
            route_handlers=[
                api_router,
            ],
            lifespan=[self.lifespan_context],
            debug=settings.debug_mode,
            plugins=[structlog_plugin],
            openapi_config=OpenAPIConfig(
                title="QCrBox",
                version="0.2",
                use_handler_docstrings=True,
            ),
            exception_handlers={
                HTTPException: handle_exception,
                ImproperlyConfiguredException: handle_exception,
                ValidationException: handle_exception,
                PermissionDeniedException: handle_exception,
                NotAuthorizedException: handle_exception,
                NotFoundException: handle_exception,
                InternalServerException: handle_exception,
                ServiceUnavailableException: handle_exception,
                Exception: handle_exception,
            },
        )

    @on_qcrbox_startup
    @eel_logging
    async def init_database(self, purge_existing_db_tables: bool) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")


class TestQCrBoxServer(TestQCrBoxServerClientBase, QCrBoxServer):
    pass


@eel_logging
def main():
    qcrbox_server = QCrBoxServer()
    qcrbox_server.run(
        host=settings.registry.server.host,
        port=settings.registry.server.port,
        purge_existing_db_tables=False,
    )


if __name__ == "__main__":
    main()
