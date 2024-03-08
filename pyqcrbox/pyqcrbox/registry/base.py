import logging
import math
from typing import Optional

import anyio
from anyio import CancelScope
from faststream import FastStream
from faststream.log import logger
from faststream.rabbit import RabbitBroker
from faststream.types import SettingField
from typing_extensions import override


class QCrBoxFastStream(FastStream):
    def __init__(
        self,
        broker: Optional[RabbitBroker] = None,
        log_level: Optional[int | str] = logging.INFO,
        title: str = "QCrBox",
        version: str = "0.0.1",
        description: str = "",
        **kwargs,
    ) -> None:
        self.log_level = log_level
        logger.setLevel(self.log_level)
        super().__init__(broker=broker, logger=logger, title=title, version=version, description=description, **kwargs)
        self.context.set_global("logger", logger)

        self._shutdown_event = anyio.Event()
        self._max_messages = math.inf
        self.msg_counter = 0
        self.clsname = self.__class__.__name__
        self._was_run_before = False

    def __str__(self):
        return f"{self.clsname} {self.title!r}"

    @property
    def max_messages(self):
        return self._max_messages

    async def _wait_for_and_handle_shutdown_request(self, cancel_scope: CancelScope):
        # Wait for shutdown event to be set. This can happen, for example, when the
        # user terminates the process presses (e.g. via Ctrl+C) or when the maximum
        # number of messages has been processed.
        await self._shutdown_event.wait()
        # self.logger.info(f"Received shutdown notification, shutting down {self.title}.")
        await self._shutdown()
        cancel_scope.cancel()  # ensure any other running tasks are cancelled

    async def _optional_shutdown_after_delay(self, cancel_scope: CancelScope, delay: Optional[float] = None) -> None:
        if delay is not None:  # pragma: no cover
            self.logger.info(f"{self} will shut down automatically after {delay:.1f} seconds.")
            await anyio.sleep(delay)
            self.logger.info(f"Reached shutdown delay of {delay:.1f} seconds, shutting down.")
            await self._shutdown()
            cancel_scope.cancel()  # ensure any other running tasks are cancelled

    def request_shutdown(self):
        self._shutdown_event.set()

    def increment_processed_message_counter(self, routing_key: Optional[str] = None):
        self.msg_counter += 1
        if self.msg_counter >= self._max_messages:
            self.logger.info(f"Reached maximum number of messages ({self._max_messages}), shutting down.")
            self.request_shutdown()

    @override
    async def run(
        self,
        max_messages: Optional[int] = None,
        shutdown_delay: Optional[float] = None,
        run_extra_options: Optional[dict[str, SettingField]] = None,
    ) -> None:
        """Run QCrBoxFastStream Application.

        Args:
            max_messages: maximum number of messages to process before shutting down
                (run indefinitely if not specified).
            shutdown_delay: delay (in seconds) after which the app is automatically shut down
                (run indefinitely if not specified)
            run_extra_options: extra options for running the app

        Returns:
            Block an event loop until stopped
        """
        assert self.broker, "You should setup a broker"  # nosec B101

        if self._was_run_before:
            raise NotImplementedError(
                "Cannot currently re-run a QCrBoxFastStream app that was run before. Please create a new one instead."
            )
        self._was_run_before = True

        if max_messages is not None:
            assert isinstance(max_messages, (int, float))
            self._max_messages = max_messages
            self.logger.info(f"{self} will shut down after {self._max_messages} processed messages.")
        else:  # pragma: no cover
            pass

        async with self.lifespan_context(**(run_extra_options or {})):
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._start, self.log_level, run_extra_options)
                    tg.start_soon(self._wait_for_and_handle_shutdown_request, tg.cancel_scope)
                    tg.start_soon(self._optional_shutdown_after_delay, tg.cancel_scope, shutdown_delay)
                    await self._stop(self.log_level)
                    tg.cancel_scope.cancel()  # pragma: no cover
            except ExceptionGroup as e:  # pragma: no cover
                for ex in e.exceptions:
                    raise ex from None
