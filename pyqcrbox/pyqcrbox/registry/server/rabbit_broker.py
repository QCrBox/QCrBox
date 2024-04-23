from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

__all__ = ["set_up_server_rabbitmq_broker"]


class PingMessage(BaseModel):
    action: str = Literal["ping"]
    payload: dict = dict()


def set_up_server_rabbitmq_broker(broker: RabbitBroker) -> None:
    @broker.subscriber("qcrbox-registry")
    async def ping_handler(msg: PingMessage):
        logger.info("[DDD] Handling 'ping' message")
        return {"response_to": "ping", "msg": "Hello from QCrBox!"}
