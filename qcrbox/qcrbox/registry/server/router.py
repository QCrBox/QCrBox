from ...common import get_rabbitmq_connection_url
from ..helpers import RabbitRouterWithConnectionRetries

rabbitmq_url = get_rabbitmq_connection_url()
router = RabbitRouterWithConnectionRetries(rabbitmq_url)
