from typing import Any

from robot.api.deco import keyword


@keyword
def should_be_none(value: Any, name: str = "Value") -> None:
    """Check if `value` is None.

    Parameters
    ----------
    value
        The value to check.
    name
        The name of the value.

    """
    if value is not None:
        raise AssertionError(f"{name} should not be None")


@keyword
def should_not_be_none(value: Any, name: str = "Value"):
    """Check if `value` is not None.

    Parameters
    ----------
    value
        The value to check.
    name
        The name of the value.

    """
    if value is None:
        raise AssertionError(f"{name} should not be None")


@keyword
def check_json_has_attributes(json: dict, *attributes) -> None:
    """Check if the provided JSON has a list of keys/attributes.

    Parameters
    ----------
    json
        The json to check.
    *attributes
        The list of keys to check for.

    """
    missing = [attribute for attribute in attributes if attribute not in json]
    if missing:
        raise AssertionError(f"JSON is missing attributes: {missing}")
