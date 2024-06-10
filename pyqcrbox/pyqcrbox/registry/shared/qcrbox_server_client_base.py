import contextlib
import inspect
from abc import ABCMeta, abstractmethod
from typing import AsyncContextManager, Callable, Optional, assert_never

import aiormq
import anyio
import stamina
import svcs
import uvicorn
from anyio import TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from faststream.rabbit import RabbitBroker
from litestar import Litestar
from litestar.testing import AsyncTestClient, TestClient
from loguru import logger

from pyqcrbox import QCRBOX_SVCS_REGISTRY, settings

from ..shared.message_dispatch import declare_rabbitmq_message_handler

__all__ = ["QCrBoxServerClientBase", "TestQCrBoxServerClientBase"]


def on_qcrbox_startup(func):
    func._is_qcrbox_startup_hook = True
    sig = inspect.signature(func)
    func._param_names = [name for name in sig.parameters.keys() if name != "self"]
    return func


class QCrBoxServerClientBase(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        broker: Optional[RabbitBroker] = None,
        asgi_server: Optional[Litestar] = None,
        svcs_registry: Optional[svcs.Registry] = None,
    ):
        self.broker = broker or RabbitBroker(settings.rabbitmq.url, graceful_timeout=10)
        self.svcs_registry = svcs_registry or QCRBOX_SVCS_REGISTRY

        self.svcs_registry.register_value(RabbitBroker, self.broker)

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
        assert self.host is not None
        assert self.port is not None

        self._set_up_asgi_server()

        uvicorn_config = uvicorn.Config(
            self.asgi_server,
            host=self.host,
            port=self.port,
        )
        self.uvicorn_server = uvicorn.Server(uvicorn_config)

    async def execute_startup_hooks(self, **kwargs):
        for name in dir(self):
            func = getattr(self, name)
            if inspect.ismethod(func) and hasattr(func, "_is_qcrbox_startup_hook"):
                cur_kwargs = {name: value for (name, value) in kwargs.items() if name in func._param_names}
                logger.trace(f"Executing startup hook {func.__name__!r} with kwargs={cur_kwargs}")
                if not inspect.iscoroutinefunction(func):
                    func(**cur_kwargs)
                else:
                    await func(**cur_kwargs)

    @contextlib.asynccontextmanager
    async def lifespan_context(self, _: Litestar) -> AsyncContextManager:
        logger.trace(f"==> Entering {self.clsname} lifespan function...")

        self._set_up_rabbitmq_broker()

        for attempt in stamina.retry_context(on=aiormq.exceptions.AMQPConnectionError, timeout=60.0, attempts=None):
            with attempt:
                await self.broker.start()

        await self.execute_startup_hooks(**self._run_kwargs)

        try:
            logger.trace("Yielding control to ASGI server ...")
            yield
            logger.trace("Received control back from ASGI server ...")
        finally:
            with contextlib.suppress(KeyError):
                logger.trace("Closing broker.")
                await self.broker.close()
                logger.trace("Done (broker is closed).")

                logger.trace("Closing SVCS registry.")
                await self.svcs_registry.aclose()
                logger.trace("Done (SVCS registry is closed).")

        logger.trace(f"<== Exiting from {self.clsname} lifespan function.")

    def declare_rabbitmq_message_handler(self, *, routing_key: str, message_dispatcher: Callable):
        declare_rabbitmq_message_handler(
            self, self.broker, routing_key=routing_key, msg_dispatcher_func=message_dispatcher
        )

    def run(self, host: Optional[str] = None, port: Optional[int] = None, **kwargs):
        self.host = host or "127.0.0.1"
        self.port = port or 8000
        logger.trace(f"Running {self.clsname} with {kwargs=}")
        self._run_kwargs = kwargs
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
        logger.info(f"Received shutdown request, shutting down {self.clsname}.")
        await self.uvicorn_server.shutdown()
        cancel_scope.cancel()


class TestQCrBoxServerClientBase(QCrBoxServerClientBase):
    @contextlib.asynccontextmanager
    async def run(
        self,
        host: Optional[str] = None,
        port: Optional[str] = None,
        task_status: TaskStatus[None] = TASK_STATUS_IGNORED,
        **kwargs,
    ):
        self.host = host or "127.0.0.1"
        self.port = port or 0  # zero means "choose a random unused port"
        self._run_kwargs = kwargs
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
                yield self
                self.shutdown()
            logger.trace("Exited task group that served uvicorn...")
        except ExceptionGroup as e:  # pragma: no cover
            for ex in e.exceptions:
                raise ex from None

    @contextlib.asynccontextmanager
    async def web_client(self):
        async with AsyncTestClient(app=self.asgi_server) as web_client:
            yield web_client

    @contextlib.contextmanager
    def web_client_sync(self):
        with TestClient(app=self.asgi_server) as web_client:
            yield web_client

    def handler_was_called(self, queue_name):
        return self.get_mock_handler(queue_name).called

    def get_mock_handler(self, queue_name):
        subscr = self._get_subscriber(queue_name)
        try:
            assert len(subscr.calls) == 1
            handler = subscr.calls[0].handler
        except AssertionError:
            logger.warning(
                f"More than one handler found for queue {queue_name!r}. "
                "Did you start more than one RabbitBroker instance? "
                "Arbitrarily returning the last handler."
            )
            handler = subscr.calls[-1].handler

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
