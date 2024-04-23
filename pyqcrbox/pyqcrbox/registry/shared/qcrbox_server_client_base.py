from abc import ABCMeta, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Optional, assert_never

import anyio
import uvicorn
from anyio import TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from faststream.rabbit import RabbitBroker
from litestar import Litestar
from litestar.testing import AsyncTestClient
from loguru import logger

from pyqcrbox import settings

__all__ = ["QCrBoxServerClientBase", "TestQCrBoxServerClientBase"]


class QCrBoxServerClientBase(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        broker: Optional[RabbitBroker] = None,
        asgi_server: Optional[Litestar] = None,
    ):
        self.broker = broker or RabbitBroker(settings.rabbitmq.url, graceful_timeout=10)

        # If not passed explicitly, the ASGI server and uvicorn server
        # will be set up when `.serve()` is called.
        self.asgi_server = asgi_server
        self.uvicorn_server = None

        self._shutdown_event = anyio.Event()

    @property
    def clsname(self):
        return self.__class__.__name__

    @abstractmethod
    def _set_up_rabbitmq_broker(self):
        assert_never(self)

    @abstractmethod
    def _set_up_asgi_server(self) -> None:
        assert_never(self)

    def _set_up_uvicorn_server(self) -> None:
        if self.uvicorn_server is not None:
            raise RuntimeError("Uvicorn server has already been set up (unexpectedly).")

        assert self.broker is not None

        self._set_up_asgi_server()

        uvicorn_config = uvicorn.Config(self.asgi_server)
        self.uvicorn_server = uvicorn.Server(uvicorn_config)

    @asynccontextmanager
    async def lifespan_context(self, _: Litestar) -> AsyncContextManager:
        logger.trace(f"==> Entering {self.clsname} lifespan function...")

        await self.broker.start()
        try:
            logger.trace("Yielding control to ASGI server ...")
            yield
            logger.trace("Received control back from ASGI server ...")
        finally:
            logger.debug("Closing broker.")
            await self.broker.close()
            logger.trace("Done (broker is closed).")

        logger.trace(f"<== Exiting from {self.clsname} lifespan function.")

    def run(self):
        try:
            anyio.run(self.serve)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Shutting down.")

    async def serve(self, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
        self._set_up_uvicorn_server()

        logger.trace(f"Entering {self.clsname}.serve()...")

        try:
            async with anyio.create_task_group() as tg:
                logger.info("Starting uvicorn server...")
                tg.start_soon(self.uvicorn_server.serve)
                tg.start_soon(self._wait_for_and_handle_shutdown_request, tg.cancel_scope)
                while not self.uvicorn_server.started:
                    await anyio.sleep(0.01)
                task_status.started()
            logger.trace("Exited task group that served uvicorn...")
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


class TestQCrBoxServerClientBase(QCrBoxServerClientBase):
    @asynccontextmanager
    async def run(self):
        self._set_up_uvicorn_server()
        yield self
        self.shutdown()

    @asynccontextmanager
    async def web_client(self):
        async with AsyncTestClient(app=self.asgi_server) as web_client:
            yield web_client

    def get_mock_handler(self, queue_name):
        subscr = self._get_subscriber(queue_name)
        assert len(subscr.calls) == 1
        handler = subscr.calls[0].handler
        return handler.mock

    def _get_subscriber(self, queue_name):
        cands = []
        for s in self.broker._subscribers.values():
            if s.queue.name == queue_name:
                cands.append(s)

        match len(cands):
            case 1:
                return cands[0]
            case 0:
                raise ValueError(f"No subscriber found for queue {queue_name!r}")
            case _:
                raise ValueError(f"More than one subscriber found for queue {queue_name!r}")
