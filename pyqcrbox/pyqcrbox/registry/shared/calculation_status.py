from typing import TYPE_CHECKING

import nats.js.errors
from faststream.nats import NatsBroker

from pyqcrbox import logger
from pyqcrbox.sql_models.calculation import CalculationNatsDB
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusDetails

if TYPE_CHECKING:
    pass


__all__ = [
    "update_calculation_status_in_nats_kv",
    "add_calculation_to_nats_kv",
]


class NatsCalculationAlreadyExists(Exception):
    pass


async def update_calculation_status_in_nats_kv(
    nats_broker: NatsBroker, status_details: CalculationStatusDetails
) -> None:
    """Append a new status to the the calculation status events for a calculation.

    Parameters
    ----------
    status_details : CalculationStatusDetails
        The calculation status details to append to the calculation.

    """
    key = status_details.calculation_id
    bucket = await nats_broker.key_value(bucket="calculations")
    try:
        calc_entry = await bucket.get(key)
        calc_as_bytes = calc_entry.value
    except nats.js.errors.KeyNotFoundError:
        logger.error(f"Can't find calculation {key!r} to update calculation status")
        raise
    if not calc_as_bytes:
        logger.error(f"calculation {key} has an empty entry in calculations database")
        raise nats.js.errors.KeyNotFoundError(f"{key} returned an empty calculation")

    calculation = CalculationNatsDB.model_validate_json(calc_as_bytes.decode())
    calculation.status_events.append(status_details)
    logger.debug(
        f"Appending status {status_details!r} to calculation {calculation!r}",
    )
    await bucket.put(
        key,
        calculation.model_dump_json(exclude={"status", "output_dataset_id"}).encode(),
    )


async def add_calculation_to_nats_kv(nats_broker: NatsBroker, calculation: CalculationNatsDB) -> None:
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
    logger.debug(
        f"Adding calculation id={calculation.calculation_id!r} to NATS: {calculation!r}",
    )
    key = calculation.calculation_id

    bucket = await nats_broker.key_value(bucket="calculations")
    try:
        bucket_keys = await bucket.keys()
    except nats.js.errors.NoKeysError:
        bucket_keys = []
    if key in bucket_keys:
        raise KeyError(f"Calculation {key!r} already in NATS, can't create new calculation")
    await bucket.put(
        key,
        calculation.model_dump_json(exclude={"status", "output_dataset_id"}).encode(),  # type: ignore
    )
