from datetime import datetime

from ... import msg_specs
from ....logging import logger
from .msg_processing import process_message

__all__ = []

@process_message.register
async def _(msg: msg_specs.ExecuteCalculation, application) -> msg_specs.QCrBoxGenericResponse:
    """
    Invoke a registered command with given arguments.
    """
    logger.debug(f"About to invoke command with arguments: {msg.payload.arguments}")
    cmd = application._command_callbacks[msg.payload.command_id]
    try:
        calculation = await cmd.execute_in_background(**msg.payload.arguments)
    except TypeError as exc:
        # TODO: raise and catch a qubox-specific exception here rather than a generic TypeError
        error_msg = f"Supplied arguments do not match the command signature (original error: {exc})"
        logger.error(error_msg)
        return msg_specs.QCrBoxGenericResponse(
            response_to="invoke_command",
            status="error",
            msg=error_msg,
        )

    application._calculations[msg.payload.calculation_id] = calculation
    logger.debug(f"Started calculation: {calculation}")
    return msg_specs.QCrBoxGenericResponse(
        response_to="invoke_command",
        status="success",
        msg="Started new calculation",
        payload={
            "cmd_id": msg.payload.command_id,
            "calculation_id": msg.payload.calculation_id,
            "started_at": datetime.now(),
        },
    )
