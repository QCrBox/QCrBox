from abc import ABC
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Field, Tag, TypeAdapter


def data_to_minmax(data: dict) -> tuple[float, float]:
    """
    Convert YAML data to min/max values for 'within' tests.

    Supports two formats:
    1. expected_value + allowed_deviation
    2. min_value + max_value
    """
    combination1 = ("expected_value", "allowed_deviation")
    combination2 = ("min_value", "max_value")

    has1 = all(key in data for key in combination1)
    has2 = all(key in data for key in combination2)

    if not (has1 or has2):
        raise ValueError("Within test requires either (expected_value + allowed_deviation) or (min_value + max_value)")

    if has1:
        expected = data["expected_value"]
        deviation = data["allowed_deviation"]
        min_val = expected - deviation
        max_val = expected + deviation
    else:
        min_val = data["min_value"]
        max_val = data["max_value"]
        if min_val > max_val:
            raise ValueError("min_value cannot be greater than max_value")

    return min_val, max_val


# ============================================================================
# Base Classes
# ============================================================================


class BaseExpectedResult(BaseModel, ABC):
    """
    Abstract base class for all expected result types.

    This serves as the foundation for all test assertions, providing:
    - Common structure for result_type discrimination
    - Factory method interface for YAML parsing
    - Type safety via Pydantic models
    """

    pass


# ============================================================================
# Status Test
# ============================================================================


class StatusExpectedResult(BaseExpectedResult):
    """
    Tests the execution status of a command.

    YAML example:
        result_type: status
        expected: successful

    Validates that the command completed with the expected status
    (successful, failed, or warning).
    """

    result_type: Literal["status"] = "status"
    expected: Literal["successful", "failed", "warning"]


# ============================================================================
# CIF Entry (Non-Loop) Tests
# ============================================================================


class BaseCifEntryExpectedResult(BaseExpectedResult, ABC):
    """
    Base class for all CIF entry tests (non-loop values).

    All subclasses share:
    - cif_entry_name: The CIF entry to test (e.g., "_cif.entry1")
    - result_type: Always 'cif_value' for entry tests
    """

    result_type: Literal["cif_value"] = "cif_value"
    cif_entry_name: str = Field(..., min_length=1)


class CifEntryMatchExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a CIF entry exactly matches an expected value.

    YAML example:
        result_type: cif_value
        test_type: match
        cif_entry_name: "_cif_entry1"
        expected_value: 'C'

    Supports string, int, float, or bool values.
    """

    test_type: Literal["match"] = "match"
    expected_value: str | int | float | bool


class CifEntryNonMatchExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a CIF entry does NOT match a forbidden value.

    YAML example:
        result_type: cif_value
        test_type: non-match
        cif_entry_name: "_cif_entry1"
        forbidden_value: 'D'

    This is a negative assertion - the test passes if the value is anything
    except the forbidden value.
    """

    test_type: Literal["non-match"] = "non-match"
    forbidden_value: str | int | float | bool


class CifEntryWithinExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a numerical CIF entry falls within an acceptable range.

    Two YAML formats supported:

    Format 1 - Deviation from expected value:
        result_type: cif_value
        test_type: within
        cif_entry_name: "_cif_entry2"
        expected_value: 1.234
        allowed_deviation: 0.001
        # Accepts values in [1.233, 1.235]

    Format 2 - Explicit min/max:
        result_type: cif_value
        test_type: within
        cif_entry_name: "_another_entry"
        max_value: 6.0
        min_value: 5.0
        # Accepts values in [5.0, 6.0]

    Internally, both formats are normalized to min_value/max_value for testing.
    """

    test_type: Literal["within"] = "within"

    # Internal representation (after parsing)
    min_value: float
    max_value: float

    def __init__(self, **data):
        deterministic_entries = ("expected_value", "allowed_deviation", "min_value", "max_value")
        cls_data = {key: val for key, val in data.items() if key not in deterministic_entries}

        cls_data["min_value"], cls_data["max_value"] = data_to_minmax(data)
        super().__init__(**cls_data)


class CifEntryContainExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a CIF entry (string) contains a specific substring.

    YAML example:
        result_type: cif_value
        test_type: contain
        cif_entry_name: "_cif.string_entry"
        expected_value: "check_me"

    Case-sensitive substring search. The entry value must contain the
    expected_value as a substring.
    """

    test_type: Literal["contain"] = "contain"
    expected_value: str


class CifEntryMissingExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a CIF entry does NOT exist in the output.

    YAML example:
        result_type: cif_value
        test_type: missing
        cif_entry_name: "_non_existent_entry"

    Test passes if the entry is completely absent from the CIF file.
    """

    test_type: Literal["missing"] = "missing"


class CifEntryPresentExpectedResult(BaseCifEntryExpectedResult):
    """
    Tests that a CIF entry exists in the output.

    YAML examples:
        # Must exist with a defined value
        result_type: cif_value
        test_type: present
        cif_entry_name: "_another_entry"
        allow_unknown: false

        # Can exist with undefined value (? or .)
        result_type: cif_value
        test_type: present
        cif_entry_name: "_cif.value_is_undefined"
        allow_unknown: true

    The allow_unknown flag controls whether CIF's special undefined values
    ('?' for unknown) are acceptable.
    """

    test_type: Literal["present"] = "present"
    allow_unknown: bool = False


# ============================================================================
# CIF Loop Entry Tests
# ============================================================================


class RowLookup(BaseModel):
    """
    Single row lookup criterion for CIF loop entries.

    Used to identify specific rows in a CIF loop by matching column values.
    Multiple RowLookup entries act as AND conditions.

    Example:
        RowLookup(row_entry_name="_loop_entry.index", row_entry_value=2)
        matches rows where _loop_entry.index == 2
    """

    row_entry_name: str = Field(..., min_length=1)
    row_entry_value: str | int | float | bool


class BaseCifLoopEntryExpectedResult(BaseExpectedResult, ABC):
    """
    Base class for all CIF loop entry tests.

    Loop tests require identifying a specific row before testing a value.
    All subclasses share:
    - result_type: Always 'cif_loop_value'
    - row_lookup: List of conditions to identify the target row (AND logic)
    - cif_entry_name: The loop column to test in the matched row

    Example loop structure with single lookup:
        loop_
        _loop_entry.index    <- row_lookup condition
        _loop_entry.value    <- cif_entry_name (what we test)
        1                    <- matches row_entry_value=1
        12                   <- the value we're testing
        2                    <- different row
        13                   <- different value

    Example with multi-row lookup:
        loop_
        _loop_entry.index           <- first lookup condition
        _loop_entry.index_additional <- second lookup condition
        _loop_entry.value           <- cif_entry_name (what we test)
        2  6  18                    <- matches index=2 AND index_additional=6
        2  7  13                    <- different row (index_additional doesn't match)
    """

    result_type: Literal["cif_loop_value"] = "cif_loop_value"
    row_lookup: list[RowLookup] = Field(..., min_length=1)
    cif_entry_name: str = Field(..., min_length=1)


class CifLoopEntryMatchExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a specific loop entry exactly matches an expected value.

    YAML example (single lookup):
        result_type: cif_loop_value
        test_type: match
        cif_entry_name: "_loop_entry.value"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 1
        expected_value: 12

    YAML example (multi-lookup):
        result_type: cif_loop_value
        test_type: match
        cif_entry_name: "_loop_entry.value"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 2
          - row_entry_name: "_loop_entry.index_additional"
            row_entry_value: 6
        expected_value: 18

    First finds the row where ALL lookup conditions match,
    then checks if cif_entry_name has the expected value in that row.
    """

    test_type: Literal["match"] = "match"
    expected_value: str | int | float | bool


class CifLoopEntryNonMatchExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a specific loop entry does NOT match a forbidden value.

    YAML example:
        result_type: cif_loop_value
        test_type: non-match
        cif_entry_name: "_loop_entry.value"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 1
        forbidden_value: 13

    Negative assertion for loop values. First finds row matching all lookup
    conditions, then verifies the value is NOT the forbidden value.
    """

    test_type: Literal["non-match"] = "non-match"
    forbidden_value: str | int | float | bool


class CifLoopEntryWithinExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a numerical loop entry falls within an acceptable range.

    Two YAML formats supported:

    Format 1 - Deviation:
        result_type: cif_loop_value
        test_type: within
        cif_entry_name: "_loop_entry.index"
        row_lookup:
          - row_entry_name: "_loop_entry.value"
            row_entry_value: 2
        expected_value: 12
        allowed_deviation: 0.001

    Format 2 - Min/Max:
        result_type: cif_loop_value
        test_type: within
        cif_entry_name: "_loop_entry.index"
        row_lookup:
          - row_entry_name: "_loop_entry.value"
            row_entry_value: 1
        max_value: 15
        min_value: 10

    Supports multi-row lookup conditions as well.
    """

    test_type: Literal["within"] = "within"

    # Internal representation
    min_value: float
    max_value: float

    def __init__(self, **data):
        deterministic_entries = ("expected_value", "allowed_deviation", "min_value", "max_value")
        cls_data = {key: val for key, val in data.items() if key not in deterministic_entries}

        cls_data["min_value"], cls_data["max_value"] = data_to_minmax(data)
        super().__init__(**cls_data)


class CifLoopEntryContainExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a loop entry (string) contains a specific substring.

    YAML example:
        result_type: cif_loop_value
        test_type: contain
        cif_entry_name: "_loop_entry.present_entry"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 2
        expected_value: "another"

    Case-sensitive substring matching in loop values.
    """

    test_type: Literal["contain"] = "contain"
    expected_value: str


class CifLoopEntryMissingExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a specific loop column does NOT exist.

    YAML example:
        result_type: cif_loop_value
        test_type: missing
        cif_entry_name: "_loop_entry.non_existent"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 1

    Note: This tests if the column exists in the loop structure,
    not if a specific row exists. The row_lookup is still used to
    identify which loop to check (in case multiple loops exist).
    """

    test_type: Literal["missing"] = "missing"


class CifLoopEntryPresentExpectedResult(BaseCifLoopEntryExpectedResult):
    """
    Tests that a loop entry exists in a specific row.

    YAML examples:
        # Must exist with defined value
        result_type: cif_loop_value
        test_type: present
        cif_entry_name: "_loop_entry.potentially_undefined"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 1
        allow_unknown: false

        # Can be undefined (?)
        result_type: cif_loop_value
        test_type: present
        cif_entry_name: "_loop_entry.potentially_undefined"
        row_lookup:
          - row_entry_name: "_loop_entry.index"
            row_entry_value: 1
        allow_unknown: true

    The allow_unknown flag handles CIF's ? markers.
    """

    test_type: Literal["present"] = "present"
    allow_unknown: bool = False


# ============================================================================
# Type Unions and Factory
# ============================================================================

# Union type for all CIF entry tests (discriminated by test_type)
CifEntryExpectedResultType = Annotated[
    Annotated[CifEntryMatchExpectedResult, Tag("match")]
    | Annotated[CifEntryNonMatchExpectedResult, Tag("non-match")]
    | Annotated[CifEntryWithinExpectedResult, Tag("within")]
    | Annotated[CifEntryContainExpectedResult, Tag("contain")]
    | Annotated[CifEntryMissingExpectedResult, Tag("missing")]
    | Annotated[CifEntryPresentExpectedResult, Tag("present")],
    Discriminator("test_type"),
]

# Union type for all CIF loop entry tests (discriminated by test_type)
CifLoopEntryExpectedResultType = Annotated[
    Annotated[CifLoopEntryMatchExpectedResult, Tag("match")]
    | Annotated[CifLoopEntryNonMatchExpectedResult, Tag("non-match")]
    | Annotated[CifLoopEntryWithinExpectedResult, Tag("within")]
    | Annotated[CifLoopEntryContainExpectedResult, Tag("contain")]
    | Annotated[CifLoopEntryMissingExpectedResult, Tag("missing")]
    | Annotated[CifLoopEntryPresentExpectedResult, Tag("present")],
    Discriminator("test_type"),
]

# Union type for ALL expected result types (discriminated by result_type)
ExpectedResultType = Annotated[
    Annotated[StatusExpectedResult, Tag("status")]
    | Annotated[CifEntryExpectedResultType, Tag("cif_value")]
    | Annotated[CifLoopEntryExpectedResultType, Tag("cif_loop_value")],
    Discriminator("result_type"),
]

ExpectedResultTypeAdapter = TypeAdapter(ExpectedResultType)
