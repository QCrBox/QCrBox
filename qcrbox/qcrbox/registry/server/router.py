from ..helpers import get_rabbitmq_connection_url, RabbitRouterWithConnectionRetries

rabbitmq_url = get_rabbitmq_connection_url()
router = RabbitRouterWithConnectionRetries(rabbitmq_url)
