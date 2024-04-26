from typing import Optional

from faststream.rabbit import RabbitBroker
from litestar import Litestar

from pyqcrbox import logger, msg_specs, settings, sql_models
from pyqcrbox.cli.helpers import get_repo_root
from pyqcrbox.helpers import generate_private_routing_key
from pyqcrbox.registry.client.message_processing import client_side_message_dispatcher

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .asgi_server import create_client_asgi_server

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        *,
        application_spec: sql_models.ApplicationSpecCreate,
        private_routing_key: Optional[str] = None,
        broker: Optional[RabbitBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        super().__init__(broker=broker, asgi_server=asgi_server)
        self.application_spec = application_spec
        self.private_routing_key = private_routing_key or generate_private_routing_key()

    def _set_up_rabbitmq_broker(self) -> None:
        self.declare_rabbitmq_message_handler(
            routing_key=self.private_routing_key,
            message_dispatcher=client_side_message_dispatcher,
        )

    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_client_asgi_server(self.lifespan_context)

    @on_qcrbox_startup
    async def send_registration_request(self):
        logger.debug("Sending registration request to QCrBox server")
        msg = msg_specs.RegisterApplication(
            action="register_application",
            payload=msg_specs.PayloadForRegisterApplication(
                application_spec=self.application_spec,
                private_routing_key=self.private_routing_key,
            ),
        )
        await self.broker.publish(
            msg,
            settings.rabbitmq.routing_key_qcrbox_registry,
            rpc=True,
            reply_to=self.private_routing_key,
        )

    async def publish(self, queue, msg):
        await self.broker.publish(msg, queue)


class TestQCrBoxClient(TestQCrBoxServerClientBase, QCrBoxClient):
    pass


def main():
    repo_root = get_repo_root()
    sample_spec_file = repo_root.joinpath("services/applications/olex2_linux/config_olex2.yaml")
    application_spec = sql_models.ApplicationSpecCreate.from_yaml_file(sample_spec_file)
    qcrbox_client = QCrBoxClient(application_spec=application_spec)
    qcrbox_client.run(port=settings.registry.client.port)


if __name__ == "__main__":
    main()
