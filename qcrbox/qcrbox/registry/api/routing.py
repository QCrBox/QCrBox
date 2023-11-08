from fastapi import Request
from propan.fastapi import RabbitRouter
from sqlalchemy import select
from sqlmodel import Session

from ..database import sql_models, engine
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


@router.get("/applications/", response_model=list[sql_models.QCrBoxApplicationRead])
def get_registered_applications():
    with Session(engine) as session:
        applications = session.scalars(select(sql_models.QCrBoxApplicationDB)).all()
        return applications


@router.get("/commands/", response_model=list[sql_models.QCrBoxCommandRead])
def get_registered_commands():
    with Session(engine) as session:
        commands = session.exec(select(sql_models.QCrBoxCommandDB)).all()
        return commands
