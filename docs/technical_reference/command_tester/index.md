# QCrBox Command Tester

**A comprehensive testing framework for QCrBox applications and commands**

QCrBox Command Tester is a command-line tool that enables automated testing of crystallographic software applications integrated with the QCrBox platform. It provides a YAML-based test specification format that allows you to define test suites, execute commands, and validate results against expected outcomes.

**Quick Links:**
- [Test Suite Format Specification](test_suite_format.md)
- [CLI Reference](cli_reference.md)

## Overview

QCrBox Command Tester allows you to:

- **Define test suites** for QCrBox using human-readable YAML files
- **Validate CIF outputs** against expected values with multiple assertion types
- **Run tests** for individual files or entire test suite directories
- **Debug failures** with detailed logging and CIF file outputs

## Architecture

```text
+-----------------------+
| YAML Test Definitions |
+-----------------------+
          |
          v
+-----------------------+
|     Test Runner       |
|    (qcrbox-test)      |
+-----------------------+
          |
          v
+-----------------------+
|   QCrBox API Client   |
+-----------------------+
          |
          v
+-----------------------+
|   QCrBox API Server   |
+-----------------------+
          |
          v
+-----------------------+
|     Containerized     |
|     Applications      |
+-----------------------+
```

## Key Features

### YAML-Based Test Definitions

Write tests in a clear, declarative format that doesn't require programming knowledge. See [Test Suite Format](test_suite_format.md) for details.

### Comprehensive Validation

Test various aspects of command execution and CIF outputs:

- **Status checks**: Verify successful/failed execution
- **CIF value tests**: Match, range, substring, presence/absence checks
- **CIF loop tests**: Validate values in specific rows of CIF loops
- **Numerical tolerances**: Test floating-point values within acceptable ranges

### Debug Mode

When tests fail, debug mode saves:

- Detailed summary logs with failure information
- Actual CIF output files for comparison
- Command execution status and error messages

All debug information is organized in timestamped directories under `qcrbox_cmd_tester/logs/` (or a custom directory specified via `--log-dir`).

## Project Structure

Tests are located alongside the application definitions in the `services/applications` directory:

```
services/applications/
├── my_app/
│   ├── config_my_app.yaml
│   ├── test_my_app.yaml   # Test suite for this application
│   └── test_cif_files/    # Test data files
│       ├── structure1.cif
│       └── structure2.cif
└── README.md

qcrbox_cmd_tester/
└── logs/                  # Debug output (default location)
    └── 20251027_143022_olex2/
        ├── summary.log
        └── test_result.cif
```

## Detailed Documentation

- [CLI Reference](cli_reference.md) - Detailed guide on running tests, command-line arguments, and the `init` command.
- [Test Suite Format](test_suite_format.md) - Complete specification of the YAML test format and available assertions.

## License

QCrBox Command Tester is released under the [MPL-2.0 License](https://mozilla.org/MPL/2.0/).
