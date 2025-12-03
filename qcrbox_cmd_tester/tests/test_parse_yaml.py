"""Test parsing YAML to test suite models."""

from pathlib import Path

import pytest

from qcrbox_cmd_tester.models import QCrBoxFileParameter, QCrBoxParameter, TestCase, TestSuite


@pytest.fixture
def test_yaml_dict():
    """Sample YAML dictionary for testing."""
    return {
        "application_slug": "TestApp",
        "application_version": "0.1.0",
        "description": "A test application",
        "test_cases": [
            {
                "name": "Test1",
                "description": "First test case",
                "command_name": "Cmd1",
                "input_parameters": [
                    {"name": "param1", "value": "value1", "type": "str"},
                    {"name": "param2", "value": "something_in_here", "type": "internal_file"},
                ],
                "expected_results": [
                    {"result_type": "status", "expected": "successful"},
                ],
            }
        ],
    }


def test_create_test_suite_from_yaml(test_yaml_dict):
    """Test creating a test suite from YAML dictionary."""
    test_suite = TestSuite.from_yaml_dict(test_yaml_dict, base_folder=Path("."))

    assert isinstance(test_suite, TestSuite)
    assert test_suite.application_slug == "TestApp"
    assert len(test_suite.tests) == 1

    test_case = test_suite.tests[0]
    assert isinstance(test_case, TestCase)
    assert test_case.name == "Test1"
    assert len(test_case.qcrbox_command_parameters) == 2

    param1 = test_case.qcrbox_command_parameters[0]
    assert isinstance(param1, QCrBoxParameter)
    assert param1.name == "param1"
    assert param1.value == "value1"

    param2 = test_case.qcrbox_command_parameters[1]
    assert isinstance(param2, QCrBoxFileParameter)
    assert param2.name == "param2"
    assert param2.cif_content == "something_in_here"
