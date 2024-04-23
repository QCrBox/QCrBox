from typing import Optional

from faststream.rabbit import RabbitBroker
from litestar import Litestar

from pyqcrbox.helpers import generate_private_routing_key

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase
from .rabbit_broker import set_up_client_rabbitmq_broker

__all__ = ["QCrBoxClient", "TestQCrBoxClient"]


class QCrBoxClient(QCrBoxServerClientBase):
    def __init__(
        self,
        *,
        private_routing_key: Optional[str] = None,
        broker: Optional[RabbitBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        super().__init__(broker=broker, asgi_server=asgi_server)
        self.private_routing_key = private_routing_key or generate_private_routing_key()

    def _set_up_rabbitmq_broker(self):
        set_up_client_rabbitmq_broker(self.broker, private_routing_key=self.private_routing_key)

    async def publish(self, queue, msg):
        await self.broker.publish(msg, queue)


class TestQCrBoxClient(TestQCrBoxServerClientBase, QCrBoxClient):
    pass


def main():
    qcrbox_client = QCrBoxClient()
    qcrbox_client.run()


if __name__ == "__main__":
    QCrBoxClient()
