from loguru import logger

from pyqcrbox.settings import settings

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, create_message_handler, on_qcrbox_startup
from .asgi_server import create_server_asgi_server
from .message_processing import server_side_message_dispatcher


class QCrBoxServer(QCrBoxServerClientBase):
    def _set_up_rabbitmq_broker(self) -> None:
        # Note: `@broker.subscriber(...)` is typically used as a decorator on a
        #       function definition. However, below we call it directly with the
        #       existing function `msg_handler` as an argument. This will
        #       automatically register this function as a handler for incoming messages.
        declare_as_incoming_msg_handler = self.broker.subscriber(settings.rabbitmq.routing_key_qcrbox_registry)
        msg_handler = create_message_handler(server_side_message_dispatcher)
        declare_as_incoming_msg_handler(msg_handler)

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
    qcrbox_server.run(port=settings.registry.server.port, purge_existing_db_tables=False)


if __name__ == "__main__":
    main()
