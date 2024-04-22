from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

__all__ = ["set_up_client_rabbitmq_broker"]


class HealthcheckMessage(BaseModel):
    action: str = Literal["healthcheck"]
    payload: dict = dict()


def set_up_client_rabbitmq_broker(broker: RabbitBroker, private_routing_key: str) -> RabbitBroker:
    @broker.subscriber(private_routing_key)
    async def ping_handler(msg: HealthcheckMessage):
        logger.info("[DDD] Handling 'healthcheck' message")
        return {"response_to": "healthcheck", "status": "healthy"}

    return broker
