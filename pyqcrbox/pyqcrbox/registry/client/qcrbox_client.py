import sys
from pathlib import Path
from typing import Optional

from faststream.nats import NatsBroker
from litestar import Litestar

from pyqcrbox import logger, msg_specs, settings, sql_models
from pyqcrbox.cli.helpers import get_repo_root
from pyqcrbox.helpers import generate_private_routing_key

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_client_asgi_server
from .executable_command import BaseCommand, ExecutableCommand

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        *,
        application_spec: sql_models.ApplicationSpecCreate,
        private_routing_key: Optional[str] = None,
        # broker: Optional[RabbitBroker] = None,
        nats_broker: Optional[NatsBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        super().__init__(nats_broker=nats_broker, asgi_server=asgi_server)
        self.application_spec = application_spec
        self.private_routing_key = private_routing_key or generate_private_routing_key()
        # self.routing_key_command_invocation = application_spec.routing_key_command_invocation
        self._calculations: list[BaseCommand] = []

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
