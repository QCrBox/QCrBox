import math
from typing import Optional

import anyio
from fastapi import FastAPI
from faststream.rabbit.fastapi import Logger, RabbitRouter
from faststream.types import SettingField
from loguru import logger
from pydantic import BaseModel
from uvicorn.config import Config
from uvicorn.server import Server

from pyqcrbox import settings


class MsgCounter:
    def __init__(self):
        self._shutdown_event = anyio.Event()
        self._max_messages = math.inf
        self.msg_counter = 0
        self.logger = logger

    @property
    def max_messages(self):
        return self._max_messages

    def increment_processed_message_counter(self):
        self.msg_counter += 1
        self.logger.debug(f"Current message count: {self.msg_counter}")
        if self.msg_counter >= self._max_messages:
            self.logger.info(f"Reached maximum number of messages ({self._max_messages}), shutting down.")
            self.request_shutdown()

    def request_shutdown(self):
        self._shutdown_event.set()


class QCrBoxRabbitRouter(RabbitRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._msg_counter = MsgCounter()

    def increment_processed_message_counter(self):
        self._msg_counter.increment_processed_message_counter()


# router = RabbitRouter("amqp://guest:guest@localhost:5672/")
router = QCrBoxRabbitRouter(settings.rabbitmq.url)


class Incoming(BaseModel):
    m: dict


@router.subscriber("test")
@router.publisher("response")
async def hello(m: Incoming, logger: Logger):
    logger.info(m)
    router.increment_processed_message_counter()
    return {"response": "Hello, Rabbit!"}


@router.get("/")
async def hello_http():
    return "Hello, HTTP!"


class QCrBoxFastAPI(FastAPI):
    def __init__(self, router: QCrBoxRabbitRouter):
        super().__init__(lifespan=router.lifespan_context)
        self.include_router(router)
        self.logger = logger

    def run(
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
        if max_messages is None:  # pragma: no cover
            pass
        else:
            assert isinstance(max_messages, (int, float))
            self._max_messages = max_messages
            self.logger.info(f"{self} will shut down after {self._max_messages} processed messages.")

        logger.info("Starting QCrBox server")
        try:
            # uvicorn.run("pyqcrbox.registry.base_fastapi_v2:app", host="0.0.0.0", port=8007, reload=True)
            # uvicorn.run(self, host="0.0.0.0", port=8007, reload=False)
            config = Config(self, host="0.0.0.0", port=8009)
            server = Server(config=config)
            anyio.run(server.serve)
        except Exception as exc:
            logger.error(f"[DDD] {exc=}")
            raise


app = QCrBoxFastAPI(router)


def main():
    # logger.info("Starting QCrBox server")
    # try:
    #     uvicorn.run("pyqcrbox.registry.base_fastapi_v2:app", host="0.0.0.0", port=8007, reload=True)
    # except Exception as exc:
    #     logger.error(f"[DDD] {exc=}")
    #     raise
    app.run()


if __name__ == "__main__":
    app.run()
