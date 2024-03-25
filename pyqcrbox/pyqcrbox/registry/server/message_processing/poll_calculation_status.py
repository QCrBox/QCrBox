# SPDX-License-Identifier: MPL-2.0
from faststream import Context, Logger, apply_types
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, sql_models
from pyqcrbox.msg_specs import process_message

__all__ = []


@process_message.register
@apply_types
async def _(
    msg: msg_specs.PollCalculationStatus,
    logger: Logger,
    broker: RabbitBroker = Context("broker"),
) -> msg_specs.ReportCalculationStatusDetails:
    """
    Retrieve calculation status details from the client who is executing the calculation.
    """
    client_routing_key = sql_models.CommandExecutionDB.get_client_routing_key(correlation_id=msg.payload.correlation_id)
    logger.debug("Retrieving calculation status from client...")

    calculation_status_details = await broker.publish(
        msg,
        routing_key=client_routing_key,
        rpc=True,
    )

    return calculation_status_details
