from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

__all__ = ["set_up_client_rabbitmq_broker"]

from pyqcrbox import msg_specs


class HealthcheckMessage(BaseModel):
    action: str = Literal["healthcheck"]
    payload: dict = dict()


def set_up_client_rabbitmq_broker(broker: RabbitBroker, private_routing_key: str) -> None:
    logger.debug(f"Setting up RabbitMQ handlers for QCrBox client ({private_routing_key=})")

    @broker.subscriber(private_routing_key)
    async def process_incoming_messages(msg_json: dict):
        if "action" in msg_json:
            action = msg_json["action"]
            match action:
                case "healthcheck":
                    logger.info("[DDD] Handling 'healthcheck' message")
                    return {"response_to": "healthcheck", "status": "healthy"}
                case _:
                    return msg_specs.responses.error(response_to=action)
        elif "response_to" in msg_json:
            logger.debug(f"Received response message: {msg_json}")
        else:
            raise TypeError(f"Unsupported message type: {msg_json}")

    # async def ping_handler(msg: HealthcheckMessage):
    #     logger.info("[DDD] Handling 'healthcheck' message")
