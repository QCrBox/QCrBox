from enum import StrEnum

from anyio.from_thread import start_blocking_portal

from pyqcrbox import logger
from pyqcrbox.svcs import get_nats_key_value

__all__ = ["CalculationStatusEnum", "update_calculation_status_in_nats_kv"]


class CalculationStatusEnum(StrEnum):
    SUBMITTED = "submitted"
    # CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # UNKNOWN = "unknown"


async def _update_status_in_nats_kv(calculation_id: str, status: str):
    kv = await get_nats_key_value(bucket="calculation_status")
    await kv.put(calculation_id, status.encode())
    return f"Successfully updated status in NATS key-value store to {status!r}"


def update_calculation_status_in_nats_kv(calculation_id: str, status: CalculationStatusEnum):
    with start_blocking_portal() as portal:
        logger.debug("Updating calculation status in NATS KV...")
        future = portal.start_task_soon(_update_status_in_nats_kv, calculation_id, status)
        _ = future.result()
        logger.debug("Done (calculation status updated in NATS KV).")
