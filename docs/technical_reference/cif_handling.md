# Implementation of cif format transfer and handling

This documentation is up-to-date for the alpha developer release. The contents within are subject to change for the
full release of QCrBox.

## Cif parameter management

When a cif parameter is required, it is passed to commands API endpoint as JSON data, e.g. `{"input_cif":
{"data_file_id": XXXX}}` where XXXX is the data file ID for the CIF which has already been uploaded to the data
manager. QCrBox uses the value of`data_file_id` to instantiate a `QCrBox.cif_data_file` object, which includes methods
to transfer the cif to a specific format or to merge it with another cif (in a container's file system) to create a
unified cif.

The `CifDataFileParameter` class is essentially an extension of the `DataFileParameter` class. The difference being that
the `DataFileParameter` class is intended for generic data files, so does not include any methods for transferring the
cif between formats.

A `CifDataFileParameter` parameter, and parameters in general, is created inside the application container in the
private `QCrBoxClient._prepare_and_launch_command` method which, in addition to other objects, returns a list of the
"parsed" parameters for command execution. These parsed parameters, including `CifDataFileParameter` objects, are kept
to be passed to the two private methods `QCrBoxClient._handle_non_interactive_output` and
`QCrBoxClient._handle_interactive_output` which are used to save a command's output to the data manager. These methods
require the parsed parameters because it is the `CifDataFileParameter` which exposes methods to transfer between
formats.

### When is a cif transferred between formats?

As mentioned earlier, a cif parameter is transferred to a specific format at the start of command execution and merge
together with a command's output after a command has executed. Therefore in order for this to happen, the command
implementation must return a file path to the cif back to QCrBox (see the command tutorials for more details), e.g.,

```python
def my_qcrbox_command(input_cif: str, output_name: str) -> str | pathlib.Path:
  """An example command.

  Parameters
  ----------
  input_cif : str
    This is a QCrBox.cif_data_file parameter, which within a container is a
    CifDataFileParameter.
  output_name : str
    This is a QCrBox.output_cif, which within a container is a BuiltinParameter
    which contains a string which is the name of the output file.

  Returns
  -------
  pathlib.Path | str
    The file path in the container to the latest cif to return to QCrBox.

  """
  intermediate_file_path = do_some_stuff(input_cif)
  output_path = pathlib.Path(intermediate_file_path).parent / output_name
  shutil.move(output_path, output_path)

  return output_path
```

The final merged cif (based on merged the cif at `output_path` and the `input_cif`) is based on the cif parameters
defined for the `QCrBox.output_cif` parameter as described in the [Working with cif files in
QCrBox](../how_to_guides/handle_cifs.md) article. If there is no `QCrBox.output_cif` parameter, then a simple merge is
conducted without any further processing; e.g. the cif files `input_cif` and `output_path` are merged together without
modifying any cif entries.

If a `QCrBox.cif_data_file` parameter has no entries specified in the yaml, as below, transferring is still attempted.
However, the QCrBoxTools functions will fail and a warning message will be logged and the original cif will be sent to
the command. **In future releases, if there are no specified entries then a transferring the cif to a new format will
not be attempted.**

```yaml
parameters:
  - name: input_cif
    dtype: QCrBox.cif_data_file
```

However, if entry sets are defined in the parameter specification like in the YAML below, the cif will be transferred to
the format specified. If this is not possible such as when QCrBoxTools is unable to transfer due to missing contents in
the file, then an warning is issued and the original cif will be sent to the command.

```yaml
parameters:
  - name: input_cif
    dtype: QCrBox.cif_data_file
    required_entry_sets: [ "cell_elements" ]
cif_entry_sets:
  - name: "cell_elements"
    required: [
      "_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha",
      "_cell_angle_beta", "_cell_angle_gamma", "_chemical_formula_sum"
    ]
```

### Implementation

Transform and merge are provided by two methods in `CifDataFileParameter` and a small options model.

```python
class Cif2CifOptions(QCrBoxPydanticBaseModel):
  application_yaml: str    # path to the application YAML inside the container
  command_name: str        # command requesting the translation/merge
  parameter_name: str      # name of the cif parameter or QCrBox.output_cif to use
  output_path: str | None  # optional path/name for the unified output CIF
```

- CifDataFileParameter.to_specific_format(input_cif_path, transform_options)
  - Lazily calls qcrboxtools' `cif_file_to_specific_by_yml` to attempt a format translation using the supplied YAML and
    parameter name (the method's second argument is named `transform_options` in the code).
  - On success writes a `<stem>-converted.cif` and copies it over the exported CIF on disk. `NoKeywordsError` is logged
    as a warning and other exceptions are logged as errors; the original CIF is preserved on failure.

- CifDataFileParameter.to_unified_format(new_cif_path, merge_options)

  - Calls qcrboxtools' `cif_file_merge_to_unified_by_yml` to merge the original exported CIF (tracked on the parameter
    instance) with the command-produced `new_cif_path` (the method's second argument is `merge_options`).

  - If `merge_options.output_path` is provided, that filename (with `.cif` suffix) is used for the unified output;
    otherwise a default `<stem>.cif` name is used. The merged file is copied into place, the parameter's
    exported path is updated on success and the merged path is returned.

Usage (client/calculation):

- `get_cif_merge_parameter(command, parsed_parameters)` returns `(parameter_name, cif_parameter)` — the name to use for
  Cif2Cif and the `CifDataFileParameter` instance to merge with.
- The client constructs `Cif2CifOptions(application_yaml, command_name, parameter_name[, output_path])` and passes it to
  the calculation as `merge_options` (see `QCrBoxClient._handle_non_interactive_output`/`_handle_interactive_output`).
  `output_path` can be taken from the third return value of `get_cif_merge_parameter` when present.
- `PythonCallableCalculation.save_output_to_data_manager` (when given `input_cif` and `merge_options`) will call `await
  input_cif.to_unified_format(output_file, merge_options)` before importing the merged file into the DataManager and
  creating a dataset. CLI-based calculations currently do not import outputs.

Conversion failures are logged and the system falls back to using the original CIF rather than failing the whole
command.
