# Test Suite Format

This document describes the YAML format for defining QCrBox test suites.

## Table of Contents

- [Overview](#overview)
- [Test Suite Structure](#test-suite-structure)
- [Test Case Structure](#test-case-structure)
- [Input Parameters](#input-parameters)
- [Expected Results](#expected-results)
  - [Status Tests](#status-tests)
  - [CIF Value Tests](#cif-value-tests)
  - [CIF Loop Value Tests](#cif-loop-value-tests)
- [Complete Examples](#complete-examples)

## Overview

A test suite YAML file defines tests for a specific QCrBox application. Each file can contain multiple test cases that verify different commands and their outputs.

## Test Suite Structure

The top-level structure of a test suite:

```yaml
application_slug: string          # Required: Name of the QCrBox application
application_version: string       # Required: Version of the application
description: string               # Optional: Description of the test suite
test_cases: []                    # Required: List of test cases (at least one)
```

### Example

```yaml
application_slug: qcrboxtools
application_version: "0.0.5"
description: "Test suite for qcrboxtools commands"
test_cases:
  - name: "test 1"
    # ... test case details
  - name: "test 2"
    # ... test case details
```

## Test Case Structure

Each test case has the following structure:

```yaml
- name: string                      # Required: Unique name for this test
  description: string               # Optional: Description of what this test does
  command_name: string              # Required: QCrBox command to execute
  manual_precondition: []           # Optional: List of manual setup steps (for documentation)
  input_parameters: []              # Optional: List of input parameters for the command
  expected_results: []              # Required: List of expected results (at least one)
```

### Example

```yaml
- name: "iso2aniso epoxide"
  description: "Test the iso2aniso command with epoxide structure"
  command_name: iso2aniso
  manual_precondition:
    - qcrboxtools container needs to be built and available
  input_parameters:
    # ... parameters
  expected_results:
    # ... expected results
```

## Input Parameters

Input parameters define the data passed to the QCrBox command. The names must be identical to the one of the QCrBox command. There are three types of parameters:

### 1. Simple Value Parameters

For string, number, or boolean values:

```yaml
- name: parameter_name           # Required: Parameter name
  type: str                      # Optional: Type (str, int, float, bool)
  value: "some value"            # Required: The parameter value
```

#### Example

```yaml
input_parameters:
  - name: output_cif_name
    type: str
    value: "result.cif"
  - name: threshold
    type: float
    value: 0.01
  - name: enabled
    type: bool
    value: true
```

### 2. External File Parameters

For files stored in in a location relative to your YAML file:

```yaml
- name: parameter_name           # Required: Parameter name
  type: external_file            # Required: Indicates file from filesystem
  value: "./path/to/file.cif"    # Required: Path relative to YAML file
  upload_filename: "custom.cif"  # Optional: Filename when uploading to QCrBox
```

#### Example

```yaml
input_parameters:
  - name: input_cif
    type: external_file
    value: "./test_cif_files/epoxide_isotropic.cif"
  - name: reference_file
    type: external_file
    value: "./test_cif_files/reference.cif"
    upload_filename: "ref.cif"
```

### 3. Internal File Parameters

For inline file content (useful for small test files):

```yaml
- name: parameter_name           # Required: Parameter name
  type: internal_file            # Required: Indicates inline content
  value: |                       # Required: File content (multiline supported)
    data_structure
    _cell.length_a  10.0
    # ... rest of CIF content
  upload_filename: "custom.cif"  # Optional: Filename when uploading to QCrBox
```

#### Example

```yaml
input_parameters:
  - name: structure_cif
    type: internal_file
    value: |
      data_new_structure
      _cell.length_a    10.0
      _cell.length_b    10.0
      loop_
      _atom_site.label
      _atom_site.fract_x
      O1  0.250
    upload_filename: "structure.cif"
```

## Expected Results

Expected results define the assertions that will be checked after command execution. Each result has a `result_type` that determines what kind of test is performed.

### Status Tests

Test the execution status of the command.

```yaml
result_type: status              # Required: Indicates a status test
expected: successful             # Required: Expected status (successful, failed, or warning)
```

#### Example

```yaml
expected_results:
  - result_type: status
    expected: successful
  - result_type: status
    expected: failed
```

### CIF Value Tests

Test values in the CIF output file (non-loop entries). All CIF value tests share:

```yaml
result_type: cif_value           # Required: Indicates a CIF value test
test_type: <test_type>           # Required: Type of test (see below)
cif_entry_name: "_entry.name"    # Required: CIF entry to test
```

#### Match Test

Test that a CIF entry exactly equals an expected value:

```yaml
result_type: cif_value
test_type: match
cif_entry_name: "_cell.length_a"
expected_value: 10.5             # Can be string, number, or boolean
```

#### Non-Match Test

Test that a CIF entry does NOT equal a forbidden value:

```yaml
result_type: cif_value
test_type: non-match
cif_entry_name: "_refine.ls_structure_factor_coef"
forbidden_value: "Fsqd"
```

#### Within Test (Numerical Range)

Test that a numerical CIF entry falls within an acceptable range. Two formats:

**Format 1: Expected value ± deviation**

```yaml
result_type: cif_value
test_type: within
cif_entry_name: "_cell.length_a"
expected_value: 10.234
allowed_deviation: 0.001         # Accepts values in [10.233, 10.235]
```

**Format 2: Explicit min/max**

```yaml
result_type: cif_value
test_type: within
cif_entry_name: "_cell.length_a"
min_value: 10.0
max_value: 11.0                  # Accepts values in [10.0, 11.0]
```

#### Contain Test (Substring)

Test that a CIF entry contains a specific substring (case-sensitive):

```yaml
result_type: cif_value
test_type: contain
cif_entry_name: "_chemical.name_common"
expected_value: "epoxide"
```

#### Present Test

Test that a CIF entry exists in the output:

```yaml
result_type: cif_value
test_type: present
cif_entry_name: "_refine.ls_number_reflns"
allow_unknown: false             # Optional: If true, allows '?' values
```

#### Missing Test

Test that a CIF entry does NOT exist in the output:

```yaml
result_type: cif_value
test_type: missing
cif_entry_name: "_non_existent_entry"
```

### CIF Loop Value Tests

Test values within CIF loops. First identifies a specific row using lookup conditions, then tests a value in that row.

All CIF loop value tests share:

```yaml
result_type: cif_loop_value      # Required: Indicates a CIF loop test
test_type: <test_type>           # Required: Type of test (see below)
cif_entry_name: "_entry.name"    # Required: Loop column to test
row_lookup:                      # Required: Conditions to identify the row (at least one)
  - row_entry_name: "_entry.id"
    row_entry_value: "value"
```

#### Row Lookup

The `row_lookup` field identifies which row in a loop to test. Multiple lookup conditions are combined with AND logic.

**Single lookup:**

```yaml
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "O1"
```

This finds the row where `_atom_site.label` equals "O1".

**Multiple lookups (AND logic):**

```yaml
row_lookup:
  - row_entry_name: "_refln.index_h"
    row_entry_value: 1
  - row_entry_name: "_refln.index_k"
    row_entry_value: 3
  - row_entry_name: "_refln.index_l"
    row_entry_value: 5

```

This finds the row where ALL THREE conditions are true.

#### Match Test

Test that a loop value exactly equals an expected value:

```yaml
result_type: cif_loop_value
test_type: match
cif_entry_name: "_atom_site.adp_type"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "O1"
expected_value: "Uani"
```

#### Non-Match Test

Test that a loop value does NOT equal a forbidden value:

```yaml
result_type: cif_loop_value
test_type: non-match
cif_entry_name: "_atom_site.adp_type"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "H1"
expected_value: "Uani"
```

#### Within Test (Numerical Range)

Test that a numerical loop value falls within a range. Two formats:

**Format 1: Expected value ± deviation**

```yaml
result_type: cif_loop_value
test_type: within
cif_entry_name: "_atom_site_aniso.u_11"
row_lookup:
  - row_entry_name: "_atom_site_aniso.label"
    row_entry_value: "O1"
expected_value: 0.029
allowed_deviation: 0.0001
```

**Format 2: Explicit min/max**

```yaml
result_type: cif_loop_value
test_type: within
cif_entry_name: "_atom_site.fract_x"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "O1"
min_value: 0.0
max_value: 1.0
```

#### Contain Test (Substring)

Test that a loop value contains a substring:

```yaml
result_type: cif_loop_value
test_type: contain
cif_entry_name: "_atom_site.type_symbol"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "C1a"
expected_value: "C"
```

#### Present Test

Test that a loop entry exists in a specific row:

```yaml
result_type: cif_loop_value
test_type: present
cif_entry_name: "_atom_site.u_iso_or_equiv"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "O1"
allow_unknown: false             # Optional: If true, allows '?' values
```

#### Missing Test

Test that a loop column does NOT exist:

```yaml
result_type: cif_loop_value
test_type: missing
cif_entry_name: "_atom_site.nonexistent_column"
row_lookup:
  - row_entry_name: "_atom_site.label"
    row_entry_value: "O1"
```

## Complete Examples

### Example 1: Basic Test with External File

```yaml
application_slug: qcrboxtools
application_version: "0.0.5"
test_cases:
  - name: "iso2aniso epoxide"
    description: "Convert isotropic to anisotropic ADPs"
    command_name: iso2aniso
    
    input_parameters:
      - name: input_cif
        type: external_file
        value: "./test_cif_files/epoxide_isotropic.cif"
      - name: output_cif_name
        type: str
        value: "epoxide_anisotropic.cif"
    
    expected_results:
      # Check command succeeded
      - result_type: status
        expected: successful
      
      # Check specific atom has anisotropic ADPs
      - result_type: cif_loop_value
        test_type: match
        cif_entry_name: "_atom_site.adp_type"
        row_lookup:
          - row_entry_name: "_atom_site.label"
            row_entry_value: "O1"
        expected_value: "Uani"
      
      # Check U11 value is within tolerance
      - result_type: cif_loop_value
        test_type: within
        cif_entry_name: "_atom_site_aniso.u_11"
        row_lookup:
          - row_entry_name: "_atom_site_aniso.label"
            row_entry_value: "O1"
        expected_value: 0.029
        allowed_deviation: 0.0001
```

### Example 2: Test with Inline File Content

```yaml
application_slug: qcrboxtools
application_version: "0.0.5"
test_cases:
  - name: "replace structure"
    description: "Replace structure with custom CIF content"
    command_name: replace_structure_from_cif
    
    input_parameters:
      - name: input_cif
        type: external_file
        value: "./test_cif_files/template.cif"
      
      - name: structure_cif
        type: internal_file
      
      - name: output_cif_name
        type: str
        value: "replaced.cif"
    
    expected_results:
      - result_type: status
        expected: successful
      
      - result_type: cif_value
        test_type: match
        cif_entry_name: "_cell.length_a"
        expected_value: 10.0
      
      - result_type: cif_loop_value
        test_type: match
        cif_entry_name: "_atom_site.fract_x"
        row_lookup:
          - row_entry_name: "_atom_site.label"
            row_entry_value: "O1"
        expected_value: 0.250
```

### Example 3: Multiple Test Types

```yaml
application_slug: myapp
application_version: "1.0.0"
test_cases:
  - name: "comprehensive test"
    command_name: process_structure
    
    input_parameters:
      - name: input_file
        type: external_file
        value: "./input.cif"
    
    expected_results:
      # Status check
      - result_type: status
        expected: successful
      
      # CIF value tests
      - result_type: cif_value
        test_type: match
        cif_entry_name: "_cell.length_a"
        expected_value: 10.5
      
      - result_type: cif_value
        test_type: within
        cif_entry_name: "_cell.volume"
        max_value: 2000.0
      
      - result_type: cif_value
        test_type: contain
        cif_entry_name: "_chemical.name_common"
        expected_value: "test"
      
      - result_type: cif_value
        test_type: present
        cif_entry_name: "_refine.ls_number_reflns"
        allow_unknown: false
      
```
