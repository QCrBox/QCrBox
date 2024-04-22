from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

from pyqcrbox.settings import settings

__all__ = ["create_client_rabbitmq_broker"]


class HealthcheckMessage(BaseModel):
    action: str = Literal["healthcheck"]
    payload: dict = dict()


def create_client_rabbitmq_broker(private_routing_key: str) -> RabbitBroker:
    broker = RabbitBroker(settings.rabbitmq.url, graceful_timeout=10)

    @broker.subscriber(private_routing_key)
    async def ping_handler(msg: HealthcheckMessage):
        logger.info("[DDD] Handling 'healthcheck' message")
        return {"response_to": "healthcheck", "status": "healthy"}

    return broker
