"""Tests for the run_suite module."""

from unittest.mock import Mock, patch

import pytest
from CifFile.StarFile import StarError

from qcrbox_cmd_tester.models import (
    QCrBoxFileParameter,
    QCrBoxParameter,
    TestCase,
    TestSuite,
)
from qcrbox_cmd_tester.models.expected_values import (
    CifEntryMatchExpectedResult,
    CifEntryPresentExpectedResult,
    StatusExpectedResult,
)
from qcrbox_cmd_tester.qcrbox_client import CommandRunResult
from qcrbox_cmd_tester.run_suite import (
    TestCaseResult,
    TestSuiteResult,
    run_test_case,
    run_test_suite,
)
from qcrbox_cmd_tester.test_implementations import IndividualTestResult

# Fixtures


@pytest.fixture
def mock_client():
    """Create a mock QCrBox client."""
    return Mock()


@pytest.fixture
def sample_cif_output():
    """Sample CIF output from a QCrBox command."""
    return """
data_example
_atom.type C
_atom.count 42
_result.value 1.234
"""


@pytest.fixture
def simple_test_case():
    """Create a simple test case with basic parameters."""
    return TestCase(
        name="test_simple",
        description="A simple test case",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[
            QCrBoxParameter(name="param1", value="value1"),
            QCrBoxParameter(name="param2", value=42),
        ],
        expected_results=[
            CifEntryMatchExpectedResult(cif_entry_name="_atom.type", expected_value="C"),
        ],
    )


@pytest.fixture
def test_case_with_file():
    """Create a test case with file parameters."""
    return TestCase(
        name="test_with_file",
        description="Test case with file input",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="analyze",
        qcrbox_command_parameters=[
            QCrBoxFileParameter(name="input_cif", file_content="data_input\n_test 1\n"),
            QCrBoxParameter(name="mode", value="advanced"),
        ],
        expected_results=[
            CifEntryMatchExpectedResult(cif_entry_name="_result.value", expected_value="1.234"),
        ],
    )


@pytest.fixture
def test_case_with_file_custom_filename():
    """Create a test case with file parameters and custom upload_filename."""
    return TestCase(
        name="test_with_custom_filename",
        description="Test case with custom upload filename",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process_file",
        qcrbox_command_parameters=[
            QCrBoxFileParameter(name="input_file", file_content="test data\n", upload_filename="custom_name.inp"),
            QCrBoxParameter(name="mode", value="test"),
        ],
        expected_results=[
            CifEntryMatchExpectedResult(cif_entry_name="_result.status", expected_value="ok"),
        ],
    )


@pytest.fixture
def test_suite_simple(simple_test_case):
    """Create a simple test suite with one test case."""
    return TestSuite(
        application_slug="test_app",
        application_version="1.0.0",
        description="A simple test suite",
        tests=[simple_test_case],
    )


@pytest.fixture
def test_suite_multiple():
    """Create a test suite with multiple test cases."""
    test_case_1 = TestCase(
        name="test_1",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="cmd1",
        qcrbox_command_parameters=[],
        expected_results=[
            CifEntryMatchExpectedResult(cif_entry_name="_atom.type", expected_value="C"),
        ],
    )

    test_case_2 = TestCase(
        name="test_2",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="cmd2",
        qcrbox_command_parameters=[],
        expected_results=[
            CifEntryPresentExpectedResult(cif_entry_name="_result.value", allow_unknown=False),
        ],
    )

    return TestSuite(
        application_slug="test_app",
        application_version="1.0.0",
        description="Test suite with multiple cases",
        tests=[test_case_1, test_case_2],
    )


# Tests for run_test_case


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_successful(mock_run_command, mock_client, simple_test_case, sample_cif_output):
    """Test running a test case that succeeds."""
    # Mock the QCrBox command to return successful result
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_case(mock_client, simple_test_case)

    # Verify the result
    assert isinstance(result, TestCaseResult)
    assert result.test_case_name == "test_simple"
    assert result.all_passed is True
    assert len(result.individual_results) == 1
    assert all(isinstance(r, IndividualTestResult) for r in result.individual_results)

    # Verify mock was called with correct parameters
    mock_run_command.assert_called_once_with(
        mock_client, "process", "test_app", "1.0.0", simple_test_case.qcrbox_command_parameters, 600.0
    )


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_command_failed(mock_run_command, mock_client, simple_test_case):
    """Test running a test case where the QCrBox command fails."""
    # Mock the QCrBox command to return failed result
    mock_run_command.return_value = CommandRunResult(
        status="failed", result_cif=None, status_events=["Error: computation failed"]
    )

    result = run_test_case(mock_client, simple_test_case)

    # Verify the result
    assert isinstance(result, TestCaseResult)
    assert result.test_case_name == "test_simple"
    assert result.all_passed is False
    assert len(result.individual_results) == 1

    # Check that the individual result indicates command failure
    individual_result = result.individual_results[0]
    assert individual_result.passed is False
    assert "Command execution failed" in individual_result.log


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_validation_failed(mock_run_command, mock_client, simple_test_case):
    """Test running a test case where validation fails."""
    # Mock successful command but with wrong output
    wrong_cif = """
data_example
_atom.type N
_atom.count 42
"""
    mock_run_command.return_value = CommandRunResult(status="successful", result_cif=wrong_cif, status_events=[])

    result = run_test_case(mock_client, simple_test_case)

    # Verify the result
    assert isinstance(result, TestCaseResult)
    assert result.all_passed is False
    assert len(result.individual_results) == 1
    assert result.individual_results[0].passed is False


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_multiple_expectations(mock_run_command, mock_client, sample_cif_output):
    """Test running a test case with multiple expected results."""
    test_case = TestCase(
        name="multi_expect",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[],
        expected_results=[
            CifEntryMatchExpectedResult(cif_entry_name="_atom.type", expected_value="C"),
            CifEntryMatchExpectedResult(cif_entry_name="_atom.count", expected_value="42"),
            CifEntryPresentExpectedResult(cif_entry_name="_result.value", allow_unknown=False),
        ],
    )

    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_case(mock_client, test_case)

    # Verify all expectations were checked
    assert len(result.individual_results) == 3
    assert result.all_passed is True
    assert all(r.passed for r in result.individual_results)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_partial_failure(mock_run_command, mock_client, sample_cif_output):
    """Test a test case where some expectations pass and some fail."""
    test_case = TestCase(
        name="partial_fail",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[],
        expected_results=[
            CifEntryMatchExpectedResult(
                cif_entry_name="_atom.type",
                expected_value="C",  # This should pass
            ),
            CifEntryMatchExpectedResult(
                cif_entry_name="_atom.count",
                expected_value="99",  # This should fail
            ),
        ],
    )

    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_case(mock_client, test_case)

    # Verify partial failure
    assert len(result.individual_results) == 2
    assert result.all_passed is False
    assert result.individual_results[0].passed is True
    assert result.individual_results[1].passed is False


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_with_file_parameters(mock_run_command, mock_client, test_case_with_file, sample_cif_output):
    """Test running a test case with file parameters."""
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_case(mock_client, test_case_with_file)

    # Verify the command was called
    assert mock_run_command.called
    assert result.all_passed is True


# Tests for run_test_suite


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_suite_single_case(mock_run_command, mock_client, test_suite_simple, sample_cif_output):
    """Test running a test suite with a single test case."""
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_suite(mock_client, test_suite_simple)

    # Verify the result
    assert isinstance(result, TestSuiteResult)
    assert result.application_slug == "test_app"
    assert result.all_passed is True
    assert len(result.test_results) == 1
    assert all(isinstance(r, TestCaseResult) for r in result.test_results)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_suite_multiple_cases(mock_run_command, mock_client, test_suite_multiple, sample_cif_output):
    """Test running a test suite with multiple test cases."""
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_suite(mock_client, test_suite_multiple)

    # Verify the result
    assert isinstance(result, TestSuiteResult)
    assert result.application_slug == "test_app"
    assert len(result.test_results) == 2

    # Verify each command was called
    assert mock_run_command.call_count == 2


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_suite_all_pass(mock_run_command, mock_client, test_suite_multiple, sample_cif_output):
    """Test a test suite where all test cases pass."""
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_suite(mock_client, test_suite_multiple)

    # All should pass
    assert result.all_passed is True
    assert all(tc.all_passed for tc in result.test_results)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_suite_one_failure(mock_run_command, mock_client, test_suite_multiple):
    """Test a test suite where one test case fails."""
    # First call succeeds, second fails
    mock_run_command.side_effect = [
        CommandRunResult(status="successful", result_cif="data_example\n_atom.type C\n", status_events=[]),
        CommandRunResult(status="failed", result_cif=None, status_events=["Error"]),
    ]

    result = run_test_suite(mock_client, test_suite_multiple)

    # Suite should fail if any test fails
    assert result.all_passed is False
    assert result.test_results[0].all_passed is True
    assert result.test_results[1].all_passed is False


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_suite_all_fail(mock_run_command, mock_client, test_suite_multiple):
    """Test a test suite where all test cases fail."""
    mock_run_command.return_value = CommandRunResult(status="failed", result_cif=None, status_events=["Error"])

    result = run_test_suite(mock_client, test_suite_multiple)

    # All should fail
    assert result.all_passed is False
    assert all(not tc.all_passed for tc in result.test_results)


# Tests for dataclass structures


def test_test_case_result_structure():
    """Test the TestCaseResult dataclass structure."""
    individual_results = [IndividualTestResult(test_case_name="test1", passed=True, log="Success")]

    result = TestCaseResult(test_case_name="test1", all_passed=True, individual_results=individual_results)

    assert result.test_case_name == "test1"
    assert result.all_passed is True
    assert result.individual_results == individual_results


def test_test_suite_result_structure():
    """Test the TestSuiteResult dataclass structure."""
    test_results = [TestCaseResult(test_case_name="test1", all_passed=True, individual_results=[])]

    result = TestSuiteResult(application_slug="app", all_passed=True, test_results=test_results)

    assert result.application_slug == "app"
    assert result.all_passed is True
    assert result.test_results == test_results


# Edge cases
@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_with_custom_upload_filename(
    mock_run_command, mock_client, test_case_with_file_custom_filename, sample_cif_output
):
    """Test that test case with custom upload_filename runs correctly."""
    # Mock the command to return success with CIF output
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif="data_test\n_result.status ok\n", status_events=[]
    )

    result = run_test_case(mock_client, test_case_with_file_custom_filename)

    # Verify the test case ran
    assert isinstance(result, TestCaseResult)
    assert result.test_case_name == "test_with_custom_filename"

    # Verify run_qcrbox_command was called with correct parameters
    mock_run_command.assert_called_once()
    call_args = mock_run_command.call_args

    # Check that the file parameter with custom upload_filename was passed
    params = call_args[0][4]  # 5th argument is qcrbox_command_parameters
    file_param = None
    for param in params:
        if isinstance(param, QCrBoxFileParameter):
            file_param = param
            break

    assert file_param is not None
    assert file_param.upload_filename == "custom_name.inp"


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_empty_cif_output(mock_run_command, mock_client, simple_test_case):
    """Test handling of empty CIF output."""
    mock_run_command.return_value = CommandRunResult(status="successful", result_cif="", status_events=[])

    # Empty CIF causes parser error - this is expected behavior
    with pytest.raises(AttributeError):
        run_test_case(mock_client, simple_test_case)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_null_cif_output(mock_run_command, mock_client, simple_test_case):
    """Test handling of None CIF output when status is successful."""
    mock_run_command.return_value = CommandRunResult(status="successful", result_cif=None, status_events=[])

    # None CIF gets converted to empty string, which causes parser error
    with pytest.raises(AttributeError):
        run_test_case(mock_client, simple_test_case)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_malformed_cif(mock_run_command, mock_client, simple_test_case):
    """Test handling of malformed CIF output."""
    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif="This is not valid CIF format", status_events=[]
    )

    # Malformed CIF causes parser error (StarError from CifFile library)
    with pytest.raises(StarError):
        run_test_case(mock_client, simple_test_case)


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_timeout_handling(mock_run_command, mock_client, simple_test_case):
    """Test handling of command timeout."""
    mock_run_command.return_value = CommandRunResult(
        status="timeout", result_cif=None, status_events=["Error: command timed out"]
    )

    result = run_test_case(mock_client, simple_test_case)

    # Verify the result indicates failure due to timeout
    assert isinstance(result, TestCaseResult)
    assert result.test_case_name == "test_simple"
    assert result.all_passed is False
    assert len(result.individual_results) == 1

    individual_result = result.individual_results[0]
    assert individual_result.passed is False
    assert "Command execution failed" in individual_result.log


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_passes_timeout(mock_run_command, mock_client, simple_test_case, sample_cif_output):
    """Test that timeout_seconds from test case is passed to run_qcrbox_command."""
    # Set a custom timeout on the test case
    simple_test_case.timeout_seconds = 123.45

    mock_run_command.return_value = CommandRunResult(
        status="successful", result_cif=sample_cif_output, status_events=[]
    )

    result = run_test_case(mock_client, simple_test_case)

    # Verify run_qcrbox_command was called with the timeout
    mock_run_command.assert_called_once_with(
        mock_client,
        "process",
        "test_app",
        "1.0.0",
        simple_test_case.qcrbox_command_parameters,
        123.45,  # timeout_seconds should be passed
    )
    assert result.all_passed is True


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_status_expected_success(mock_run_command, mock_client):
    """Test handling of StatusExpectedResult when status matches."""
    test_case = TestCase(
        name="test_status",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[],
        expected_results=[
            StatusExpectedResult(expected="successful"),
        ],
    )

    mock_run_command.return_value = CommandRunResult(status="successful", result_cif="data_test\n", status_events=[])

    result = run_test_case(mock_client, test_case)

    assert result.all_passed is True
    assert len(result.individual_results) == 1
    assert result.individual_results[0].passed is True
    assert result.individual_results[0].log is None


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_status_expected_failure(mock_run_command, mock_client):
    """Test handling of StatusExpectedResult when status doesn't match."""
    test_case = TestCase(
        name="test_status_fail",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[],
        expected_results=[
            StatusExpectedResult(expected="successful"),
        ],
    )

    mock_run_command.return_value = CommandRunResult(status="failed", result_cif=None, status_events=["error"])

    result = run_test_case(mock_client, test_case)

    assert result.all_passed is False
    assert len(result.individual_results) == 1
    assert result.individual_results[0].passed is False
    assert "Expected status 'successful', got 'failed'" in result.individual_results[0].log


@patch("qcrbox_cmd_tester.run_suite.run_qcrbox_command")
def test_run_test_case_status_expected_failed(mock_run_command, mock_client):
    """Test handling of StatusExpectedResult expecting failed status."""
    test_case = TestCase(
        name="test_expect_failed",
        qcrbox_application_slug="test_app",
        qcrbox_application_version="1.0.0",
        qcrbox_command_name="process",
        qcrbox_command_parameters=[],
        expected_results=[
            StatusExpectedResult(expected="failed"),
        ],
    )

    mock_run_command.return_value = CommandRunResult(status="failed", result_cif=None, status_events=["Expected error"])

    result = run_test_case(mock_client, test_case)

    assert result.all_passed is True
    assert len(result.individual_results) == 1
    assert result.individual_results[0].passed is True
    assert result.individual_results[0].test_case_name == "status_failed"
