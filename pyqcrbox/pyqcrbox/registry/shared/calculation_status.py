import json
from typing import TYPE_CHECKING

import nats.js.errors

from pyqcrbox import logger
from pyqcrbox.nats_models.calculation import CalculationNatsDB
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusDetails
from pyqcrbox.svcs import get_nats_key_value

if TYPE_CHECKING:
    pass


__all__ = [
    "update_calculation_status_in_nats_kv_NEW",
    "add_calculation_to_nats_kv",
]


class NatsCalculationAlreadyExists(Exception):
    pass


async def update_calculation_status_in_nats_kv_NEW(status_details: CalculationStatusDetails) -> None:
    key = status_details.calculation_id

    bucket = await get_nats_key_value(bucket="calculation_status")
    try:
        calc_as_bytes = await bucket.get(key)
    except nats.js.errors.KeyNotFoundError:
        logger.error(f"Can't find calculation {key!r} to update calculation status")
        raise

    calculation = CalculationNatsDB.model_validate_json(calc_as_bytes.decode())
    calculation.status_events.append(status_details)

    await bucket.put(
        key,
        json.dumps(calculation.model_dump(mode="json")).encode(),
    )
    logger.debug(
        f"Updated calculation status details in NATS key-value store for calculation {status_details.calculation_id!r}"
    )


async def add_calculation_to_nats_kv(calculation: CalculationNatsDB) -> None:
    """Add a new calculation to the NATS data manager.

    Parameters
    ----------
    calculation : CalculationNats
        An object containing metadata about the new calculation.

    Raises
    ------
    KeyError
        Raised when trying to add a new calculation to an already populated
        calculation id.

    """
    logger.debug(f"Adding calculation id={calculation.calculation_id!r} to NATS: calculation=f{calculation!r}")
    key = calculation.calculation_id

    bucket = await get_nats_key_value(bucket="calculations")
    # try:
    #     bucket_keys = await bucket.keys()
    # except nats.js.errors.NoKeysError:
    #     bucket_keys = []
    # if key in bucket_keys:
    #     raise KeyError(f"Calculation {key!r} already in NATS, can't create new calculation")
    await bucket.put(
        key,
        json.dumps(calculation.model_dump()).encode(),
    )
