# CLI Reference

This guide covers the command-line interface for `qcrbox-test`.

## Basic Usage

### Running All Tests

By default, the tester looks for test files matching `test_*.yaml` in the `services/applications/` directory structure:

```bash
qcrbox-test
```

This will:
- Recursively find all `test_*.yaml` and `test_*.yml` files in `services/applications/`
- Execute each test suite sequentially
- Display results for each test case
- Show a summary at the end

### Running Tests from a Custom Directory

Specify a different directory containing test suites:

```bash
qcrbox-test --test-location services/applications/my_app/
```

### Running a Single Test File

Run a specific test suite file:

```bash
qcrbox-test --test-location services/applications/my_app/test_my_app.yaml
```

## Initializing a Test Suite

You can generate a new test suite based on an existing application configuration and a valid CIF file. This is useful for bootstrapping a new test file.

```bash
qcrbox-test init --config <path_to_app_config> --valid_cif <path_to_cif> [--output <output_path>]
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `--config` | Path to the application configuration file (e.g., `config_my_app.yaml`) | Yes |
| `--valid_cif` | Path to a valid CIF file to use as a template/input | Yes |
| `--output` | Output path for the generated test suite YAML file | No |

## Command-Line Options

### Full Syntax

```bash
qcrbox-test [--test-location PATH] [--qcrbox-url URL] [--debug]
```

### Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--test-location` | Path to a YAML test file or directory | `qcrbox_tests` |
| `--qcrbox-url` | URL of the QCrBox API server | `$QCRBOX_API_URL` or `http://localhost:11000` |
| `--debug` | Enable debug mode with detailed logging | Disabled |
| `--help` | Show help message and exit | - |

## Configuring the QCrBox API URL

There are three ways to specify the QCrBox API URL (in order of priority):

### 1. Command-Line Flag (Highest Priority)

```bash
qcrbox-test --qcrbox-url http://localhost:8000
```

### 2. Environment Variable

Set the `QCRBOX_API_URL` environment variable:

```bash
# One-time use
export QCRBOX_API_URL="http://localhost:11000"
qcrbox-test

# Persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export QCRBOX_API_URL="http://localhost:11000"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Default Value (Lowest Priority)

If neither the flag nor environment variable is set, the default is `http://localhost:11000`.

## Debug Mode

### Enabling Debug Mode

```bash
qcrbox-test --debug
```

### What Debug Mode Does

When enabled, debug mode saves detailed information for **failed tests** to the `logs/` directory:

1. **Summary Log**: A text file with detailed failure information
2. **CIF Outputs**: The actual CIF files returned by QCrBox commands
3. **Test Metadata**: Command parameters, expected vs. actual values

### Debug Output Structure

```
logs/
└── 20251027_143022_olex2/       # Timestamp + application slug
    ├── summary.log              # Detailed test results
    └── test_result.cif          # Output CIF file
```
