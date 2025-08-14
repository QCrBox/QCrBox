from typing import Any

import svcs
from faststream.nats import NatsBroker
from litestar import Litestar, MediaType, get
from litestar.di import Provide
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
from litestar.response import Redirect
from pydantic import BaseModel

from pyqcrbox import helpers, logger, msg_specs, settings
from pyqcrbox.data_management import CalculationAlreadyExists, DataFileManager
from pyqcrbox.debug import log_eel
from pyqcrbox.msg_specs.base import QCrBoxGenericResponse
from pyqcrbox.registry.server.api.api_endpoints import handle_exception
from pyqcrbox.sql_models import CalculationDB, CalculationStatusDetails, CalculationStatusEnum

from ..shared import (
    QCrBoxServerClientBase,
    TestQCrBoxServerClientBase,
    on_qcrbox_startup,
    structlog_plugin,
)
from .api import api_router


class ExecutingClientDetails(BaseModel):
    client_id: str
    private_inbox_prefix: str


class CalculationDetails(BaseModel):
    calculation_id: str
    application_slug: str
    application_version: str
    command_name: str
    command_arguments: dict[str, Any]
    executing_client: ExecutingClientDetails | None = None


def build_litestar_dependencies(container: svcs.Container) -> dict:
    return {
        "nats_broker": Provide(lambda: container.aget(NatsBroker)),
        "data_file_manager": Provide(lambda: container.aget(DataFileManager)),
    }


@get(path="/", media_type=MediaType.HTML, include_in_schema=False)
async def web_root_handler() -> Redirect:
    return Redirect(path="/api")


class QCrBoxServer(QCrBoxServerClientBase):
    def _set_up_nats_broker(self) -> None:
        """Initialise NATS inbox handlers."""
        if not self.nats_broker:
            raise RuntimeError(f"A NATS Broker has not been configured for {self!r}")
        self.nats_broker.subscriber("register-application")(self.handle_application_registration)
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_by_user")(
            self.handle_command_invocation_by_user
        )
        self.nats_broker.subscriber("server.cmd.handle_command_invocation_client_response")(
            self.handle_command_invocation_client_response
        )

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

    @log_eel
    async def handle_command_invocation_by_user(self, msg: msg_specs.InvokeCommandNATS) -> QCrBoxGenericResponse:
        """Handle a command request from a user.

        This handler takes a request from the API and sends a message to the NATS
        inbox `client.cmd.handle_invocation_request.{application-details}`. The response
        from that request to the client(s) is then handled by `hand_command_invocation_client_response`
        which determines if the client can execute the request.

        This function is what generates the response for the API request.

        Parameters
        ----------
        msg : msg_specs.InvokeCommandNATS
            A NATS message for command invocation requests.

        Returns
        -------
        QCrBoxGenericResponse
            A response message containing data about if the command could be
            executed or not.

        """
        logger.info(f"Received command invocation from user: {msg!r}")

        calculation_id = helpers.generate_calculation_id()
        calculation_details = CalculationDetails(calculation_id=calculation_id, **msg.model_dump())
        self.calculations[calculation_id] = calculation_details

        invocation_request_to_client = msg_specs.CommandInvocationRequestNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            command_name=msg.command_name,
            command_arguments=msg.command_arguments,
            calculation_id=calculation_id,
        )

        # Send invocation request to client(s) and get back their response which
        # indicates if the client can execute the requested command or not
        invocation_response_from_client = await self.nats_broker.publish(
            message=invocation_request_to_client,
            subject=f"client.cmd.handle_invocation_request.{invocation_request_to_client.nats_subject_parts}",
            rpc=True,
        )
        # Now send the command request response to another inbox in the server (this class)
        # which will either ask the client to discard the request or execute the request
        invocation_response_from_client = msg_specs.CommandInvocationClientResponseNATS(
            **invocation_response_from_client  # type: ignore
        )
        await self.nats_broker.publish(
            message=invocation_response_from_client, subject="server.cmd.handle_command_invocation_client_response"
        )

        # Whatever happens, try and the request to the calculations database. This method
        # also returns the status to return to the API, e.g. either failure or submitted
        command_request_final_status = await self.add_command_request_to_database(
            invocation_request_to_client, invocation_response_from_client
        )
        logger.debug(f"Command invocation final status before execution: {command_request_final_status}")

        return command_request_final_status

    @log_eel
    async def handle_command_invocation_client_response(
        self, msg: msg_specs.CommandInvocationClientResponseNATS
    ) -> None:
        """Handle a client response for a user command invocation request.

        This function will either send a request to discard the command execution
        request or request for the command to execute on the client. It does not
        deal with tracking the calculation.

        Parameters
        ----------
        msg : msg_specs.CommandInvocationClientResponseNATS
            The response message sent back from the client upon a command invocation
            request by a user.

        """
        logger.info(f"Received client response: {msg!r}")

        # If the client is not available, discard request and return
        if not msg.client_is_available:
            logger.info(f"Client {msg.client_id!r} not available, discarding the request: {msg!r}")
            await self.nats_broker.publish(
                msg_specs.DiscardCommandInvocationNATS(calculation_id=msg.calculation_id),
                subject=f"{msg.private_inbox_prefix}.cmd.discard",
            )
            return

        logger.debug(f"Retrieving details for calculation: {msg.calculation_id!r}")
        try:
            calc = self.calculations[msg.calculation_id]
        except KeyError as exc:
            error_msg = f"Unable to find calculation: {msg.calculation_id!r}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from exc

        # If for some reason the calculation has an `executing_client`, then that means
        # the calculation is already running on some client. We **shouldn't** ever get
        # here, but if we do we need to discard the current request.
        if calc.executing_client:
            logger.info(f"Calculation {msg.calculation_id} is already executing, discarding the request: {msg!r}")
            await self.nats_broker.publish(
                msg_specs.DiscardCommandInvocationNATS(calculation_id=msg.calculation_id),
                subject=f"{msg.private_inbox_prefix}.cmd.discard",
            )

        # If the client is available and the calculation is not already executing somewhere,
        # then we can send a request to the client to execute the command
        logger.info(
            f"Requesting client {msg.client_id!r} ({msg.private_inbox_prefix!r}) to execute command request: {msg!r}"
        )
        response_to_client = msg_specs.CommandExecutionRequestNATS(
            application_slug=calc.application_slug,
            application_version=calc.application_version,
            command_name=calc.command_name,
            command_arguments=calc.command_arguments,
            calculation_id=calc.calculation_id,
        )
        logger.debug(f"Message to client for command execution: {response_to_client}")
        await self.nats_broker.publish(response_to_client, subject=f"{msg.private_inbox_prefix}.cmd.execute")
        calc.executing_client = ExecutingClientDetails(
            client_id=msg.client_id,
            private_inbox_prefix=msg.private_inbox_prefix,
        )

    @log_eel
    async def add_command_request_to_database(
        self,
        user_invocation_request: msg_specs.CommandInvocationRequestNATS,
        client_invocation_response: msg_specs.CommandInvocationClientResponseNATS,
    ) -> msg_specs.QCrBoxGenericResponse:
        """Add a user command request to the calculation database.

        Parameters
        ----------
        user_invocation_request : msg_specs.CommandInvocationRequestNATS
            A NATS message dataclass for a user requesting a command invocation.
            This is the message sent to client which will execute the command
            request.
        client_invocation_response : msg_specs.CommandInvocationClientResponseNATS
            A NATS message dataclass containing the response from the client requested
            to execute the command request.

        Returns
        -------
        msg_specs.QCrBoxGenericResponse
            A response to send back to the API request, indicating if the client
            has accepted the request or not.

        """
        # If the client is not available, we don't need to add this request to the
        # database as the calculation won't be happening
        if not client_invocation_response.client_is_available:
            client_id = client_invocation_response.client_id
            logger.error("Client is not available to execute command request")
            return msg_specs.QCrBoxGenericResponse(
                response_to="server.cmd.handle_command_invocation_by_user",
                status=CalculationStatusEnum.FAILED,
                payload={"error": f"The client '{client_id!r}' is not available to execute the command request"},
            )

        calculation_db_entry = CalculationDB(
            calculation_id=user_invocation_request.calculation_id,
            client_private_inbox=client_invocation_response.private_inbox_prefix,
            application_slug=user_invocation_request.application_slug,
            application_version=user_invocation_request.application_version,
            command_name=user_invocation_request.command_name,
            command_arguments=user_invocation_request.command_arguments,
        )

        # Don't allow the same calculation to be added to the database multiple times.
        # This **shouldn't** ever happen.
        data_file_manager = await self.svcs_container.aget(DataFileManager)
        try:
            await data_file_manager.add_calculation(calculation_db_entry)
        except CalculationAlreadyExists:
            logger.error(f"Trying to add a calculation to the database which already exists: {calculation_db_entry}")
            return msg_specs.QCrBoxGenericResponse(
                response_to="server.cmd.handle_command_invocation_by_user",
                status=CalculationStatusEnum.FAILED,
                payload={"error": "Tried to add a new calculation to one which already exists"},
            )
        logger.debug("Updating calculation status to SUBMITTED after command request accepted")
        await data_file_manager.update_calculation_status_events(
            CalculationStatusDetails(
                calculation_id=user_invocation_request.calculation_id,
                status=CalculationStatusEnum.SUBMITTED,
                stdout="",
                stderr="",
                extra_info={},
            )
        )

        return msg_specs.QCrBoxGenericResponse(
            response_to="server.cmd.handle_command_invocation_by_user",
            status=CalculationStatusEnum.SUBMITTED,
            payload={"calculation_id": user_invocation_request.calculation_id},
        )

    def _set_up_asgi_server(self) -> None:
        """Initialise the ASGI server for providing the API endpoints."""

        async def get_nats_broker():
            return await self.svcs_container.aget(NatsBroker)

        async def get_data_file_manager():
            return await self.svcs_container.aget(DataFileManager)

        self.asgi_server = Litestar(
            route_handlers=[api_router, web_root_handler],
            lifespan=[self.lifespan_context],
            debug=settings.debug_mode,
            plugins=[structlog_plugin],
            dependencies={
                "nats_broker": Provide(get_nats_broker),
                "data_file_manager": Provide(get_data_file_manager),
            },
            openapi_config=OpenAPIConfig(
                title="QCrBox",
                version="0.3.0",
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
            },  # type: ignore
        )

    @on_qcrbox_startup
    async def init_database(self, purge_existing_db_tables: bool) -> None:
        """Initialise the registry database.

        Parameters
        ----------
        purge_existing_db_tables : bool
            If True, remove existing entries from the database to create an empty
            database.

        """
        logger.info(f"Initialising database...: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")


class TestQCrBoxServer(TestQCrBoxServerClientBase, QCrBoxServer):  # type: ignore
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
