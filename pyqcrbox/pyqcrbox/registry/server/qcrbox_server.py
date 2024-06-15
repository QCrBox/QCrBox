from faststream.rabbit import ExchangeType

from pyqcrbox import logger, settings

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .api_endpoints import create_server_asgi_server
from .message_processing import server_side_message_dispatcher


class QCrBoxServer(QCrBoxServerClientBase):
    def _set_up_rabbitmq_broker(self) -> None:
        self.attach_message_dispatcher(
            queue_name=settings.rabbitmq.routing_key_qcrbox_registry,
            message_dispatcher=server_side_message_dispatcher,
            exchange_type=ExchangeType.DIRECT,
            routing_key="",
        )

    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_server_asgi_server(self.lifespan_context)

    @on_qcrbox_startup
    async def init_database(self, purge_existing_db_tables: bool) -> None:
        logger.info("Initialising database...")
        logger.debug(f"Database url: {settings.db.url}")
        settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
        logger.info("Finished initialising database...")

    async def publish(self, queue, msg):
        await self.broker.publish(msg, queue)


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
