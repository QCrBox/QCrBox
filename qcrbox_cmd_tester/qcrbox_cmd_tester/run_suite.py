"""
Test execution framework for running test suites.

This module orchestrates the execution of test suites and test cases,
delegating QCrBox-specific operations to qcrbox_client.py.
"""

from dataclasses import dataclass

from qcrboxapiclient.client import Client

from qcrbox_cmd_tester.models.expected_values import StatusExpectedResult

from .models import TestCase, TestSuite
from .qcrbox_client import run_qcrbox_command
from .test_implementations import IndividualTestResult, check_result


@dataclass
class TestCaseResult:
    """Result of executing a single test case."""

    test_case_name: str
    all_passed: bool
    individual_results: list[IndividualTestResult]
    result_cif: str | None = None  # Store the CIF result for debugging
    command_status: str | None = None  # Store command status


@dataclass
class TestSuiteResult:
    """Result of executing an entire test suite."""

    application_slug: str
    all_passed: bool
    test_results: list[TestCaseResult]


def run_test_case(client: Client, test_case: TestCase) -> TestCaseResult:
    """
    Execute a single test case against QCrBox.

    Args:
        client: QCrBox API client
        test_case: The test case to execute

    Returns
    -------
        TestCaseResult with test outcomes

    """
    command_result = run_qcrbox_command(
        client,
        test_case.qcrbox_command_name,
        test_case.qcrbox_application_slug,
        test_case.qcrbox_application_version,
        test_case.qcrbox_command_parameters,
        test_case.timeout_seconds,
    )

    # Check expected results against command output
    individual_results = []
    all_passed = True
    for expected_result in test_case.expected_results:
        if isinstance(expected_result, StatusExpectedResult):
            result = IndividualTestResult(
                test_case_name=f"status_{expected_result.expected}",
                passed=command_result.status == expected_result.expected,
                log=None
                if command_result.status == expected_result.expected
                else f"Expected status '{expected_result.expected}', got '{command_result.status}'",
            )
            individual_results.append(result)
            if not result.passed:
                all_passed = False
            continue

        if command_result.status != "successful":
            individual_results.append(
                IndividualTestResult(
                    test_case_name=test_case.name,
                    passed=False,
                    log=(
                        "Command execution failed; cannot check expected result of type "
                        f"{type(expected_result).__name__}"
                    ),
                )
            )
            all_passed = False
            continue

        result = check_result(
            cif_text=command_result.result_cif if command_result.result_cif is not None else "",
            expected_result=expected_result,
        )
        individual_results.append(result)
        if not result.passed:
            all_passed = False

    return TestCaseResult(
        test_case_name=test_case.name,
        all_passed=all_passed,
        individual_results=individual_results,
        result_cif=command_result.result_cif,
        command_status=command_result.status,
    )


def run_test_suite(client: Client, test_suite: TestSuite) -> TestSuiteResult:
    """
    Execute all test cases in a test suite.

    Args:
        client: QCrBox API client
        test_suite: The test suite to execute

    Returns
    -------
        TestSuiteResult with all test case results

    """
    case_results = [run_test_case(client, test_case) for test_case in test_suite.tests]
    return TestSuiteResult(
        application_slug=test_suite.application_slug,
        all_passed=all(case.all_passed for case in case_results),
        test_results=case_results,
    )
