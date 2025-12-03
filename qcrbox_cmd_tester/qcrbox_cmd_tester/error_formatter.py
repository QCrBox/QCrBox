"""
Error formatting utilities for YAML validation errors.

Provides human-readable error messages with rich formatting for YAML parsing
and validation errors, including context about test cases and expected results.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

console = Console()


def format_yaml_error(error: Exception, yaml_file: Path, yaml_data: dict | None = None) -> None:
    """
    Format and display YAML loading errors nicely using rich.

    Args:
        error: The exception that was raised
        yaml_file: Path to the YAML file that caused the error
        yaml_data: Parsed YAML data (if available) for context in validation errors
    """
    console.print()

    if isinstance(error, yaml.YAMLError):
        _format_yaml_syntax_error(error, yaml_file)
    elif isinstance(error, ValidationError):
        _format_validation_error(error, yaml_file, yaml_data)
    elif isinstance(error, FileNotFoundError):
        _format_file_not_found_error(error, yaml_file)
    elif isinstance(error, PermissionError):
        _format_permission_error(yaml_file)
    else:
        _format_generic_error(error, yaml_file)

    console.print()


def _format_yaml_syntax_error(error: yaml.YAMLError, yaml_file: Path) -> None:
    """Format YAML parsing/syntax errors."""
    console.print(
        Panel(
            f"[red bold]YAML Parsing Error[/red bold]\n\n"
            f"Failed to parse YAML file: [cyan]{yaml_file}[/cyan]\n\n"
            f"[yellow]Error details:[/yellow]\n{str(error)}",
            title="❌ Invalid YAML Syntax",
            border_style="red",
        )
    )


def _format_file_not_found_error(error: FileNotFoundError, yaml_file: Path) -> None:
    """Format file not found errors."""
    missing_file = Path(error.filename) if error.filename else None

    if missing_file and missing_file.resolve() != yaml_file.resolve():
        message = (
            f"[red bold]File Not Found[/red bold]\n\n"
            f"The test suite [cyan]{yaml_file}[/cyan] references a file that could not be found:\n"
            f"[yellow]{missing_file}[/yellow]\n\n"
            f"Please check that the referenced file exists and the path is correct relative to the test suite."
        )
    else:
        message = (
            f"[red bold]File Not Found[/red bold]\n\n"
            f"Could not find file: [cyan]{yaml_file}[/cyan]\n\n"
            f"Please check that the file path is correct."
        )

    console.print(
        Panel(
            message,
            title="❌ File Not Found",
            border_style="red",
        )
    )


def _format_permission_error(yaml_file: Path) -> None:
    """Format permission denied errors."""
    console.print(
        Panel(
            f"[red bold]Permission Denied[/red bold]\n\n"
            f"Cannot read file: [cyan]{yaml_file}[/cyan]\n\n"
            f"Please check file permissions.",
            title="❌ Permission Error",
            border_style="red",
        )
    )


def _format_generic_error(error: Exception, yaml_file: Path) -> None:
    """Format generic/unexpected errors."""
    console.print(
        Panel(
            f"[red bold]Error Loading Test Suite[/red bold]\n\n"
            f"File: [cyan]{yaml_file}[/cyan]\n\n"
            f"[yellow]Error:[/yellow] {str(error)}",
            title="❌ Unexpected Error",
            border_style="red",
        )
    )


def _format_validation_error(error: ValidationError, yaml_file: Path, yaml_data: dict | None) -> None:
    """
    Format Pydantic validation errors with detailed context.

    Args:
        error: The ValidationError from Pydantic
        yaml_file: Path to the YAML file
        yaml_data: Parsed YAML data for extracting test case names
    """
    error_count = error.error_count()
    error_s = "error" if error_count == 1 else "errors"

    console.print(
        Panel(
            f"[red bold]YAML Validation Error[/red bold]\n\n"
            f"The YAML file [cyan]{yaml_file.name}[/cyan] has {error_count} validation {error_s}.\n"
            f"Please check that your YAML structure matches the expected format.",
            title=f"❌ {error_count} Validation {error_s.title()} Found",
            border_style="red",
        )
    )

    # Display each validation error
    for i, err in enumerate(error.errors(), 1):
        location = _build_readable_location(err["loc"], yaml_data)
        msg = err["msg"]
        error_type = err["type"]

        console.print(f"\n[bold]Error {i}:[/bold]")
        console.print(f"  [cyan]Location:[/cyan] {location}")
        console.print(f"  [yellow]Message:[/yellow] {msg}")
        console.print(f"  [dim]Type: {error_type}[/dim]")

        # Show the input value if available and not too large
        if "input" in err and err["input"] is not None:
            input_str = str(err["input"])
            if len(input_str) < 100:
                console.print(f"  [magenta]Input:[/magenta] {input_str}")

    console.print("\n[dim]For more information on the YAML format, see the documentation.[/dim]")


def _build_readable_location(location_tuple: tuple, yaml_data: dict | None) -> str:
    """
    Build a human-readable location string from Pydantic's error location tuple.

    Converts error locations like (0, 'status', 'expected') into readable paths like:
    "Test case 0: test_name → expected value 0: status → expected"

    Args:
        location_tuple: Pydantic's error location tuple
        yaml_data: Parsed YAML data for context

    Returns
    -------
        Human-readable location string

    """
    location_parts = [str(loc) for loc in location_tuple]
    readable_location = []
    test_cases = yaml_data.get("test_cases", []) if yaml_data else []

    idx = 0
    current_test_case = None

    while idx < len(location_parts):
        part = location_parts[idx]

        # Check if this is a numeric index at the start
        if idx == 0 and part.isdigit():
            num_idx = int(part)

            # Determine if this is a test_cases index or expected_results index
            # by looking ahead for discriminator keywords
            has_discriminator = _has_result_type_discriminator(location_parts, idx + 1)

            if has_discriminator:
                # This is an expected_results index
                test_case_info = _format_test_case_context(test_cases)
                if test_case_info:
                    readable_location.append(test_case_info)
                    current_test_case = test_cases[0] if test_cases else None

                # Format the expected result info
                result_info = _format_expected_result(location_parts, idx, current_test_case)
                readable_location.append(result_info["text"])
                idx = result_info["next_idx"]
                continue
            else:
                # This is a test_cases index
                test_case_info = _format_test_case_by_index(test_cases, num_idx)
                if test_case_info:
                    readable_location.append(test_case_info)
                    current_test_case = test_cases[num_idx] if num_idx < len(test_cases) else None
                idx += 1
                continue

        # Handle discriminator values that appear after test case
        if _is_result_type_discriminator(part) and current_test_case:
            result_info = _format_expected_result_from_discriminator(location_parts, idx, current_test_case)
            readable_location.append(result_info["text"])
            idx = result_info["next_idx"]
            continue

        # For other parts, just add them as-is
        readable_location.append(part)
        idx += 1

    return " → ".join(readable_location)


def _has_result_type_discriminator(location_parts: list[str], idx: int) -> bool:
    """Check if the location at idx contains a result_type discriminator."""
    if idx >= len(location_parts):
        return False
    return location_parts[idx] in ["status", "cif_value", "cif_loop_value"]


def _is_result_type_discriminator(part: str) -> bool:
    """Check if a part is a result_type discriminator."""
    return part in ["status", "cif_value", "cif_loop_value"]


def _is_test_type_discriminator(part: str) -> bool:
    """Check if a part is a test_type discriminator."""
    return part in ["match", "non-match", "within", "contain", "missing", "present"]


def _format_test_case_context(test_cases: list) -> str | None:
    """
    Format test case context when we know errors are in first test.

    Args:
        test_cases: List of test case dictionaries from YAML

    Returns
    -------
        Formatted string or None if no test cases

    """
    if not test_cases:
        return None

    test_case = test_cases[0]
    test_name = test_case.get("name", "test_0") if isinstance(test_case, dict) else "test_0"
    return f"Test case 0: {test_name}"


def _format_test_case_by_index(test_cases: list, index: int) -> str | None:
    """
    Format test case information by index.

    Args:
        test_cases: List of test case dictionaries from YAML
        index: Index of the test case

    Returns
    -------
        Formatted string or None if index out of range

    """
    if index >= len(test_cases):
        return None

    test_case = test_cases[index]
    test_name = test_case.get("name", f"test_{index}") if isinstance(test_case, dict) else f"test_{index}"
    return f"Test case {index}: {test_name}"


def _format_expected_result(location_parts: list[str], idx: int, test_case: dict | None) -> dict:
    """
    Format expected result information from location parts.

    Args:
        location_parts: List of location parts from Pydantic error
        idx: Current index in location_parts (should be the result index)
        test_case: Current test case dictionary for context

    Returns
    -------
        Dictionary with 'text' (formatted string) and 'next_idx' (next index to process)

    """
    num_idx = int(location_parts[idx])
    result_type = location_parts[idx + 1]
    test_type = None

    # Check for test_type (for cif_value and cif_loop_value)
    if idx + 2 < len(location_parts) and result_type in ["cif_value", "cif_loop_value"]:
        potential_test_type = location_parts[idx + 2]
        if _is_test_type_discriminator(potential_test_type):
            test_type = potential_test_type
            text = f"expected value {num_idx}: {result_type}({test_type})"
            return {"text": text, "next_idx": idx + 3}

    # Status or result_type without test_type
    text = f"expected value {num_idx}: {result_type}"
    return {"text": text, "next_idx": idx + 2}


def _format_expected_result_from_discriminator(location_parts: list[str], idx: int, test_case: dict) -> dict:
    """
    Format expected result when starting from a discriminator value.

    Args:
        location_parts: List of location parts from Pydantic error
        idx: Current index in location_parts (should be the discriminator)
        test_case: Current test case dictionary for finding result index

    Returns
    -------
        Dictionary with 'text' (formatted string) and 'next_idx' (next index to process)

    """
    result_type = location_parts[idx]
    test_type = None
    result_index = None

    # Check for test_type
    if idx + 1 < len(location_parts) and result_type in ["cif_value", "cif_loop_value"]:
        potential_test_type = location_parts[idx + 1]
        if _is_test_type_discriminator(potential_test_type):
            test_type = potential_test_type
            # Find index in expected_results
            result_index = _find_result_index(test_case, result_type, test_type)
            if result_index is not None:
                text = f"expected value {result_index}: {result_type}({test_type})"
            else:
                text = f"expected value: {result_type}({test_type})"
            return {"text": text, "next_idx": idx + 2}

    # Status or no test_type - find the result index
    result_index = _find_result_index(test_case, result_type, None)
    if result_index is not None:
        text = f"expected value {result_index}: {result_type}"
    else:
        text = f"expected value: {result_type}"
    return {"text": text, "next_idx": idx + 1}


def _find_result_index(test_case: dict, result_type: str, test_type: str | None) -> int | None:
    """
    Find the index of an expected result matching the given types.

    Args:
        test_case: Test case dictionary
        result_type: Result type to match (status, cif_value, cif_loop_value)
        test_type: Test type to match (match, within, etc.) or None

    Returns
    -------
        Index of matching result or None if not found

    """
    expected_results = test_case.get("expected_results", [])
    for idx, res in enumerate(expected_results):
        if not isinstance(res, dict):
            continue
        if res.get("result_type") != result_type:
            continue
        if test_type is not None and res.get("test_type") != test_type:
            continue
        return idx
    return None
