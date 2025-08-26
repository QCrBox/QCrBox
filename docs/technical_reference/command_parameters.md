# Command Parameter Specification

## Parameter types

| QCrBox Data Type       | Class                  | Description                      |
|------------------------|------------------------|----------------------------------|
| `str`                  | `str`                  | String type                      |
| `int`                  | `int`                  | Integer type                     |
| `float`                | `float`                | Floating-point number            |
| `bool`                 | `bool`                 | Boolean value                    |
| `QCrBox.output_cif`    | `str`                  | Path or name of output CIF file  |
| `QCrBox.data_file`     | `DataFileParameter`    | Custom data file parameter       |
| `QCrBox.cif_data_file` | `CifDataFileParameter` | Custom CIF data file parameter   |

## Deprecated data types

| QCrBox Data Type       | Class                  | Description                      |
|------------------------|------------------------|----------------------------------|
| `QCrBox.work_cif`      | `str`                  | Path or name of working CIF file |
| `QCrBox.folder_path`   | `str`                  | Folder path                      |
| `QCrBox.input_path`    | `str`                  | Path to input data               |
| `QCrBox.output_path`   | `str`                  | Path to output data              |
| `QCrBox.input_folder`  | `str`                  | Input folder path                |

Expected attributes

```python
name: str
dtype: DTypeAsStr
description: str
```

Optional attributes (default value has to be a builtin value)

```python
default_value: Any | None = None
valid_values: ValidValueSpec | None = None
```

Valid values can be a numeric range, a list of string enums or a regex.

```python
numeric_range: tuple[float | int, float | int] | None = None
string_enum: list[str] | None = None
string_regex: str | None = None
```
