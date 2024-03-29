# SPDX-License-Identifier: MPL-2.0

from loguru import logger

from qcrbox.common import msg_specs, sql_models

from .base import process_message

__all__ = []


@process_message.register
async def _(msg: msg_specs.GetCalculationStatusDetails, application) -> msg_specs.QCrBoxGenericResponse:
    """
    Retrieve status details for a given calculation.
    """
    logger.debug(f"Retrieving status details for calculation_id={msg.payload.calculation_id}")
    try:
        calculation = application._calculations[msg.payload.calculation_id]
    except KeyError:
        error_msg = f"No calculation found for calculation_id={msg.payload.calculation_id}"
        logger.error(error_msg)
        return msg_specs.QCrBoxGenericResponse(
            response_to="get_calculation_status_details", status="error", msg=error_msg
        )

    status_details = sql_models.QCrBoxCalculationStatusDetails(
        status=calculation.status.value,
        details=await calculation.status_details,
    ).dict()

    return msg_specs.QCrBoxGenericResponse(
        response_to="get_calculation_status_details",
        status="success",
        payload=status_details,
    )
