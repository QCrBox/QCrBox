from loguru import logger

from qcrbox.common import msg_specs
from .base import process_message

__all__ = []


@process_message.register
async def _(msg: msg_specs.GetContainerStatus, application) -> msg_specs.GetContainerStatusResponse:
    """
    Return status of the current container.
    """
    logger.debug(f"Received message: {msg}")

    return msg_specs.GetContainerStatusResponse(
        response_to="get_container_status",
        status="success",
        msg="TODO: differentiate between 'idle' and 'executing_command' (or similar)",
        payload=msg_specs.GetContainerStatusResponsePayload(
            container_status="idle",
            container_id=msg.payload.container_id,
        ),
    )
