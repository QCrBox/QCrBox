"""Tests for the test_implementations module."""

import pytest

from qcrbox_cmd_tester.models.expected_values import (
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
    RowLookup,
)
from qcrbox_cmd_tester.test_implementations import (
    TEST_FUNCTION_MAP,
    IndividualTestResult,
    check_result,
    generate_test_case_name,
)


@pytest.fixture
def sample_cif():
    """Sample CIF text for testing."""
    return """
data_example
_cif.entry1 C
_cif.entry2 1.234
_another.entry 5.678
_cif.string_entry 'Check only for this part: check_me'
_cif.value_is_undefined ?

loop_
_loop_entry.index
_loop_entry.index_additional
_loop_entry.value
_loop_entry.present_entry
_loop_entry.potentially_undefined
1 6 12 'multi-word string' ?
2 7 13 'another string' .
2 6 18 'do not use this one' .
3 7 19 'do not find this one either' ?
"""


# Test check_result function with CIF entry tests


def test_match_success(sample_cif):
    """Test successful match of CIF entry value."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry1", expected_value="C")
    result = check_result(sample_cif, expected)

    assert isinstance(result, IndividualTestResult)
    assert result.passed is True
    assert "match" in result.log.lower()


def test_match_failure(sample_cif):
    """Test failed match of CIF entry value."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry1", expected_value="D")
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "expected" in result.log.lower()


def test_match_numerical_int(sample_cif):
    """Test match with numerical value (int)."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry2", expected_value=1.234)
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "match" in result.log.lower()


def test_match_numerical_float_trailing_zeros(sample_cif):
    """Test match with numerical value having different trailing zeros."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry2", expected_value=1.2340)
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_match_numerical_string_representation(sample_cif):
    """Test match with numerical value as string."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry2", expected_value="1.234")
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_match_numerical_failure(sample_cif):
    """Test failed match with different numerical value."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_cif.entry2", expected_value=1.235)
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_non_match_success(sample_cif):
    """Test successful non-match verification."""
    expected = CifEntryNonMatchExpectedResult(cif_entry_name="_cif.entry1", forbidden_value="D")
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_non_match_failure(sample_cif):
    """Test failed non-match verification."""
    expected = CifEntryNonMatchExpectedResult(cif_entry_name="_cif.entry1", forbidden_value="C")
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_within_success(sample_cif):
    """Test successful within range check."""
    expected = CifEntryWithinExpectedResult(cif_entry_name="_cif.entry2", min_value=1.233, max_value=1.235)
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "within" in result.log.lower()


def test_within_failure(sample_cif):
    """Test failed within range check."""
    expected = CifEntryWithinExpectedResult(cif_entry_name="_cif.entry2", min_value=2.0, max_value=3.0)
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "outside" in result.log.lower()


def test_contain_success(sample_cif):
    """Test successful substring containment check."""
    expected = CifEntryContainExpectedResult(cif_entry_name="_cif.string_entry", expected_value="check_me")
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_contain_failure(sample_cif):
    """Test failed substring containment check."""
    expected = CifEntryContainExpectedResult(cif_entry_name="_cif.string_entry", expected_value="not_there")
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_missing_success(sample_cif):
    """Test successful missing entry verification."""
    expected = CifEntryMissingExpectedResult(cif_entry_name="_nonexistent.entry")
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "missing as expected" in result.log.lower()


def test_missing_failure(sample_cif):
    """Test failed missing entry verification."""
    expected = CifEntryMissingExpectedResult(cif_entry_name="_cif.entry1")
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_present_success(sample_cif):
    """Test successful present entry verification."""
    expected = CifEntryPresentExpectedResult(cif_entry_name="_another.entry", allow_unknown=False)
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_present_undefined_allowed(sample_cif):
    """Test present entry with undefined value allowed."""
    expected = CifEntryPresentExpectedResult(cif_entry_name="_cif.value_is_undefined", allow_unknown=True)
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_present_undefined_not_allowed(sample_cif):
    """Test present entry with undefined value not allowed."""
    expected = CifEntryPresentExpectedResult(cif_entry_name="_cif.value_is_undefined", allow_unknown=False)
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "undefined" in result.log.lower()


# Test check_result function with CIF loop entry tests


def test_loop_match_success(sample_cif):
    """Test successful loop entry match."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value=12,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_match_failure(sample_cif):
    """Test failed loop entry match."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value=99,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_match_numerical_int(sample_cif):
    """Test loop entry match with numerical value as int."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value=12,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_match_numerical_float(sample_cif):
    """Test loop entry match with numerical value as float."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value=12.0,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_match_numerical_string(sample_cif):
    """Test loop entry match with numerical value as string."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value="12",
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_present_undefined_allowed(sample_cif):
    """Test loop entry present with undefined value allowed."""
    expected = CifLoopEntryPresentExpectedResult(
        cif_entry_name="_loop_entry.potentially_undefined",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        allow_unknown=True,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_present_undefined_not_allowed(sample_cif):
    """Test loop entry present with undefined value not allowed."""
    expected = CifLoopEntryPresentExpectedResult(
        cif_entry_name="_loop_entry.potentially_undefined",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        allow_unknown=False,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


# Test that the TEST_FUNCTION_MAP is properly configured


def test_map_has_all_types():
    """Ensure all expected result types have corresponding test functions."""
    expected_types = [
        CifEntryMatchExpectedResult,
        CifEntryNonMatchExpectedResult,
        CifEntryWithinExpectedResult,
        CifEntryContainExpectedResult,
        CifEntryMissingExpectedResult,
        CifEntryPresentExpectedResult,
        CifLoopEntryMatchExpectedResult,
        # Add more as needed
    ]

    for expected_type in expected_types:
        assert expected_type in TEST_FUNCTION_MAP, f"Missing test function for {expected_type.__name__}"


def test_map_functions_callable():
    """Ensure all functions in the map are callable."""
    for func in TEST_FUNCTION_MAP.values():
        assert callable(func)


# Test the generate_test_case_name helper function


def test_with_entry_name():
    """Test name generation with entry name."""
    name = generate_test_case_name("match", "_cif.entry1")
    assert name == "match__cif.entry1"


def test_without_entry_name():
    """Test name generation without entry name."""
    name = generate_test_case_name("status")
    assert name == "status_test"


def test_loop_test_naming():
    """Test name generation for loop tests."""
    name = generate_test_case_name("loop_match", "_loop_entry.value")
    assert name == "loop_match__loop_entry.value"


def test_none_entry_name():
    """Test with explicitly None entry name."""
    name = generate_test_case_name("unknown", None)
    assert name == "unknown_test"


def test_loop_non_match_success(sample_cif):
    """Test successful loop entry non-match verification."""
    expected = CifLoopEntryNonMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        forbidden_value=99,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_non_match_failure(sample_cif):
    """Test failed loop entry non-match verification."""
    expected = CifLoopEntryNonMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        forbidden_value=12,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_within_success(sample_cif):
    """Test successful loop entry within range check."""
    expected = CifLoopEntryWithinExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        min_value=11,
        max_value=13,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "within" in result.log.lower()


def test_loop_within_failure(sample_cif):
    """Test failed loop entry within range check."""
    expected = CifLoopEntryWithinExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        min_value=20,
        max_value=30,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "outside" in result.log.lower()


def test_loop_contain_success(sample_cif):
    """Test successful loop entry substring containment check."""
    expected = CifLoopEntryContainExpectedResult(
        cif_entry_name="_loop_entry.present_entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value="multi",
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True


def test_loop_contain_failure(sample_cif):
    """Test failed loop entry substring containment check."""
    expected = CifLoopEntryContainExpectedResult(
        cif_entry_name="_loop_entry.present_entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value="not_there",
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_missing_success(sample_cif):
    """Test successful loop entry missing verification."""
    expected = CifLoopEntryMissingExpectedResult(
        cif_entry_name="_loop_entry.nonexistent",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "missing" in result.log.lower()


def test_loop_missing_failure(sample_cif):
    """Test failed loop entry missing verification."""
    expected = CifLoopEntryMissingExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_match_missing_entry(sample_cif):
    """Test match when entry is missing."""
    expected = CifEntryMatchExpectedResult(cif_entry_name="_nonexistent.entry", expected_value="test")
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not found" in result.log.lower()


def test_non_match_missing_entry(sample_cif):
    """Test non-match when entry is missing."""
    expected = CifEntryNonMatchExpectedResult(cif_entry_name="_nonexistent.entry", forbidden_value="test")
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not found" in result.log.lower()


def test_within_missing_entry(sample_cif):
    """Test within when entry is missing."""
    expected = CifEntryWithinExpectedResult(cif_entry_name="_nonexistent.entry", min_value=1.0, max_value=2.0)
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not found" in result.log.lower()


def test_within_invalid_number(sample_cif):
    """Test within when entry is not a valid number."""
    expected = CifEntryWithinExpectedResult(
        cif_entry_name="_cif.entry1",  # This is "C", not a number
        min_value=1.0,
        max_value=2.0,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not a valid number" in result.log.lower()


def test_contain_missing_entry(sample_cif):
    """Test contain when entry is missing."""
    expected = CifEntryContainExpectedResult(cif_entry_name="_nonexistent.entry", expected_value="test")
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not found" in result.log.lower()


def test_loop_non_match_missing_entry(sample_cif):
    """Test loop non-match when entry is missing."""
    expected = CifLoopEntryNonMatchExpectedResult(
        cif_entry_name="_nonexistent.entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        forbidden_value="test",
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_within_missing_entry(sample_cif):
    """Test loop within when entry is missing."""
    expected = CifLoopEntryWithinExpectedResult(
        cif_entry_name="_nonexistent.entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        min_value=1.0,
        max_value=2.0,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_within_invalid_number(sample_cif):
    """Test loop within when entry is not a valid number."""
    expected = CifLoopEntryWithinExpectedResult(
        cif_entry_name="_loop_entry.present_entry",  # This is a string
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        min_value=1.0,
        max_value=2.0,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "not a valid number" in result.log.lower()


def test_loop_contain_missing_entry(sample_cif):
    """Test loop contain when entry is missing."""
    expected = CifLoopEntryContainExpectedResult(
        cif_entry_name="_nonexistent.entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        expected_value="test",
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


def test_loop_missing_with_invalid_row(sample_cif):
    """Test loop missing with invalid row lookup."""
    expected = CifLoopEntryMissingExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=999)],  # Non-existent row
    )
    result = check_result(sample_cif, expected)

    # Should pass because the lookup fails (treated as missing)
    assert result.passed is True


def test_loop_present_missing_entry(sample_cif):
    """Test loop present when entry is missing."""
    expected = CifLoopEntryPresentExpectedResult(
        cif_entry_name="_nonexistent.entry",
        row_lookup=[RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1)],
        allow_unknown=False,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False


# Test multi-row lookup functionality


def test_multi_row_lookup_match_success(sample_cif):
    """Test successful loop entry match with multiple lookup conditions."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[
            RowLookup(row_entry_name="_loop_entry.index", row_entry_value=2),
            RowLookup(row_entry_name="_loop_entry.index_additional", row_entry_value=6),
        ],
        expected_value=18,  # Should match row 3: 2 6 18 ...
    )
    result = check_result(sample_cif, expected)

    assert result.passed is True
    assert "2 AND" in result.log
    assert "6" in result.log


def test_multi_row_lookup_no_match(sample_cif):
    """Test loop entry match fails when no row matches all conditions."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[
            RowLookup(row_entry_name="_loop_entry.index", row_entry_value=1),
            RowLookup(row_entry_name="_loop_entry.index_additional", row_entry_value=7),  # Impossible combo
        ],
        expected_value=12,
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "No row found matching conditions" in result.log


def test_multi_row_lookup_wrong_value(sample_cif):
    """Test multi-row lookup finds correct row but value doesn't match."""
    expected = CifLoopEntryMatchExpectedResult(
        cif_entry_name="_loop_entry.value",
        row_lookup=[
            RowLookup(row_entry_name="_loop_entry.index", row_entry_value=2),
            RowLookup(row_entry_name="_loop_entry.index_additional", row_entry_value=7),
        ],
        expected_value=99,  # Should find row 2 (2 7 13) but value is wrong
    )
    result = check_result(sample_cif, expected)

    assert result.passed is False
    assert "expected '99', got '13'" in result.log
