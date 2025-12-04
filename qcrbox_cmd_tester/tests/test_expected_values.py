"""Tests for the expected_values module."""

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
    ExpectedResultTypeAdapter,
    StatusExpectedResult,
)


def parse_data(data: dict):
    """Parse expected result from YAML dictionary."""
    return ExpectedResultTypeAdapter.validate_python(data)


# Test StatusExpectedResult parsing


def test_parse_successful():
    """Test parsing successful status."""
    data = {"result_type": "status", "expected": "successful"}
    result = parse_data(data)

    assert isinstance(result, StatusExpectedResult)
    assert result.expected == "successful"
    assert result.result_type == "status"


# Test CIF entry (non-loop) expected result parsing


def test_parse_match_string():
    """Test parsing CIF entry match with string value."""
    data = {
        "result_type": "cif_value",
        "test_type": "match",
        "cif_entry_name": "_test.entry",
        "expected_value": "C",
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryMatchExpectedResult)
    assert result.cif_entry_name == "_test.entry"
    assert result.expected_value == "C"
    assert result.test_type == "match"


def test_parse_non_match():
    """Test parsing CIF entry non-match."""
    data = {
        "result_type": "cif_value",
        "test_type": "non-match",
        "cif_entry_name": "_test.entry",
        "forbidden_value": "D",
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryNonMatchExpectedResult)
    assert result.forbidden_value == "D"


def test_parse_within_deviation():
    """Test parsing within test with deviation."""
    data = {
        "result_type": "cif_value",
        "test_type": "within",
        "cif_entry_name": "_test.entry",
        "expected_value": 1.234,
        "allowed_deviation": 0.001,
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryWithinExpectedResult)
    assert result.min_value == pytest.approx(1.233)
    assert result.max_value == pytest.approx(1.235)


def test_parse_within_minmax():
    """Test parsing within test with min/max values."""
    data = {
        "result_type": "cif_value",
        "test_type": "within",
        "cif_entry_name": "_test.entry",
        "min_value": 5.0,
        "max_value": 6.0,
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryWithinExpectedResult)
    assert result.min_value == 5.0
    assert result.max_value == 6.0


def test_parse_contain():
    """Test parsing contain test."""
    data = {
        "result_type": "cif_value",
        "test_type": "contain",
        "cif_entry_name": "_test.entry",
        "expected_value": "check_me",
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryContainExpectedResult)
    assert result.expected_value == "check_me"


def test_parse_missing():
    """Test parsing missing test."""
    data = {"result_type": "cif_value", "test_type": "missing", "cif_entry_name": "_test.entry"}
    result = parse_data(data)

    assert isinstance(result, CifEntryMissingExpectedResult)
    assert result.cif_entry_name == "_test.entry"


def test_parse_present_no_undefined():
    """Test parsing present test with undefined not allowed."""
    data = {
        "result_type": "cif_value",
        "test_type": "present",
        "cif_entry_name": "_test.entry",
        "allow_unknown": False,
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryPresentExpectedResult)
    assert result.allow_unknown is False


def test_parse_present_allow_unknown():
    """Test parsing present test with undefined allowed."""
    data = {
        "result_type": "cif_value",
        "test_type": "present",
        "cif_entry_name": "_test.entry",
        "allow_unknown": True,
    }
    result = parse_data(data)

    assert isinstance(result, CifEntryPresentExpectedResult)
    assert result.allow_unknown is True


def test_parse_present_default_undefined():
    """Test parsing present test with default undefined handling."""
    # allow_unknown defaults to False
    data = {"result_type": "cif_value", "test_type": "present", "cif_entry_name": "_test.entry"}
    result = parse_data(data)

    assert isinstance(result, CifEntryPresentExpectedResult)
    assert result.allow_unknown is False


# Test CIF loop entry expected result parsing


def test_parse_loop_match():
    """Test parsing loop entry match."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "match",
        "cif_entry_name": "_loop.value",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 1}],
        "expected_value": 12,
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryMatchExpectedResult)
    assert result.cif_entry_name == "_loop.value"
    assert len(result.row_lookup) == 1
    assert result.row_lookup[0].row_entry_name == "_loop.index"
    assert result.row_lookup[0].row_entry_value == 1
    assert result.expected_value == 12


def test_parse_loop_non_match():
    """Test parsing loop entry non-match."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "non-match",
        "cif_entry_name": "_loop.value",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 1}],
        "forbidden_value": 13,
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryNonMatchExpectedResult)
    assert result.forbidden_value == 13


def test_parse_loop_within_deviation():
    """Test parsing loop within test with deviation."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "within",
        "cif_entry_name": "_loop.value",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 2}],
        "expected_value": 12,
        "allowed_deviation": 0.001,
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryWithinExpectedResult)
    assert result.min_value == pytest.approx(11.999)
    assert result.max_value == pytest.approx(12.001)


def test_parse_loop_within_minmax():
    """Test parsing loop within test with min/max values."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "within",
        "cif_entry_name": "_loop.value",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 1}],
        "min_value": 10,
        "max_value": 15,
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryWithinExpectedResult)
    assert result.min_value == 10
    assert result.max_value == 15


def test_parse_loop_contain():
    """Test parsing loop contain test."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "contain",
        "cif_entry_name": "_loop.text",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 2}],
        "expected_value": "another",
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryContainExpectedResult)
    assert result.expected_value == "another"


def test_parse_loop_missing():
    """Test parsing loop missing test."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "missing",
        "cif_entry_name": "_loop.nonexistent",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 1}],
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryMissingExpectedResult)
    assert result.cif_entry_name == "_loop.nonexistent"


def test_parse_loop_present():
    """Test parsing loop present test."""
    data = {
        "result_type": "cif_loop_value",
        "test_type": "present",
        "cif_entry_name": "_loop.maybe_undefined",
        "row_lookup": [{"row_entry_name": "_loop.index", "row_entry_value": 1}],
        "allow_unknown": True,
    }
    result = parse_data(data)

    assert isinstance(result, CifLoopEntryPresentExpectedResult)
    assert result.allow_unknown is True


def test_within_missing_required_fields():
    """Test within test with missing required fields raises error."""
    # Missing both deviation and min/max
    data = {"result_type": "cif_value", "test_type": "within", "cif_entry_name": "_test.entry"}

    with pytest.raises(ValueError, match="requires either"):
        parse_data(data)
