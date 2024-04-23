from loguru import logger

from pyqcrbox.settings import settings

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase, on_qcrbox_startup
from .asgi_server import create_server_asgi_server
from .rabbit_broker import set_up_server_rabbitmq_broker


class QCrBoxServer(QCrBoxServerClientBase):
    def _set_up_rabbitmq_broker(self) -> None:
        set_up_server_rabbitmq_broker(self.broker)

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
    qcrbox_server.run(purge_existing_db_tables=False)


if __name__ == "__main__":
    main()
