"""Integration test with the actual YAML file."""

from pathlib import Path

import yaml

from qcrbox_cmd_tester.models.expected_values import ExpectedResultTypeAdapter


def test_parse_all_results_from_yaml():
    """Test that all expected_results from test_all_result_types.yaml parse correctly."""
    yaml_path = Path(__file__).parent / "test_all_result_types.yaml"

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    # Get all expected_results from the first test case
    test_case = data["test_cases"][0]

    expected_results = test_case["expected_results"]

    # Parse each expected result
    parsed_results = []
    for result_data in expected_results:
        result = ExpectedResultTypeAdapter.validate_python(result_data)
        parsed_results.append(result)

    # Verify we parsed them all
    assert len(parsed_results) == len(expected_results)
    assert len(parsed_results) == 19  # From the YAML file (added multi-row lookup test)

    # Verify various types are present
    result_types = [type(r).__name__ for r in parsed_results]

    assert "StatusExpectedResult" in result_types
    assert "CifEntryMatchExpectedResult" in result_types
    assert "CifEntryNonMatchExpectedResult" in result_types
    assert "CifEntryWithinExpectedResult" in result_types
    assert "CifEntryContainExpectedResult" in result_types
    assert "CifEntryMissingExpectedResult" in result_types
    assert "CifEntryPresentExpectedResult" in result_types
    assert "CifLoopEntryMatchExpectedResult" in result_types
    assert "CifLoopEntryNonMatchExpectedResult" in result_types
    assert "CifLoopEntryWithinExpectedResult" in result_types
    assert "CifLoopEntryContainExpectedResult" in result_types
    assert "CifLoopEntryMissingExpectedResult" in result_types
    assert "CifLoopEntryPresentExpectedResult" in result_types

    print(f"\nSuccessfully parsed {len(parsed_results)} expected results")
    for i, result in enumerate(parsed_results, 1):
        print(f"  {i:2d}. {type(result).__name__}")
