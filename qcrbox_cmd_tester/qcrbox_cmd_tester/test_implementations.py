from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .io_adapters import CIFIOAdapter, PyCIFRWAdapter, ValueMissingError
from .models.expected_values import (
    CifEntryContainExpectedResult,
    CifEntryMatchExpectedResult,
    CifEntryMissingExpectedResult,
    CifEntryNonMatchExpectedResult,
    CifEntryPresentExpectedResult,
    CifEntryWithinExpectedResult,
    CifLoopEntryContainExpectedResult,
    CifLoopEntryMatchExpectedResult,
    CifLoopEntryMissingExpectedResult,
    CifLoopEntryNonMatchExpectedResult,
    CifLoopEntryPresentExpectedResult,
    CifLoopEntryWithinExpectedResult,
    ExpectedResultType,
)


@dataclass
class IndividualTestResult:
    test_case_name: str
    passed: bool
    log: str


# ============================================================================
# Helper Functions
# ============================================================================


def generate_test_case_name(test_type: str, entry_name: str | None = None) -> str:
    """
    Generate a consistent test case name.

    This central function ensures naming consistency across all tests
    and provides a single point for future naming convention changes.

    Args:
        test_type: The type of test (e.g., 'match', 'within', 'present')
        entry_name: Optional CIF entry name to include in the test case name

    Returns
    -------
        A formatted test case name string

    Examples
    --------
        >>> generate_test_case_name('match', '_cif.entry1')
        'match__cif.entry1'
        >>> generate_test_case_name('status')
        'status_test'

    """
    if entry_name:
        return f"{test_type}_{entry_name}"
    else:
        return f"{test_type}_test"


# ============================================================================
# Individual Test Functions
# ============================================================================

# Status is not tested here since it does not require CIF parsing


def test_cif_entry_match(adapter: CIFIOAdapter, expected: CifEntryMatchExpectedResult) -> IndividualTestResult:
    """Test that a CIF entry exactly matches an expected value."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)

        # Try numerical comparison first
        try:
            actual_float = float(actual_value)
            expected_float = float(expected.expected_value)
            passed = actual_float == expected_float
        except (ValueError, TypeError):
            # Fall back to string comparison
            actual_str = str(actual_value).strip()
            expected_str = str(expected.expected_value).strip()
            passed = actual_str == expected_str

        if passed:
            log = f"✓ Entry '{expected.cif_entry_name}' matches expected value '{expected.expected_value}'"
        else:
            log = f"✗ Entry '{expected.cif_entry_name}': expected '{expected.expected_value}', got '{actual_value}'"

        return IndividualTestResult(
            test_case_name=generate_test_case_name("match", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except ValueMissingError as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("match", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_entry_non_match(adapter: CIFIOAdapter, expected: CifEntryNonMatchExpectedResult) -> IndividualTestResult:
    """Test that a CIF entry does NOT match a forbidden value."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)

        # Try numerical comparison first
        try:
            actual_float = float(actual_value)
            forbidden_float = float(expected.forbidden_value)
            passed = actual_float != forbidden_float
        except (ValueError, TypeError):
            # Fall back to string comparison
            actual_str = str(actual_value).strip()
            forbidden_str = str(expected.forbidden_value).strip()
            passed = actual_str != forbidden_str

        if passed:
            log = f"✓ Entry '{expected.cif_entry_name}' does not match forbidden value '{expected.forbidden_value}'"
        else:
            log = f"✗ Entry '{expected.cif_entry_name}' has forbidden value '{expected.forbidden_value}'"

        return IndividualTestResult(
            test_case_name=generate_test_case_name("non_match", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except ValueMissingError as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("non_match", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_entry_within(adapter: CIFIOAdapter, expected: CifEntryWithinExpectedResult) -> IndividualTestResult:
    """Test that a numerical CIF entry falls within an acceptable range."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)

        # Convert to float for numerical comparison
        try:
            actual_float = float(actual_value)
        except (ValueError, TypeError):
            return IndividualTestResult(
                test_case_name=generate_test_case_name("within", expected.cif_entry_name),
                passed=False,
                log=f"✗ Entry '{expected.cif_entry_name}' value '{actual_value}' is not a valid number",
            )

        passed = expected.min_value <= actual_float <= expected.max_value

        if passed:
            log = (
                f"✓ Entry '{expected.cif_entry_name}' value {actual_float} "
                f"is within [{expected.min_value}, {expected.max_value}]"
            )
        else:
            log = (
                f"✗ Entry '{expected.cif_entry_name}' value {actual_float} "
                f"is outside [{expected.min_value}, {expected.max_value}]"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("within", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except ValueMissingError as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("within", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_entry_contain(adapter: CIFIOAdapter, expected: CifEntryContainExpectedResult) -> IndividualTestResult:
    """Test that a CIF entry (string) contains a specific substring."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)
        actual_str = str(actual_value)

        passed = expected.expected_value in actual_str

        if passed:
            log = f"✓ Entry '{expected.cif_entry_name}' contains '{expected.expected_value}'"
        else:
            log = (
                f"✗ Entry '{expected.cif_entry_name}' does not contain '{expected.expected_value}' "
                f"(actual: '{actual_str}')"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("contain", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except ValueMissingError as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("contain", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_entry_missing(adapter: CIFIOAdapter, expected: CifEntryMissingExpectedResult) -> IndividualTestResult:
    """Test that a CIF entry does NOT exist in the output."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)
        # If we get here, the entry exists, which means the test failed
        return IndividualTestResult(
            test_case_name=generate_test_case_name("missing", expected.cif_entry_name),
            passed=False,
            log=f"✗ Entry '{expected.cif_entry_name}' should be missing but was found with value '{actual_value}'",
        )
    except ValueMissingError:
        # Entry is missing, which is what we expect
        return IndividualTestResult(
            test_case_name=generate_test_case_name("missing", expected.cif_entry_name),
            passed=True,
            log=f"✓ Entry '{expected.cif_entry_name}' is missing as expected",
        )


def test_cif_entry_present(adapter: CIFIOAdapter, expected: CifEntryPresentExpectedResult) -> IndividualTestResult:
    """Test that a CIF entry exists in the output."""
    try:
        actual_value = adapter.get_entry_from_cif_block(expected.cif_entry_name)
        actual_str = str(actual_value).strip()

        # Check if value is undefined (? or .)
        is_undefined = actual_str in ("?", ".")

        if is_undefined and not expected.allow_unknown:
            return IndividualTestResult(
                test_case_name=generate_test_case_name("present", expected.cif_entry_name),
                passed=False,
                log=(
                    f"✗ Entry '{expected.cif_entry_name}' is present but has undefined value "
                    f"'{actual_str}' (allow_unknown=False)"
                ),
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("present", expected.cif_entry_name),
            passed=True,
            log=f"✓ Entry '{expected.cif_entry_name}' is present with value '{actual_value}'",
        )
    except ValueMissingError as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("present", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_loop_entry_match(adapter: CIFIOAdapter, expected: CifLoopEntryMatchExpectedResult) -> IndividualTestResult:
    """Test that a specific loop entry exactly matches an expected value."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)

        # Try numerical comparison first
        try:
            actual_float = float(actual_value)
            expected_float = float(expected.expected_value)
            passed = actual_float == expected_float
        except (ValueError, TypeError):
            # Fall back to string comparison
            actual_str = str(actual_value).strip()
            expected_str = str(expected.expected_value).strip()
            passed = actual_str == expected_str

        # Build lookup description for log messages
        lookup_desc = " AND ".join(
            f"{lookup.row_entry_name}={lookup.row_entry_value}" for lookup in expected.row_lookup
        )

        if passed:
            log = (
                f"✓ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"matches expected value '{expected.expected_value}'"
            )
        else:
            log = (
                f"✗ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}): "
                f"expected '{expected.expected_value}', got '{actual_value}'"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_match", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except (ValueMissingError, ValueError, IndexError) as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_match", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_loop_entry_non_match(
    adapter: CIFIOAdapter, expected: CifLoopEntryNonMatchExpectedResult
) -> IndividualTestResult:
    """Test that a specific loop entry does NOT match a forbidden value."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)

        # Try numerical comparison first
        try:
            actual_float = float(actual_value)
            forbidden_float = float(expected.forbidden_value)
            passed = actual_float != forbidden_float
        except (ValueError, TypeError):
            # Fall back to string comparison
            actual_str = str(actual_value).strip()
            forbidden_str = str(expected.forbidden_value).strip()
            passed = actual_str != forbidden_str

        # Build lookup description for log messages
        lookup_desc = " AND ".join(
            f"{lookup.row_entry_name}={lookup.row_entry_value}" for lookup in expected.row_lookup
        )

        if passed:
            log = (
                f"✓ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"does not match forbidden value '{expected.forbidden_value}'"
            )
        else:
            log = (
                f"✗ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"has forbidden value '{expected.forbidden_value}'"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_non_match", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except (ValueMissingError, ValueError, IndexError) as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_non_match", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_loop_entry_within(
    adapter: CIFIOAdapter, expected: CifLoopEntryWithinExpectedResult
) -> IndividualTestResult:
    """Test that a numerical loop entry falls within an acceptable range."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)

        # Convert to float for numerical comparison
        try:
            actual_float = float(actual_value)
        except (ValueError, TypeError):
            return IndividualTestResult(
                test_case_name=generate_test_case_name("loop_within", expected.cif_entry_name),
                passed=False,
                log=f"✗ Loop entry '{expected.cif_entry_name}' value '{actual_value}' is not a valid number",
            )

        passed = expected.min_value <= actual_float <= expected.max_value

        # Build lookup description for log messages
        lookup_desc = " AND ".join(
            f"{lookup.row_entry_name}={lookup.row_entry_value}" for lookup in expected.row_lookup
        )

        if passed:
            log = (
                f"✓ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"value {actual_float} is within [{expected.min_value}, {expected.max_value}]"
            )
        else:
            log = (
                f"✗ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"value {actual_float} is outside [{expected.min_value}, {expected.max_value}]"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_within", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except (ValueMissingError, ValueError, IndexError) as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_within", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_loop_entry_contain(
    adapter: CIFIOAdapter, expected: CifLoopEntryContainExpectedResult
) -> IndividualTestResult:
    """Test that a loop entry (string) contains a specific substring."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)
        actual_str = str(actual_value)

        passed = expected.expected_value in actual_str

        # Build lookup description for log messages
        lookup_desc = " AND ".join(
            f"{lookup.row_entry_name}={lookup.row_entry_value}" for lookup in expected.row_lookup
        )

        if passed:
            log = (
                f"✓ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"contains '{expected.expected_value}'"
            )
        else:
            log = (
                f"✗ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"does not contain '{expected.expected_value}' (actual: '{actual_str}')"
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_contain", expected.cif_entry_name),
            passed=passed,
            log=log,
        )
    except (ValueMissingError, ValueError, IndexError) as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_contain", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


def test_cif_loop_entry_missing(
    adapter: CIFIOAdapter, expected: CifLoopEntryMissingExpectedResult
) -> IndividualTestResult:
    """Test that a specific loop column does NOT exist."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)
        # If we get here, the entry exists, which means the test failed
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_missing", expected.cif_entry_name),
            passed=False,
            log=f"✗ Loop entry '{expected.cif_entry_name}' should be missing but was found with value '{actual_value}'",
        )
    except ValueMissingError:
        # Entry is missing, which is what we expect
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_missing", expected.cif_entry_name),
            passed=True,
            log=f"✓ Loop entry '{expected.cif_entry_name}' is missing as expected",
        )
    except (ValueError, IndexError):
        # Row lookup failed, treat as missing
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_missing", expected.cif_entry_name),
            passed=True,
            log=f"✓ Loop entry '{expected.cif_entry_name}' is missing (lookup failed as expected)",
        )


def test_cif_loop_entry_present(
    adapter: CIFIOAdapter, expected: CifLoopEntryPresentExpectedResult
) -> IndividualTestResult:
    """Test that a loop entry exists in a specific row."""
    try:
        # Convert RowLookup models to tuple list
        row_lookups = [(lookup.row_entry_name, str(lookup.row_entry_value)) for lookup in expected.row_lookup]

        actual_value = adapter.get_loop_entry_from_cif_block(expected.cif_entry_name, row_lookups)
        actual_str = str(actual_value).strip()

        # Check if value is undefined (? or .)
        is_undefined = actual_str in ("?", ".")

        # Build lookup description for log messages
        lookup_desc = " AND ".join(
            f"{lookup.row_entry_name}={lookup.row_entry_value}" for lookup in expected.row_lookup
        )

        if is_undefined and not expected.allow_unknown:
            return IndividualTestResult(
                test_case_name=generate_test_case_name("loop_present", expected.cif_entry_name),
                passed=False,
                log=(
                    f"✗ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                    f"is present but has undefined value '{actual_str}' (allow_unknown=False)"
                ),
            )

        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_present", expected.cif_entry_name),
            passed=True,
            log=(
                f"✓ Loop entry '{expected.cif_entry_name}' (where {lookup_desc}) "
                f"is present with value '{actual_value}'"
            ),
        )
    except (ValueMissingError, ValueError, IndexError) as e:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("loop_present", expected.cif_entry_name),
            passed=False,
            log=f"✗ {str(e)}",
        )


# ============================================================================
# Test Function Lookup Map
# ============================================================================

TEST_FUNCTION_MAP: dict[type, Callable[[CIFIOAdapter, Any], IndividualTestResult]] = {
    CifEntryMatchExpectedResult: test_cif_entry_match,
    CifEntryNonMatchExpectedResult: test_cif_entry_non_match,
    CifEntryWithinExpectedResult: test_cif_entry_within,
    CifEntryContainExpectedResult: test_cif_entry_contain,
    CifEntryMissingExpectedResult: test_cif_entry_missing,
    CifEntryPresentExpectedResult: test_cif_entry_present,
    CifLoopEntryMatchExpectedResult: test_cif_loop_entry_match,
    CifLoopEntryNonMatchExpectedResult: test_cif_loop_entry_non_match,
    CifLoopEntryWithinExpectedResult: test_cif_loop_entry_within,
    CifLoopEntryContainExpectedResult: test_cif_loop_entry_contain,
    CifLoopEntryMissingExpectedResult: test_cif_loop_entry_missing,
    CifLoopEntryPresentExpectedResult: test_cif_loop_entry_present,
}
# StatusExpectedResult is not tested here since its success/failure is determined
# at a higher level (command execution) and does not require CIF parsing.


# ============================================================================
# Main Check Result Function
# ============================================================================


def check_result(cif_text: str, expected_result: ExpectedResultType) -> IndividualTestResult:
    """
    Check a CIF output against an expected result specification.

    Args:
        cif_text: The CIF file content to test
        expected_result: The expected result specification

    Returns
    -------
        IndividualTestResult with the test outcome

    """
    # Create adapter for CIF parsing
    adapter = PyCIFRWAdapter(cif_text)

    # Look up the appropriate test function based on the result type
    test_function = TEST_FUNCTION_MAP.get(type(expected_result))

    if test_function is None:
        return IndividualTestResult(
            test_case_name=generate_test_case_name("unknown"),
            passed=False,
            log=f"✗ Unknown test type: {type(expected_result).__name__}",
        )

    # Execute the test
    return test_function(adapter, expected_result)
