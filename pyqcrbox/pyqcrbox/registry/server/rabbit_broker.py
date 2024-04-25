from typing import Literal

from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic import BaseModel

__all__ = ["set_up_server_rabbitmq_broker"]

from pyqcrbox import msg_specs, settings


class PingMessage(BaseModel):
    action: str = Literal["ping"]
    payload: dict = dict()


def set_up_server_rabbitmq_broker(broker: RabbitBroker) -> None:
    @broker.subscriber(settings.rabbitmq.routing_key_qcrbox_registry)
    def process_incoming_messages(msg_json: dict):
        match msg_json["action"]:
            case "ping":
                return ping_handler(msg_json)
            case "register_application":
                msg = msg_specs.RegisterApplication(**msg_json)
                return handle_application_registration_request(msg)
            case _:
                return

    def ping_handler(msg: msg_specs.QCrBoxBaseAction):
        assert msg.action == "ping"
        logger.info("[DDD] Handling 'ping' message")
        return msg_specs.responses.success(response_to=msg.action)

    def handle_application_registration_request(msg: msg_specs.RegisterApplication):
        assert msg.action == "register_application"
        response_msg = msg_specs.responses.success(response_to=msg.action)
        # broker.publish(response_msg, msg.payload.private_routing_key)
        return response_msg
