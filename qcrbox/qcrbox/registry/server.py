import json

import pydantic
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .api import router
from .database import create_db_and_tables, seed_database
from .messaging import msg_specs, process_message

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


@router.broker.handle("qcrbox_registry")
async def handle_incoming_messages(msg_dict) -> msg_specs.QCrBoxGenericResponse:
    logger.info(f"Received message: {msg_dict} (type: {type(msg_dict).__name__})")
    if isinstance(msg_dict, (str, bytes)):
        try:
            msg_dict = json.loads(msg_dict)
        except Exception as exc:
            error_msg = (
                f"Incoming message does not represent a valid JSON structure: {msg_dict}.\n"
                f"The original error was: {exc}"
            )
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(
                response_to="incoming_message", status="error", msg=error_msg)

    for cls in msg_specs.VALID_QCRBOX_ACTIONS:
        try:
            msg_obj = cls(**msg_dict)
            break
        except pydantic.ValidationError as exc:
            pass
    else:
        if "action" not in msg_dict:
            # raise ValueError(f"Invalid message structure: message must have an 'action' key")
            error_msg = f"Invalid message structure: message must have an 'action' key"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)
        else:
            # TODO: This doesn't currently distinguish between the following cases:
            #         - 'action' key is invalid
            #         - 'action' key is valid but the remaining arguments don't match the expected structure
            #       In order to catch the second case, we need to inspect the `pydantic.ValidationError` above.
            error_msg = f"Invalid action: {msg_dict['action']!r}"
            # raise ValueError(f"Invalid action: {msg_dict['action']!r}")
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

    # Process the message - it will be passed to the correct processing function based on
    # its type/structure (the heavy lifting is done by `functools.singledispatch`).
    return process_message(msg_obj)


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
