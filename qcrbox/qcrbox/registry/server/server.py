import json

import pydantic
import uvicorn
from fastapi import FastAPI
from loguru import logger

from qcrbox.common import msg_specs
from .database import create_db_and_tables, seed_database
from .messaging import process_message_sync_or_async
from .api import fastapi_app, router


@router.after_startup
async def init_db(_: FastAPI):
    logger.debug(f"Established connection to RabbitMQ.")
    logger.debug(f"Setting up QCrBox registry database.")
    create_db_and_tables()
    seed_database()


@router.after_startup
async def report_successful_startup(_: FastAPI):
    logger.info("QCrBox registry startup was successful.")


def action_does_not_match(exc: pydantic.ValidationError):
    def is_action_mismatch_error(err_dict):
        return err_dict["loc"] == ("action",) and err_dict["type"] == "value_error.const"

    assert isinstance(exc, pydantic.ValidationError)
    return [] != [err_dict for err_dict in exc.errors() if is_action_mismatch_error(err_dict)]


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
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

    if "action" not in msg_dict:
        error_msg = f"Invalid message structure: message must have an 'action' field"
        logger.error(error_msg)
        return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

    # Try matching the given message against all valid action classes.
    # If a match is found, dispatch the message for processing; otherwise
    # return a response with an informative error message.
    for cls in msg_specs.VALID_QCRBOX_ACTIONS:
        try:
            msg_obj = cls(**msg_dict)
            break
        except pydantic.ValidationError as exc:
            if action_does_not_match(exc):
                # this action does not match; try the next one instead
                continue
            else:
                logger.error(f"Invalid message structure for action {msg_dict['action']!r}. Errors: {exc.errors()}")
                raise
    else:
        error_msg = f"Invalid action: {msg_dict['action']!r}"
        logger.error(error_msg)
        return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

    # Process the message - it will be passed to the correct processing function based on
    # its type/structure (the heavy lifting is done by `functools.singledispatch`).
    return await process_message_sync_or_async(msg_obj)


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
