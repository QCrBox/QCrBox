"""Tests for the models module."""

import tempfile
from pathlib import Path

import pytest

from qcrbox_cmd_tester.models import (
    QCrBoxFileParameter,
    QCrBoxParameter,
    TestCase,
    TestSuite,
)
from qcrbox_cmd_tester.models.expected_values import (
    CifEntryMatchExpectedResult,
)

# Tests for QCrBoxParameter.from_yaml_dict


def test_parameter_from_yaml_dict_simple():
    """Test creating a simple parameter from YAML dict."""
    data = {"name": "param1", "value": "test_value", "type": "str"}
    param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

    assert isinstance(param, QCrBoxParameter)
    assert param.name == "param1"
    assert param.value == "test_value"


def test_parameter_from_yaml_dict_internal_file():
    """Test creating an internal file parameter from YAML dict."""
    cif_content = "data_test\n_atom.type C\n"
    data = {"name": "input_cif", "value": cif_content, "type": "internal_file"}
    param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

    assert isinstance(param, QCrBoxFileParameter)
    assert param.name == "input_cif"
    assert param.cif_content == cif_content


def test_parameter_from_yaml_dict_external_file():
    """Test creating an external file parameter from YAML dict."""
    # Create a temporary CIF file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False) as f:
        f.write("data_test\n_atom.type C\n")
        temp_file = Path(f.name)

    try:
        data = {"name": "input_cif", "value": str(temp_file), "type": "external_file"}
        param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

        assert isinstance(param, QCrBoxFileParameter)
        assert param.name == "input_cif"
        assert "data_test" in param.cif_content
    finally:
        temp_file.unlink()


def test_parameter_from_yaml_dict_external_file_relative_path():
    """Test creating an external file parameter with relative path."""
    # Create a temporary directory and file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cif_file = tmpdir / "test.cif"
        cif_file.write_text("data_test\n_atom.type N\n")

        data = {
            "name": "input_cif",
            "value": "test.cif",  # Relative path
            "type": "external_file",
        }
        param = QCrBoxParameter.from_yaml_dict(data, base_folder=tmpdir)

        assert isinstance(param, QCrBoxFileParameter)
        assert "data_test" in param.cif_content
        assert "_atom.type N" in param.cif_content


# Tests for QCrBoxFileParameter


def test_file_parameter_from_internal_file():
    """Test creating QCrBoxFileParameter from internal file content."""
    content = "data_example\n_test 1\n"
    param = QCrBoxFileParameter.from_internal_file(content, "test_param")

    assert param.name == "test_param"
    assert param.cif_content == content


def test_file_parameter_from_external_file():
    """Test creating QCrBoxFileParameter from external file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False) as f:
        f.write("data_external\n_value 42\n")
        temp_file = Path(f.name)

    try:
        param = QCrBoxFileParameter.from_external_file(temp_file, "external_param", base_folder=Path("."))

        assert param.name == "external_param"
        assert "data_external" in param.cif_content
    finally:
        temp_file.unlink()


def test_file_parameter_upload_filename_default():
    """Test that upload_filename defaults to None."""
    content = "data_test\n"
    param = QCrBoxFileParameter.from_internal_file(content, "test_param")

    assert param.upload_filename is None


def test_file_parameter_upload_filename_custom():
    """Test setting custom upload_filename."""
    content = "data_test\n"
    param = QCrBoxFileParameter.from_internal_file(content, "test_param", upload_filename="custom.inp")

    assert param.upload_filename == "custom.inp"


def test_file_parameter_from_external_file_with_upload_filename():
    """Test creating QCrBoxFileParameter from external file with custom upload_filename."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write("test input file\n")
        temp_file = Path(f.name)

    try:
        param = QCrBoxFileParameter.from_external_file(
            temp_file, "input_file", base_folder=Path("."), upload_filename="custom_name.inp"
        )

        assert param.name == "input_file"
        assert param.upload_filename == "custom_name.inp"
        assert "test input file" in param.cif_content
    finally:
        temp_file.unlink()


def test_parameter_from_yaml_dict_external_file_with_upload_filename():
    """Test creating an external file parameter from YAML dict with upload_filename."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("constraint file content\n")
        temp_file = Path(f.name)

    try:
        data = {
            "name": "constraint_file",
            "value": str(temp_file),
            "type": "external_file",
            "upload_filename": "CONSTRAIN.txt",
        }
        param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

        assert isinstance(param, QCrBoxFileParameter)
        assert param.name == "constraint_file"
        assert param.upload_filename == "CONSTRAIN.txt"
        assert "constraint file content" in param.cif_content
    finally:
        temp_file.unlink()


def test_parameter_from_yaml_dict_internal_file_with_upload_filename():
    """Test creating an internal file parameter from YAML dict with upload_filename."""
    file_content = "internal file data\n"
    data = {
        "name": "data_file",
        "value": file_content,
        "type": "internal_file",
        "upload_filename": "data.dat",
    }
    param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

    assert isinstance(param, QCrBoxFileParameter)
    assert param.name == "data_file"
    assert param.upload_filename == "data.dat"
    assert param.cif_content == file_content


def test_parameter_from_yaml_dict_external_file_without_upload_filename():
    """Test that upload_filename is optional and defaults to None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cif", delete=False) as f:
        f.write("data_test\n")
        temp_file = Path(f.name)

    try:
        data = {
            "name": "input_cif",
            "value": str(temp_file),
            "type": "external_file",
            # No upload_filename specified
        }
        param = QCrBoxParameter.from_yaml_dict(data, base_folder=Path("."))

        assert isinstance(param, QCrBoxFileParameter)
        assert param.upload_filename is None
    finally:
        temp_file.unlink()


# Tests for TestCase validators


def test_test_case_must_have_expected_results():
    """Test that TestCase must have at least one expected result."""
    with pytest.raises(ValueError, match="at least one expected result"):
        TestCase(
            name="test1",
            qcrbox_application_slug="app",
            qcrbox_application_version="1.0",
            qcrbox_command_name="cmd",
            qcrbox_command_parameters=[],
            expected_results=[],  # Empty - should fail
        )


def test_test_case_duplicate_parameter_names():
    """Test that TestCase validates unique parameter names."""
    with pytest.raises(ValueError, match="Duplicate parameter names"):
        TestCase(
            name="test1",
            qcrbox_application_slug="app",
            qcrbox_application_version="1.0",
            qcrbox_command_name="cmd",
            qcrbox_command_parameters=[
                QCrBoxParameter(name="param1", value="value1"),
                QCrBoxParameter(name="param1", value="value2"),  # Duplicate!
            ],
            expected_results=[CifEntryMatchExpectedResult(cif_entry_name="_test", expected_value="test")],
        )


# Tests for TestSuite


def test_test_suite_from_yaml_file():
    """Test loading TestSuite from a YAML file."""
    yaml_content = """
application_slug: test_app
application_version: 1.0.0
description: Test suite
test_cases:
  - name: test1
    command_name: process
    timeout_seconds: 123
    input_parameters: []
    expected_results:
      - result_type: cif_value
        test_type: match
        cif_entry_name: _atom.type
        expected_value: C
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_file = Path(f.name)

    try:
        suite = TestSuite.from_yaml_file(temp_file)

        assert suite.application_slug == "test_app"
        assert suite.application_version == "1.0.0"
        assert suite.description == "Test suite"
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "test1"
        assert suite.tests[0].timeout_seconds == 123
    finally:
        temp_file.unlink()


def test_test_suite_must_have_tests():
    """Test that TestSuite must have at least one test."""
    with pytest.raises(ValueError, match="at least one test"):
        TestSuite(
            application_slug="app",
            application_version="1.0",
            tests=[],  # Empty - should fail
        )


def test_test_suite_duplicate_test_names():
    """Test that TestSuite validates unique test names."""
    test1 = TestCase(
        name="test1",
        qcrbox_application_slug="app",
        qcrbox_application_version="1.0",
        qcrbox_command_name="cmd",
        qcrbox_command_parameters=[],
        expected_results=[CifEntryMatchExpectedResult(cif_entry_name="_test", expected_value="test")],
    )

    test2 = TestCase(
        name="test1",  # Duplicate name!
        qcrbox_application_slug="app",
        qcrbox_application_version="1.0",
        qcrbox_command_name="cmd2",
        qcrbox_command_parameters=[],
        expected_results=[CifEntryMatchExpectedResult(cif_entry_name="_test", expected_value="test")],
    )

    with pytest.raises(ValueError, match="Duplicate test names"):
        TestSuite(application_slug="app", application_version="1.0", tests=[test1, test2])


def test_test_suite_to_dict():
    """Test converting TestSuite to dictionary."""
    test_case = TestCase(
        name="test1",
        qcrbox_application_slug="app",
        qcrbox_application_version="1.0",
        qcrbox_command_name="cmd",
        qcrbox_command_parameters=[],
        expected_results=[CifEntryMatchExpectedResult(cif_entry_name="_test", expected_value="test")],
    )

    suite = TestSuite(application_slug="app", application_version="1.0", tests=[test_case])

    result = suite.to_dict()

    assert isinstance(result, dict)
    assert result["application_slug"] == "app"
    assert result["application_version"] == "1.0"
    assert len(result["tests"]) == 1
    assert result["tests"][0]["name"] == "test1"


def test_test_suite_to_json_file():
    """Test exporting TestSuite to JSON file."""
    test_case = TestCase(
        name="test1",
        qcrbox_application_slug="app",
        qcrbox_application_version="1.0",
        qcrbox_command_name="cmd",
        qcrbox_command_parameters=[],
        expected_results=[CifEntryMatchExpectedResult(cif_entry_name="_test", expected_value="test")],
    )

    suite = TestSuite(application_slug="app", application_version="1.0", tests=[test_case])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_file = Path(f.name)

    try:
        suite.to_json_file(str(temp_file))

        # Verify file was created and contains valid JSON
        import json

        with open(temp_file) as f:
            data = json.load(f)

        assert data["application_slug"] == "app"
        assert len(data["tests"]) == 1
    finally:
        temp_file.unlink()
