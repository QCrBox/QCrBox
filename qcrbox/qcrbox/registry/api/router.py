from propan.fastapi import RabbitRouter

from .helpers import wrap_with_retry, get_rabbitmq_connection_url


class RabbitRouterWithConnectionRetries(RabbitRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broker.connect = wrap_with_retry(
            self.broker.connect,
            wait_interval=3,
            max_attempt_number=50,
        )


rabbitmq_url = get_rabbitmq_connection_url()
router = RabbitRouterWithConnectionRetries(rabbitmq_url)
