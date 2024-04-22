from contextlib import asynccontextmanager
from typing import AsyncContextManager, Optional

import anyio
import uvicorn
from anyio import TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from faststream.rabbit import RabbitBroker
from litestar import Litestar
from loguru import logger

from pyqcrbox.settings import settings

from .asgi_server import create_client_asgi_server
from .rabbit_broker import create_client_rabbitmq_broker


class QCrBoxClient:
    def __init__(
        self,
        *,
        private_routing_key: Optional[str] = None,
        broker: Optional[RabbitBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        self.broker = broker or create_client_rabbitmq_broker(private_routing_key)
        self.asgi_server = asgi_server or create_client_asgi_server(self.lifespan_context)
        uvicorn_config = uvicorn.Config(self.asgi_server)
        self.uvicorn_server = uvicorn.Server(uvicorn_config)

        self._shutdown_event = anyio.Event()

    @asynccontextmanager
    async def lifespan_context(self, _: Litestar) -> AsyncContextManager:
        logger.trace("==> Entering QCrBox client lifespan function...")
        await self.broker.start()
        try:
            logger.trace("Yielding control to Litestar app ...")
            yield
            logger.trace("Received control back from Litestar app ...")
        finally:
            logger.debug("Closing broker.")
            await self.broker.close()
            logger.debug("Done (broker is closed).")
        logger.trace("<== Exiting from QCrBox client lifespan function.")

    async def publish(self, queue, msg):
        await self.broker.publish(msg, queue)

    def run(self, purge_existing_db_tables: bool = False):
        try:
            anyio.run(self.serve, purge_existing_db_tables)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Shutting down.")

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

    def shutdown(self):
        logger.trace("Setting shutdown event")
        self._shutdown_event.set()
        logger.trace("Done, exiting shutdown()")

    async def _wait_for_and_handle_shutdown_request(self, cancel_scope: anyio.CancelScope):
        # Wait for shutdown event to be set. This can happen, for example, when the
        # user terminates the process presses (e.g. via Ctrl+C) or when the maximum
        # number of messages has been processed.
        logger.trace("Waiting for shutdown event to be set...")
        await self._shutdown_event.wait()
        logger.info("Received shutdown request, shutting down QCrBox client.")
        await self.uvicorn_server.shutdown()
        cancel_scope.cancel()


async def init_database(purge_existing_db_tables: bool) -> None:
    logger.info("Initialising database...")
    logger.debug(f"Database url: {settings.db.url}")
    settings.db.create_db_and_tables(purge_existing_tables=purge_existing_db_tables)
    logger.info("Finished initialising database...")


def main():
    qcrbox_client = QCrBoxClient()
    qcrbox_client.run()


if __name__ == "__main__":
    main()
