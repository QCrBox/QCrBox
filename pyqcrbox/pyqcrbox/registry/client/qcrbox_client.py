import sys
from pathlib import Path
from typing import Optional

from faststream.nats import NatsBroker
from litestar import Litestar

from pyqcrbox import helpers, logger, msg_specs, settings, sql_models
from pyqcrbox.cli.helpers import get_repo_root
from pyqcrbox.helpers import generate_private_routing_key
from pyqcrbox.registry.shared.calculation_status import update_calculation_status_in_nats_kv

from ..shared import CalculationStatusEnum, QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_client_asgi_server
from .client_status import ClientStatus, ClientStatusEnum
from .executable_command import BaseCommand, ExecutableCommand

# from .message_processing.command_invocation_request import handle_command_invocation_request_via_nats

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        *,
        application_spec: sql_models.ApplicationSpecCreate,
        client_id: str = "anonymous_client",
        private_routing_key: Optional[str] = None,
        # broker: Optional[RabbitBroker] = None,
        nats_broker: Optional[NatsBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        super().__init__(nats_broker=nats_broker, asgi_server=asgi_server)
        self.application_spec = application_spec
        self.client_id = client_id
        self.private_routing_key = private_routing_key or generate_private_routing_key()
        # self.routing_key_command_invocation = application_spec.routing_key_command_invocation
        self._calculations: list[BaseCommand] = []
        self.status = ClientStatus(ClientStatusEnum.IDLE)

    # def _set_up_rabbitmq_broker(self) -> None:
    #     self.set_up_message_dispatcher(
    #         queue_name=self.private_routing_key,
    #         message_dispatcher=client_side_message_dispatcher,
    #     )
    #     self.set_up_message_dispatcher(
    #         queue_name=self.routing_key_command_invocation,
    #         # TODO: use separate dispatcher from the one for private routing key
    #         message_dispatcher=client_side_message_dispatcher,
    #     )

    def _set_up_nats_broker(self) -> None:
        logger.warning("TODO: set up NATS broker for client")

        slug_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.application_spec.version)

        self.nats_broker.subscriber(f"client.cmd.handle_invocation_request.{slug_sanitized}.{version_sanitized}")(
            self.handle_command_invocation_request_from_server
        )
        self.nats_broker.subscriber(f"{self.private_inbox}.cmd.execute")(self.handle_command_execution)
        self.nats_broker.subscriber(f"{self.private_inbox}.calc.status")(self.get_calculation_status)

        # # Subscriber for command invocation requests
        # subject = f"cmd-invocation.request.{self.application_spec.nats_subject}"
        # # self.nats_broker.subscriber(subject)(handle_command_invocation_request_via_nats)
        #
        # @self.nats_broker.subscriber(subject)
        # async def handle_command_invocation_request_via_nats(msg: msg_specs.CommandInvocationRequest):
        #     assert msg.action == "command_invocation_request"
        #     logger.debug(f"Received command invocation request: {msg}")
        #
        #     msg_indicate_availability = msg_specs.ClientIndicatesAvailabilityToExecuteCommand(
        #         action="client_is_available_to_execute_command",
        #         payload=msg_specs.PayloadForClientIsAvailableToExecuteCommand(
        #             cmd_invocation_payload=msg.payload,
        #             # private_routing_key=self.private_routing_key,
        #         ),
        #     )
        #
        #     server_response = await self.nats_broker.publish(
        #         msg_indicate_availability,
        #         f"cmd-invocation.response.{msg.payload.correlation_id}",
        #         rpc=True,
        #         rpc_timeout=settings.nats.rpc_timeout,
        #         raise_timeout=True,
        #     )
        #     logger.debug(f"Received response from server: {server_response}")

    async def handle_command_invocation_request_from_server(self, msg: msg_specs.CommandInvocationRequestNATS):
        # logger.info(f"Received command invocation request: {msg!r} (current client status: {self.status})")
        logger.info(f"Received command invocation request: {msg!r} (current client status: TODO)")

        response_msg = msg_specs.CommandInvocationClientResponseNATS(
            application_slug=msg.application_slug,
            application_version=msg.application_version,
            client_id=self.client_id,
            client_is_available=self.status.is_available,
            calculation_id=msg.calculation_id,
            private_inbox_prefix=self.private_inbox,
        )

        if self.status.is_available:
            self.status.set_pending()

        return response_msg

    async def handle_discard_command_invocation(self, msg: msg_specs.DiscardCommandInvocationNATS):
        logger.info(f"Received request to discard command invocation: {msg!r} (current status: {self.status}")
        self.status.set_idle()

    async def handle_command_execution(self, msg: msg_specs.CommandExecutionRequestNATS):
        logger.info(f"Received command execution request: {msg!r} (current status: {self.status}")
        self.status.set_busy()

        cmd = self.get_executable_command(msg.command_name)
        calc = await cmd.execute_in_background(**msg.arguments, _calculation_id=msg.calculation_id)
        # logger.debug(f"Storing calculation details: {calc!r}")
        self.calculations[msg.calculation_id] = calc
        # logger.debug(f"Storing KV value for {msg.calculation_id=}")
        await update_calculation_status_in_nats_kv(msg.calculation_id, CalculationStatusEnum.RUNNING)

        await calc.wait_until_finished()
        await update_calculation_status_in_nats_kv(msg.calculation_id, calc.status)

        self.status.set_idle()

    async def get_calculation_status(
        self, msg: msg_specs.GetCalculationStatusNATS
    ) -> msg_specs.CalculationStatusResponseNATS:
        logger.debug(f"Current contents of self.calculations: {self.calculations.items()!r}")
        logger.debug(f"Retrieving calculation details for calculation_id={msg.calculation_id!r}")
        status = self.calculations[msg.calculation_id].status
        logger.debug(f"Current calculation status: {status!r}")
        response = msg_specs.CalculationStatusResponseNATS(calculation_id=msg.calculation_id, status=status)
        return response

    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_client_asgi_server(self.lifespan_context)

    async def _run_custom_shutdown_tasks(self):
        logger.debug("Terminating running calculations...")
        logger.warning("TODO: actually terminate any running calculations...")
        for calc in self._calculations:
            await calc.terminate()

    def get_executable_command(self, command_name):
        cmd_spec = self.application_spec.get_command_spec(command_name)
        return ExecutableCommand(cmd_spec)

    # @on_qcrbox_startup
    # async def send_registration_request(self):
    #     logger.debug("Sending registration request to QCrBox server")
    #     msg = msg_specs.RegisterApplication(
    #         action="register_application",
    #         payload=msg_specs.PayloadForRegisterApplication(
    #             application_spec=self.application_spec,
    #             private_routing_key=self.private_routing_key,
    #         ),
    #     )
    #     await self.broker.publish(
    #         msg,
    #         settings.rabbitmq.routing_key_qcrbox_registry,
    #         # rpc=True,
    #         reply_to=self.private_routing_key,
    #     )
    #
    #     resp = await self.nats_broker.publish(
    #         msg, "register-application", rpc=True, rpc_timeout=settings.nats.rpc_timeout, raise_timeout=True
    #     )
    #     logger.error(f"Received response to registration request: {resp=}")

    @on_qcrbox_startup
    async def send_registration_request_via_nats(self):
        logger.debug("Sending registration request to QCrBox server")
        msg = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.PayloadForRegisterApplication(
                application_spec=self.application_spec,
                private_routing_key=self.private_routing_key,
            ),
        )

        resp = await self.nats_broker.publish(
            msg, "register-application", rpc=True, rpc_timeout=settings.nats.rpc_timeout, raise_timeout=True
        )
        logger.debug(f"Received response to registration request: {resp=}")
        logger.warning("TODO: raise error if registration failed!")

    # async def publish(self, queue, msg):
    #     await self.broker.publish(msg, queue)


class TestQCrBoxClient(TestQCrBoxServerClientBase, QCrBoxClient):
    pass


def main():
    repo_root = get_repo_root(__file__)

    try:
        application_config_file = Path(sys.argv[1])
    except IndexError:
        application_config_file = repo_root.joinpath("services/applications/olex2_linux/config_olex2.yaml")

    application_spec = sql_models.ApplicationSpecCreate.from_yaml_file(application_config_file)

    qcrbox_client = QCrBoxClient(application_spec=application_spec)
    qcrbox_client.run(host=settings.registry.client.host, port=settings.registry.client.port)


if __name__ == "__main__":
    main()
