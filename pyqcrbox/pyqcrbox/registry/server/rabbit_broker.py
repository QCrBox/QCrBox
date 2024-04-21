from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

from pyqcrbox.settings import settings

__all__ = ["create_rabbitmq_broker"]


class PingMessage(BaseModel):
    action: str = Literal["ping"]
    payload: dict = dict()


def create_rabbitmq_broker() -> RabbitBroker:
    broker = RabbitBroker(settings.rabbitmq.url, graceful_timeout=10)

    @broker.subscriber("qcrbox-registry")
    async def ping_handler(msg: PingMessage):
        logger.info("[DDD] Handling 'ping' message")
        return {"response_to": "ping", "msg": "Hello from QCrBox!"}

    # NOTE: we can also access the handler programmatically as follows:
    #
    # subscr = list(broker._subscribers.values())[0]
    # subscr.calls[0].handler

    # broker.hello_handler = hello
    return broker
