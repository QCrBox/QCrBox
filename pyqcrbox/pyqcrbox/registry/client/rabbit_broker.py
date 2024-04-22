from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

from pyqcrbox.settings import settings

__all__ = ["create_server_rabbitmq_broker"]


class HealthcheckMessage(BaseModel):
    action: str = Literal["healthcheck"]
    payload: dict = dict()


def create_server_rabbitmq_broker() -> RabbitBroker:
    broker = RabbitBroker(settings.rabbitmq.url, graceful_timeout=10)

    @broker.subscriber("qcrbox-registry")
    async def ping_handler(msg: HealthcheckMessage):
        logger.info("[DDD] Handling 'healthcheck' message")
        return {"response_to": "healthcheck", "status": "healthy"}

    return broker
