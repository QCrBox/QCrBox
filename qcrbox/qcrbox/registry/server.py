import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api import router
from .database import create_db_and_tables, seed_database

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
    logger.debug(f"Established connection to RabbitMQ.")
    logger.debug(f"Setting up QCrBox registry database.")
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
