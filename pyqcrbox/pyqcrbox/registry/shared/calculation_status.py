from enum import StrEnum

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


async def update_calculation_status_in_nats_kv(calculation_id: str, status: str):
    kv = await get_nats_key_value(bucket="calculation_status")
    await kv.put(calculation_id, status.encode())
    return f"Successfully updated status in NATS key-value store to {status!r}"
