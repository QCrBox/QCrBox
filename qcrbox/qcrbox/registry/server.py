import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from propan.fastapi import RabbitRouter

from ..cli.helpers.qcrbox_helpers import get_rabbitmq_connection_url
from .database import create_db_and_tables, seed_database

rabbitmq_url = get_rabbitmq_connection_url()
router = RabbitRouter(rabbitmq_url)
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


def main():
    logger.info("Starting QCrBox registry server")
    try:
        uvicorn.run("qcrbox.registry.server:fastapi_app", host="0.0.0.0", port=8000, reload=True)
    except Exception as exc:
        logger.info("Line 3")
        logger.info(f"{exc=}")
        logger.info("Line 4")
        raise


# Note: the call to `include_router()` must happen *after* the various handlers
# have been defined, so it's best to keep this at the end of the file.
fastapi_app.include_router(router)


if __name__ == "__main__":
    main()
