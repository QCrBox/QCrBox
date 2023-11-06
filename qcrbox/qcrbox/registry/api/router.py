from fastapi import Request
from propan.fastapi import RabbitRouter

from .helpers import get_rabbitmq_connection_url, wrap_with_retry

__all__ = ["router"]


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

@router.get("/")
async def hello_http(request: Request):
    return "Hello from QCrBox!"


@router.get("/ping")
async def hello_http(request: Request):
    return {"status": "success", "message": "pong"}
