import contextlib
import uvicorn
from aiormq.exceptions import AMQPConnectionError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from propan.fastapi import RabbitRouter
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type

from ..cli.helpers.qcrbox_helpers import get_rabbitmq_connection_url
from .database import create_db_and_tables, seed_database


def wrap_with_retry(orig_connect_func, *, wait_interval, max_attempt_number):
    @retry(
        reraise=True,
        wait=wait_fixed(wait_interval),
        stop=stop_after_attempt(max_attempt_number),
        retry=retry_if_exception_type(AMQPConnectionError),
    )
    async def connect_with_retries(*args, **kwargs):
        logger.debug("Attempting to establish connection to RabbitMQ.")
        await orig_connect_func(*args, **kwargs)

    return connect_with_retries


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
fastapi_app = FastAPI(lifespan=router.lifespan_context, logger=logger)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@router.after_startup
async def init_db(_: FastAPI):
    create_db_and_tables()
    seed_database()


@router.after_startup
async def report_successful_startup(_: FastAPI):
    logger.info("QCrBox registry startup was successful.")


def main():
    logger.info("Starting QCrBox registry server")
    try:
        uvicorn.run("qcrbox.registry.server:fastapi_app", host="0.0.0.0", port=8000, reload=True)
    except Exception as exc:
        logger.info(f"[DDD] {exc=}")
        raise


# Note: the call to `include_router()` must happen *after* the various handlers
# have been defined, so it's best to keep this at the end of the file.
fastapi_app.include_router(router)


if __name__ == "__main__":
    main()
