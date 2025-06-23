from robot.api.deco import keyword


@keyword
def should_be_none(value, name="Value"):
    if value is not None:
        raise AssertionError(f"{name} should not be None")


@keyword
def should_not_be_none(value, name="Value"):
    if value is None:
        raise AssertionError(f"{name} should not be None")


@keyword
def check_json_has_attributes(json, *attributes):
    missing = [attribute for attribute in attributes if attribute not in json]
    if missing:
        raise AssertionError(f"JSON is missing attributes: {missing}")
