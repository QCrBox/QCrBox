# Command Parameter Specification

This document details how (the) QCrBox (registry) handles parameters for commands.

## Parameter types

The table below lists the supported data types for parameters. The first four rows are the standard data types in
Python, whilst the last three are custom data types for QCrBox.

| QCrBox Data Type       | Class                  | Description                                                         |
|------------------------|------------------------|---------------------------------------------------------------------|
| `str`                  | `str`                  | String type                                                         |
| `int`                  | `int`                  | Integer type                                                        |
| `float`                | `float`                | Floating-point number                                               |
| `bool`                 | `bool`                 | Boolean value                                                       |
| `QCrBox.data_file`     | `DataFileParameter`    | Custom data file parameter type, used for generic files (e.g. .csv) |
| `QCrBox.cif_data_file` | `CifDataFileParameter` | Custom CIF data file parameter typed, used for CIF files            |
| `QCrBox.output_cif`    | `str`                  | Name to use for the output CIF file                                 |

In addition to the above data types, we have the following **deprecated** data types which have been removed since
moving to using NATS as the message broker and data store/manager. These were removed because there is no shared file
system between containers, so the concept of input and output paths and intermediate work files are not required because
they are not handled by users or application developers. These could come back in the future, if a use case is found.

| QCrBox Data Type      | Class | Description                      |
|-----------------------|-------|----------------------------------|
| `QCrBox.work_cif`     | `str` | Path or name of working CIF file |
| `QCrBox.folder_path`  | `str` | Folder path                      |
| `QCrBox.input_path`   | `str` | Path to input data               |
| `QCrBox.output_path`  | `str` | Path to output data              |
| `QCrBox.input_folder` | `str` | Input folder path                |

## Parameter YAML specification

Parameters are defined as an array of Parameter Specifications. Each parameter requires the following fields,

- `name` - the name of the parameter (must match what is used in the command implementation)
- `dtype` - the data type of the parameter
- `description` - a description of the parameter

In addition to these three required fields, we have two optional fields

- `default_value` - the default value for the parameter, used as a placeholder
- `valid_value` - specification of the valid/allowed values for the parameter

Whilst these are optional, it is strongly recommended these fields are used where appropriate. The table below shows
which data types are compatible with both `default_value` and `valid_value`.

| Data Type              | Compatible |
|------------------------|------------|
| `str`                  | ✅          |
| `int`                  | ✅          |
| `float`                | ✅          |
| `bool`                 | ✅          |
| `QCrBox.data_file`     | ❌          |
| `QCrBox.cif_data_file` | ❌          |
| `QCrBox.output_cif`    | ✅          |

If `valid_value` is not set, the parameter is essentially free to be whatever is possible within the remit of the data
type that it is. Below is an example of a YAML specification of parameters for a command.

```yaml
parameters:
  - name: input_cif
    dtype: QCrBox.cif_data_file
    description: The input CIF file
  - name: print_times
    dtype: int
    description: The number of times to print the CIF file
    default_value: 2
    valid_value:
      numeric_range: [1, 10]
  - name: print_mode
    description: The mode to use to print the CIF file
    default_value: plain
    valid_value:
      choices: ["colourful", "plain", "json"]
  - name: cif_label
    description: The CIF label/section to print, must begin with an _
    valid_value:
      regex: "^_"
```


All parameters are expected to have at least these three attributes.
