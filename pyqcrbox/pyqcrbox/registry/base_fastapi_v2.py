import math

import anyio
import uvicorn
from fastapi import FastAPI
from faststream.rabbit.fastapi import Logger, RabbitRouter
from loguru import logger
from pydantic import BaseModel

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


app = QCrBoxFastAPI(router)


def main():
    logger.info("Starting QCrBox server")
    try:
        uvicorn.run("pyqcrbox.registry.base_fastapi_v2:app", host="0.0.0.0", port=8007, reload=True)
    except Exception as exc:
        logger.error(f"[DDD] {exc=}")
        raise


if __name__ == "__main__":
    main()
