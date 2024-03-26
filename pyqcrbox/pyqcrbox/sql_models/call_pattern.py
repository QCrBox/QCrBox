import re
from typing import Annotated

from pydantic import AfterValidator

__all__ = ["CallPattern"]


def remove_linebreaks(value: str) -> str:
    return re.sub(r"\\?\n", " ", value)


def condense_whitespace(value: str) -> str:
    return re.sub("\s+", " ", value)


def normalise_call_pattern(value: str) -> str:
    value = remove_linebreaks(value)
    value = condense_whitespace(value)
    return value.strip()


class CallPatternString(str):
    def __new__(cls, value):
        return super().__new__(cls, normalise_call_pattern(value))

    @property
    def param_names(self):
        param_pattern = re.compile("{(.*?)}")
        return param_pattern.findall(self)


CallPattern = Annotated[
    str,
    AfterValidator(CallPatternString),
]
