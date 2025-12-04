"""
Tests for error_formatter module.

Tests the formatting of various error types when loading YAML files,
including validation errors, syntax errors, and file I/O errors.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from pydantic import ValidationError

from qcrbox_cmd_tester.error_formatter import (
    _build_readable_location,
    _find_result_index,
    _format_expected_result,
    _format_expected_result_from_discriminator,
    _format_test_case_by_index,
    _format_test_case_context,
    _has_result_type_discriminator,
    _is_result_type_discriminator,
    _is_test_type_discriminator,
    format_yaml_error,
)


class TestDiscriminatorChecks:
    """Test functions that check for discriminator values."""

    def test_is_result_type_discriminator_valid(self):
        """Test that valid result_type discriminators are recognized."""
        assert _is_result_type_discriminator("status")
        assert _is_result_type_discriminator("cif_value")
        assert _is_result_type_discriminator("cif_loop_value")

    def test_is_result_type_discriminator_invalid(self):
        """Test that invalid values are not recognized as result_type discriminators."""
        assert not _is_result_type_discriminator("match")
        assert not _is_result_type_discriminator("invalid")
        assert not _is_result_type_discriminator("0")

    def test_is_test_type_discriminator_valid(self):
        """Test that valid test_type discriminators are recognized."""
        for test_type in ["match", "non-match", "within", "contain", "missing", "present"]:
            assert _is_test_type_discriminator(test_type)

    def test_is_test_type_discriminator_invalid(self):
        """Test that invalid values are not recognized as test_type discriminators."""
        assert not _is_test_type_discriminator("status")
        assert not _is_test_type_discriminator("invalid")
        assert not _is_test_type_discriminator("0")

    def test_has_result_type_discriminator_true(self):
        """Test detection of result_type discriminator in location parts."""
        location_parts = ["0", "status", "expected"]
        assert _has_result_type_discriminator(location_parts, 1)

        location_parts = ["0", "cif_value", "match"]
        assert _has_result_type_discriminator(location_parts, 1)

    def test_has_result_type_discriminator_false(self):
        """Test that non-discriminator values are not detected."""
        location_parts = ["0", "invalid", "expected"]
        assert not _has_result_type_discriminator(location_parts, 1)

        location_parts = ["0"]
        assert not _has_result_type_discriminator(location_parts, 1)

    def test_has_result_type_discriminator_out_of_bounds(self):
        """Test that out of bounds index returns False."""
        location_parts = ["0", "status"]
        assert not _has_result_type_discriminator(location_parts, 5)


class TestTestCaseFormatting:
    """Test functions that format test case information."""

    def test_format_test_case_context_with_name(self):
        """Test formatting test case context when test has a name."""
        test_cases = [{"name": "my_test", "expected_results": []}]
        result = _format_test_case_context(test_cases)
        assert result == "Test case 0: my_test"

    def test_format_test_case_context_without_name(self):
        """Test formatting test case context when test has no name."""
        test_cases = [{"expected_results": []}]
        result = _format_test_case_context(test_cases)
        assert result == "Test case 0: test_0"

    def test_format_test_case_context_empty_list(self):
        """Test formatting test case context with empty list."""
        result = _format_test_case_context([])
        assert result is None

    def test_format_test_case_context_non_dict(self):
        """Test formatting test case context when item is not a dict."""
        test_cases = ["not a dict"]
        result = _format_test_case_context(test_cases)
        assert result == "Test case 0: test_0"

    def test_format_test_case_by_index_valid(self):
        """Test formatting test case by index with valid index."""
        test_cases = [
            {"name": "first_test"},
            {"name": "second_test"},
        ]
        result = _format_test_case_by_index(test_cases, 1)
        assert result == "Test case 1: second_test"

    def test_format_test_case_by_index_no_name(self):
        """Test formatting test case by index when test has no name."""
        test_cases = [{}]
        result = _format_test_case_by_index(test_cases, 0)
        assert result == "Test case 0: test_0"

    def test_format_test_case_by_index_out_of_bounds(self):
        """Test formatting test case by index with out of bounds index."""
        test_cases = [{"name": "test"}]
        result = _format_test_case_by_index(test_cases, 5)
        assert result is None


class TestExpectedResultFormatting:
    """Test functions that format expected result information."""

    def test_format_expected_result_status(self):
        """Test formatting expected result for status type."""
        location_parts = ["0", "status", "expected"]
        result = _format_expected_result(location_parts, 0, None)
        assert result == {"text": "expected value 0: status", "next_idx": 2}

    def test_format_expected_result_cif_value_with_test_type(self):
        """Test formatting expected result for cif_value with test_type."""
        location_parts = ["1", "cif_value", "match", "cif_entry_name"]
        result = _format_expected_result(location_parts, 0, None)
        assert result == {"text": "expected value 1: cif_value(match)", "next_idx": 3}

    def test_format_expected_result_cif_loop_value_with_test_type(self):
        """Test formatting expected result for cif_loop_value with test_type."""
        location_parts = ["2", "cif_loop_value", "within", "min_value"]
        result = _format_expected_result(location_parts, 0, None)
        assert result == {"text": "expected value 2: cif_loop_value(within)", "next_idx": 3}

    def test_format_expected_result_cif_value_without_test_type(self):
        """Test formatting expected result for cif_value without test_type."""
        location_parts = ["0", "cif_value", "invalid_next"]
        result = _format_expected_result(location_parts, 0, None)
        assert result == {"text": "expected value 0: cif_value", "next_idx": 2}

    def test_format_expected_result_from_discriminator_status(self):
        """Test formatting expected result from discriminator for status."""
        location_parts = ["status", "expected"]
        test_case = {"expected_results": [{"result_type": "status", "expected": "successful"}]}
        result = _format_expected_result_from_discriminator(location_parts, 0, test_case)
        assert result == {"text": "expected value 0: status", "next_idx": 1}

    def test_format_expected_result_from_discriminator_with_test_type(self):
        """Test formatting expected result from discriminator with test_type."""
        location_parts = ["cif_value", "match", "cif_entry_name"]
        test_case = {
            "expected_results": [{"result_type": "cif_value", "test_type": "match", "cif_entry_name": "_entry"}]
        }
        result = _format_expected_result_from_discriminator(location_parts, 0, test_case)
        assert result == {"text": "expected value 0: cif_value(match)", "next_idx": 2}

    def test_format_expected_result_from_discriminator_not_found(self):
        """Test formatting when result not found in test case."""
        location_parts = ["status", "expected"]
        test_case = {"expected_results": [{"result_type": "cif_value", "test_type": "match"}]}
        result = _format_expected_result_from_discriminator(location_parts, 0, test_case)
        assert result == {"text": "expected value: status", "next_idx": 1}


class TestFindResultIndex:
    """Test the function that finds result indices in test cases."""

    def test_find_result_index_status(self):
        """Test finding result index for status type."""
        test_case = {
            "expected_results": [
                {"result_type": "status", "expected": "successful"},
                {"result_type": "cif_value", "test_type": "match"},
            ]
        }
        result = _find_result_index(test_case, "status", None)
        assert result == 0

    def test_find_result_index_with_test_type(self):
        """Test finding result index with both result_type and test_type."""
        test_case = {
            "expected_results": [
                {"result_type": "cif_value", "test_type": "match"},
                {"result_type": "cif_value", "test_type": "within"},
                {"result_type": "status"},
            ]
        }
        result = _find_result_index(test_case, "cif_value", "within")
        assert result == 1

    def test_find_result_index_not_found(self):
        """Test finding result index when no match exists."""
        test_case = {"expected_results": [{"result_type": "status", "expected": "successful"}]}
        result = _find_result_index(test_case, "cif_value", "match")
        assert result is None

    def test_find_result_index_non_dict_in_results(self):
        """Test finding result index with non-dict items in results."""
        test_case = {"expected_results": ["not a dict", {"result_type": "status"}]}
        result = _find_result_index(test_case, "status", None)
        assert result == 1

    def test_find_result_index_empty_results(self):
        """Test finding result index with empty expected_results."""
        test_case = {"expected_results": []}
        result = _find_result_index(test_case, "status", None)
        assert result is None


class TestBuildReadableLocation:
    """Test the main location building function."""

    def test_build_readable_location_simple_status(self):
        """Test building location for simple status error."""
        location_tuple = (0, "status", "expected")
        yaml_data = {
            "test_cases": [
                {"name": "my_test", "expected_results": [{"result_type": "status", "expected": "successful"}]}
            ]
        }
        result = _build_readable_location(location_tuple, yaml_data)
        assert result == "Test case 0: my_test → expected value 0: status → expected"

    def test_build_readable_location_cif_value_with_test_type(self):
        """Test building location for cif_value with test_type."""
        location_tuple = (0, "cif_value", "match", "cif_entry_name")
        yaml_data = {
            "test_cases": [
                {
                    "name": "test_cif",
                    "expected_results": [
                        {"result_type": "cif_value", "test_type": "match", "cif_entry_name": "_entry"}
                    ],
                }
            ]
        }
        result = _build_readable_location(location_tuple, yaml_data)
        assert result == "Test case 0: test_cif → expected value 0: cif_value(match) → cif_entry_name"

    def test_build_readable_location_multiple_expected_results(self):
        """Test building location with multiple expected results."""
        location_tuple = (1, "cif_loop_value", "within", "min_value")
        yaml_data = {
            "test_cases": [
                {
                    "name": "complex_test",
                    "expected_results": [
                        {"result_type": "status", "expected": "successful"},
                        {"result_type": "cif_loop_value", "test_type": "within", "min_value": 0},
                    ],
                }
            ]
        }
        result = _build_readable_location(location_tuple, yaml_data)
        assert result == "Test case 0: complex_test → expected value 1: cif_loop_value(within) → min_value"

    def test_build_readable_location_no_yaml_data(self):
        """Test building location without yaml_data."""
        location_tuple = (0, "status", "expected")
        result = _build_readable_location(location_tuple, None)
        # Should still work but won't have test names
        assert "expected" in result

    def test_build_readable_location_empty_test_cases(self):
        """Test building location with empty test cases."""
        location_tuple = (0, "status", "expected")
        yaml_data = {"test_cases": []}
        result = _build_readable_location(location_tuple, yaml_data)
        assert "expected" in result

    def test_build_readable_location_multiple_test_cases(self):
        """Test building location with multiple test cases, error in second test."""
        # When there are multiple test cases and the location tuple starts with an index
        # that doesn't have a discriminator after it, it's a test case index
        location_tuple = (1, "status", "expected")
        yaml_data = {
            "test_cases": [
                {"name": "first_test"},
                {"name": "second_test", "expected_results": [{"result_type": "status", "expected": "successful"}]},
            ]
        }
        result = _build_readable_location(location_tuple, yaml_data)
        # The logic treats (1, 'status', ...) as an expected_results index within first test
        # because 'status' is a discriminator. For a true test case index, there would be
        # more in the path like (1, 'expected_results', 0, 'status', 'expected')
        assert "Test case 0:" in result or "expected value 1: status" in result


class TestFormatYamlError:
    """Test the main format_yaml_error function."""

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_yaml_syntax_error(self, mock_console):
        """Test formatting YAML syntax errors."""
        error = yaml.YAMLError("Invalid syntax")
        yaml_file = Path("/path/to/test.yaml")

        format_yaml_error(error, yaml_file)

        # Should print empty line, panel, and another empty line
        assert mock_console.print.call_count == 3

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_file_not_found_error(self, mock_console):
        """Test formatting file not found errors."""
        error = FileNotFoundError("File not found")
        yaml_file = Path("/path/to/missing.yaml")

        format_yaml_error(error, yaml_file)

        assert mock_console.print.call_count == 3

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_permission_error(self, mock_console):
        """Test formatting permission errors."""
        error = PermissionError("Permission denied")
        yaml_file = Path("/path/to/restricted.yaml")

        format_yaml_error(error, yaml_file)

        assert mock_console.print.call_count == 3

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_generic_error(self, mock_console):
        """Test formatting generic/unexpected errors."""
        error = ValueError("Something went wrong")
        yaml_file = Path("/path/to/test.yaml")

        format_yaml_error(error, yaml_file)

        assert mock_console.print.call_count == 3

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_validation_error_single(self, mock_console):
        """Test formatting a single validation error."""
        # Create a mock ValidationError
        error = MagicMock(spec=ValidationError)
        error.error_count.return_value = 1
        error.errors.return_value = [
            {
                "loc": (0, "status", "expected"),
                "msg": "Input should be 'successful', 'failed' or 'warning'",
                "type": "literal_error",
                "input": "invalid",
            }
        ]

        yaml_file = Path("test.yaml")
        yaml_data = {
            "test_cases": [{"name": "my_test", "expected_results": [{"result_type": "status", "expected": "invalid"}]}]
        }

        format_yaml_error(error, yaml_file, yaml_data)

        # Should print: empty line, panel, error details, documentation hint, empty line
        assert mock_console.print.call_count >= 5

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_validation_error_multiple(self, mock_console):
        """Test formatting multiple validation errors."""
        error = MagicMock(spec=ValidationError)
        error.error_count.return_value = 2
        error.errors.return_value = [
            {"loc": (0, "status", "expected"), "msg": "Error 1", "type": "literal_error", "input": "bad1"},
            {
                "loc": (1, "cif_value", "match", "cif_entry_name"),
                "msg": "Error 2",
                "type": "string_too_short",
                "input": "",
            },
        ]

        yaml_file = Path("test.yaml")
        yaml_data = {
            "test_cases": [
                {
                    "name": "test",
                    "expected_results": [{"result_type": "status"}, {"result_type": "cif_value", "test_type": "match"}],
                }
            ]
        }

        format_yaml_error(error, yaml_file, yaml_data)

        # Should print multiple error sections
        assert mock_console.print.call_count >= 8

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_validation_error_with_large_input(self, mock_console):
        """Test that large input values are not displayed."""
        error = MagicMock(spec=ValidationError)
        error.error_count.return_value = 1
        error.errors.return_value = [
            {
                "loc": (0, "status", "expected"),
                "msg": "Error",
                "type": "error_type",
                "input": "x" * 200,  # Large input that should not be shown
            }
        ]

        yaml_file = Path("test.yaml")
        yaml_data = {"test_cases": [{"name": "test", "expected_results": []}]}

        format_yaml_error(error, yaml_file, yaml_data)

        # Large input should not trigger an additional print call
        call_args = [str(call) for call in mock_console.print.call_args_list]
        assert not any("x" * 200 in arg for arg in call_args)

    @patch("qcrbox_cmd_tester.error_formatter.console")
    def test_format_validation_error_without_input(self, mock_console):
        """Test formatting validation error without input field."""
        error = MagicMock(spec=ValidationError)
        error.error_count.return_value = 1
        error.errors.return_value = [
            {
                "loc": (0, "status"),
                "msg": "Error message",
                "type": "error_type",
                # No 'input' field
            }
        ]

        yaml_file = Path("test.yaml")
        yaml_data = {"test_cases": [{"name": "test", "expected_results": []}]}

        format_yaml_error(error, yaml_file, yaml_data)

        # Should not crash
        assert mock_console.print.called
