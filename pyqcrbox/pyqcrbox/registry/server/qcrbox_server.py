import anyio
from anyio import TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from loguru import logger

from pyqcrbox.settings import settings

from ..shared import QCrBoxServerClientBase, TestQCrBoxServerClientBase
from .asgi_server import create_asgi_server
from .rabbit_broker import set_up_server_rabbitmq_broker


class QCrBoxServer(QCrBoxServerClientBase):
    def _set_up_rabbitmq_broker(self) -> None:
        set_up_server_rabbitmq_broker(self.broker)

    def _set_up_asgi_server(self) -> None:
        self.asgi_server = create_asgi_server(self.lifespan_context)

    async def publish(self, queue, msg):
        await self.broker.publish(msg, queue)

    async def serve(self, purge_existing_db_tables: bool = False, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
        await init_database(purge_existing_db_tables)

        logger.trace("Entering QCrBoxServer.serve()...")

        try:
            async with anyio.create_task_group() as tg:
                logger.info("Starting uvicorn server...")
                tg.start_soon(self.uvicorn_server.serve)
                tg.start_soon(self._wait_for_and_handle_shutdown_request, tg.cancel_scope)
                while not self.uvicorn_server.started:
                    await anyio.sleep(0.01)
                task_status.started()
            logger.trace("Exited task group that served uvicorn...")
            # await self.router.shutdown()
            # logger.info("Bar!")
        except ExceptionGroup as e:  # pragma: no cover
            for ex in e.exceptions:
                raise ex from None


class TestQCrBoxServer(TestQCrBoxServerClientBase, QCrBoxServer):
    pass


async def init_database(purge_existing_db_tables: bool) -> None:
    logger.info("Initialising database...")
    logger.debug(f"Database url: {settings.db.url}")
    settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
    logger.info("Finished initialising database...")


def main():
    qcrbox_server = QCrBoxServer()
    qcrbox_server.run()


if __name__ == "__main__":
    main()
