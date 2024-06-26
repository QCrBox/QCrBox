from enum import StrEnum

from anyio.from_thread import start_blocking_portal

from pyqcrbox import logger
from pyqcrbox.svcs import get_nats_key_value

__all__ = ["CalculationStatus", "update_calculation_status"]


class CalculationStatus(StrEnum):
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


async def _update_status_in_nats_kv(calculation_id: str, status: str):
    kv = await get_nats_key_value(bucket="calculation_status")
    await kv.put(calculation_id, status.encode())
    return f"Successfully updated status in NATS key-value store to {status!r}"


def update_calculation_status(calculation_id: str, status: CalculationStatus):
    with start_blocking_portal() as portal:
        logger.debug(f"[DDD] started blocking portal: {portal=}")
        future = portal.start_task_soon(_update_status_in_nats_kv, calculation_id, status)
        logger.debug("[DDD] Waiting for task to complete...")
        result = future.result()
        logger.debug(f"[DDD] Task finished with result: {result!r}")
