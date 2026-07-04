import asyncio
import contextlib
import inspect
from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator

import anyio
import nats.errors
import stamina
import svcs
import uvicorn
from anyio import TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from faststream.nats import NatsBroker
from litestar import Litestar
from litestar.testing import AsyncTestClient, TestClient

from pyqcrbox._version import __version__ as pyqcrbox_version
from pyqcrbox.data_management import DataManager
from pyqcrbox.logging import logger
from pyqcrbox.services.persistence import NatsPersistenceAdapter, SQLitePersistenceAdapter
from pyqcrbox.services.services_registry import QCRBOX_GLOBAL_SERVICES_REGISTRY

__all__ = ["QCrBoxServerClientBase", "TestQCrBoxServerClientBase"]


def on_qcrbox_startup(func):
    func._is_qcrbox_startup_hook = True
    sig = inspect.signature(func)
    func._param_names = [name for name in sig.parameters if name != "self"]
    return func


class QCrBoxServerClientBase(metaclass=ABCMeta):
    def __init__(self, *, asgi_server: Litestar | None = None):
        self.svcs_container = svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY)
        self.nats_broker = asyncio.run(self.svcs_container.aget(NatsBroker))  # !! bad !!
        self.data_manager = asyncio.run(self.svcs_container.aget(DataManager))  # !! bad !!
        self.nats_persistence_adapter = NatsPersistenceAdapter()
        self.sqlite_persistence_adapter = SQLitePersistenceAdapter()


        # If not passed explicitly, the ASGI server and uvicorn server
        # will be set up when `.serve()` is called.
        self.asgi_server = asgi_server
        self.uvicorn_server = None

        self._private_inbox = None  # will be created after NATS broker startup
        self._shutdown_event = anyio.Event()
        self._notification_events = {}

        self.calculations = {}
        self.kv_applications = None
        self.kv_calculation_status = None

        self.host = None
        self.port = None

    @property
    def clsname(self):
        return self.__class__.__name__

    @abstractmethod
    def _set_up_nats_broker(self):
        pass

    @abstractmethod
    def _set_up_asgi_server(self) -> None:
        pass

    def _set_up_uvicorn_server(self) -> None:
        if self.uvicorn_server is not None:
            raise RuntimeError("Uvicorn server has already been set up (unexpectedly).")
        assert self.nats_broker is not None
        assert self.host is not None
        assert self.port is not None

        self._set_up_asgi_server()
        assert self.asgi_server is not None

        uvicorn_config = uvicorn.Config(
            self.asgi_server,
            host=self.host,
            port=self.port,
        )
        self.uvicorn_server = uvicorn.Server(uvicorn_config)

    async def _start_broker(self):
        for attempt in stamina.retry_context(on=nats.errors.NoServersError, timeout=10.0, attempts=None):
            with attempt:
                await self.nats_broker.start()

    async def _close_broker(self):
        await self.nats_broker.close()

    async def _create_private_nats_inbox(self):
        await self._start_broker()
        self._private_inbox = await self.nats_broker.new_inbox()
        logger.debug(f"Created private NATS inbox: {self._private_inbox}")
        await self._close_broker()

    async def _wait_for_and_handle_shutdown_request(self, cancel_scope: anyio.CancelScope):
        assert self.uvicorn_server is not None
        # Wait for shutdown event to be set. This can happen, for example, when the
        # user terminates the process presses (e.g. via Ctrl+C) or when the maximum
        # number of messages has been processed.
        logger.debug("Waiting for shutdown event to be set...")
        await self._shutdown_event.wait()
        logger.info(f"Received shutdown request, shutting down {self.clsname}.")
        await self._run_custom_shutdown_tasks()
        if self.uvicorn_server.started:
            await self.uvicorn_server.shutdown()
        cancel_scope.cancel()

    async def _set_up_key_value_store(self):
        self.kv_applications = await self.nats_broker.key_value(bucket="applications")

    async def _run_custom_shutdown_tasks(self):  # noqa: B027
        """Run custom shutdown tasks.

        This is a no-op by default but can be used by derived classes to run
        tasks when the shutdown signal is received.
        """
        pass

    async def _run_pre_broker_close_tasks(self):  # noqa: B027
        """Run tasks just before the NATS broker is closed on shutdown.

        Unlike `_run_custom_shutdown_tasks` (which only runs on the internal
        shutdown-event path), this runs whenever the ASGI lifespan exits, so
        it is also reached on signal-driven shutdown. The broker is still
        connected at this point, so derived classes can send final messages
        (e.g. a client deregistration).
        """
        pass

    @property
    def private_inbox(self):
        if self._private_inbox is not None:
            return self._private_inbox

        raise RuntimeError(
            "Private inbox has not been set up yet (broker must have been started "
            "to retrieve a unique inbox name from NATS server)."
        )

    async def execute_startup_hooks(self, **kwargs):
        for name in dir(self):
            func = getattr(self, name)
            if inspect.ismethod(func) and hasattr(func, "_is_qcrbox_startup_hook"):
                cur_kwargs = {name: value for (name, value) in kwargs.items() if name in func._param_names}  # type: ignore
                logger.debug(f"Executing startup hook {func.__name__!r} with kwargs={cur_kwargs}")
                if not inspect.iscoroutinefunction(func):
                    func(**cur_kwargs)
                else:
                    await func(**cur_kwargs)

    @contextlib.asynccontextmanager
    async def lifespan_context(self, _: Litestar) -> AsyncGenerator:
        logger.debug(f"==> Entering {self.clsname} lifespan function...")

        async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
            self.svcs_container = container
            self.nats_broker = await self.svcs_container.aget(NatsBroker)
            self.data_manager = await self.svcs_container.aget(DataManager)

            await self._create_private_nats_inbox()
            self._set_up_nats_broker()
            await self._start_broker()
            await self._set_up_key_value_store()
            await self.execute_startup_hooks(**self._run_kwargs)

            try:
                logger.debug("Yielding control to ASGI server...")
                yield
                logger.debug("Received control back from ASGI server...")
            finally:
                with contextlib.suppress(Exception):
                    await self._run_pre_broker_close_tasks()
                with contextlib.suppress(KeyError):
                    logger.debug("Closing broker.")
                    await self.nats_broker.close()
                    logger.debug("Broker is closed.")

        logger.debug(f"<== Exiting from {self.clsname} lifespan function.")

    def run(self, host: str | None = None, port: int | None = None, **kwargs):
        self.host = host or "127.0.0.1"
        self.port = port or 8000
        logger.debug(f"Running {self.clsname} with {kwargs=}")
        logger.debug(f"pyqcrbox version: {pyqcrbox_version}")
        self._run_kwargs = kwargs
        try:
            anyio.run(self.serve)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Shutting down.")

    async def serve(self, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
        self._set_up_uvicorn_server()
        assert self.uvicorn_server is not None

        logger.debug(f"Entering {self.clsname}.serve()...")

        try:
            async with anyio.create_task_group() as tg:
                logger.info("Starting uvicorn server...")
                tg.start_soon(self.uvicorn_server.serve)
                tg.start_soon(self._wait_for_and_handle_shutdown_request, tg.cancel_scope)
                while not self.uvicorn_server.started:
                    await anyio.sleep(0.01)
                task_status.started()
            logger.debug("Exited task group that served uvicorn...")
        except ExceptionGroup as e:  # pragma: no cover
            logger.error(f"[EEE] Exception group: {e}")
            for ex in e.exceptions:
                logger.error(f"      Exception: {ex}")
                raise ex from None

    def shutdown(self):
        logger.debug("Setting shutdown event")
        self._shutdown_event.set()
        logger.debug("Done, exiting shutdown()")


class TestQCrBoxServerClientBase(QCrBoxServerClientBase):
    @contextlib.asynccontextmanager
    async def run(  # type: ignore
        self,
        host: str | None = None,
        port: int | None = None,
        task_status: TaskStatus[None] = TASK_STATUS_IGNORED,
        **kwargs,
    ):
        self.host = host or "127.0.0.1"
        self.port = port or 0  # zero means "choose a random unused port"
        self._run_kwargs = kwargs
        self._set_up_uvicorn_server()

        logger.debug(f"Entering {self.clsname}.serve()...")
        assert self.uvicorn_server is not None
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
            logger.debug("Exited task group that served uvicorn...")
        except ExceptionGroup as e:  # pragma: no cover
            for ex in e.exceptions:
                raise ex from None

    @contextlib.asynccontextmanager
    async def web_client(self):
        assert self.asgi_server is not None
        async with AsyncTestClient(app=self.asgi_server) as web_client:
            yield web_client

    @contextlib.contextmanager
    def web_client_sync(self):
        assert self.asgi_server is not None
        with TestClient(app=self.asgi_server) as web_client:
            yield web_client
