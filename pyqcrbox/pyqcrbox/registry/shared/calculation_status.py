import json
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from pyqcrbox import logger
from pyqcrbox.svcs import get_nats_key_value

if TYPE_CHECKING:
    pass


__all__ = ["CalculationStatusEnum", "update_calculation_status_in_nats_kv_NEW"]


class CalculationStatusEnum(StrEnum):
    SUBMITTED = "submitted"
    # CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # UNKNOWN = "unknown"


class CalculationStatusDetails(BaseModel):
    calculation_id: str
    status: CalculationStatusEnum
    stdout: str | None
    stderr: str | None
    extra_info: dict


# async def update_calculation_status_in_nats_kv(
#     calculation_id: str,
#     status: CalculationStatusEnum,
#     stdout: str = "",
#     stderr: str = "",
# ):
#     status_details = CalculationStatusDetails(
#         status=status,
#         stdout=stdout,
#         stderr=stderr,
#     )
#     kv = await get_nats_key_value(bucket="calculation_status")
#     await kv.put(calculation_id, json.dumps(status_details.model_dump()).encode())
#     logger.debug(f"Updated status in NATS key-value store to {status!r} ({calculation_id=!r}")


async def update_calculation_status_in_nats_kv_NEW(status_details: CalculationStatusDetails):
    kv = await get_nats_key_value(bucket="calculation_status")
    await kv.put(status_details.calculation_id, json.dumps(status_details.model_dump()).encode())
    logger.debug(f"Updated calculation status details in NATS key-value store: {status_details!r}")
