from ..helpers import RabbitRouterWithConnectionRetries
from ...common import get_rabbitmq_connection_url

rabbitmq_url = get_rabbitmq_connection_url()
router = RabbitRouterWithConnectionRetries(rabbitmq_url)
