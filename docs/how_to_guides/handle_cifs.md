Working with cif files in QCrBox
================================

QCrBox transfers data between containers using the crystallographic information file format (CIF). However, cif supports a number of aliases for the same entry. In addition some entries have been deprecated over the years. This provides a challenge for interoperability as one program within QCrBox might require a specific cif entry format for its input, while the software package that output the information might use another.

## Unified cif: The transfer format

As such we decided to convert all cif files to a state containing a unique set of keywords and split standard uncertainties (SUs).
For the keyword names, we used the base definition of the current IUCr cif dictionaries, such as the [cif_core.dic](https://github.com/COMCIFS/cif_core/blob/master/cif_core.dic). Additionally, standard uncertainties are separated into their own keywords. This ensures that numerical convergence is actually possible.

The following example entries should illustrate the convention:

```CIF
data_old_format

_cell_length_a     10.032(3)
_cell_length_b      9.147(4)


data_unified_format

_cell.length_a      10.032
_cell.length_a_su    0.003
_cell.length_b       9.147
_cell.length_b_su    0.004
```

QCrBox does offer tools to convert between formats to make integration of software using any format as seamless as possible.

## Nomenclature in this HowTo:
**Unified CIF**: See above

**Specific CIF** CIF file create using specific keywords in a specific format, this can be the DDL1 style of keywords but it does not have to be.

**Specific CIF entry**: A name of a cif entry **in any convention** that is contained within the CIF dictionaries. `_atom_site_fract_x` and `_atom_site.fract_x` are both valid specific cif entries.

**Required CIF entry**: A specific CIF entry that has to be in a CIF file. Either needed run the program (input) and therefore needs to be created from its unified equivalent. The other possibility is that it needs to be present in the output for the program to have run successfully and will be converted to its unified equivalent after the end of the data processing. Defined in the format (DDL1 or DDLm) of the program that is running within the QCrBox container.

**Optional CIF entry**: A specific CIF entry that might be used by a script or program (input). In this case it will be included if the unified CIF equivalent is present and otherwise ignored. For the definition of an output parameter, it will be included if the containerised program has written it, but will not cause an error if not present for conversion to unified cif.

**Split SUs**: Splitting the standard uncertainties into their own keywords.

**Merge SUs**: Combining a keyword with a standard uncertainty keyword to get the bracket notation.

**Custom CIF categories**: Programs or organisations might define their own CIF entries in their own namespace. The old convention is using an underscore after the namespace *e.g.* `_qcrbox_my_value`, while the new convention is `qcrbox.my_value`. Listing the categories as a custom category without a leading underscore will insure the correct back and forth conversion between the two.

## Converting to Unified CIF using the QCrBoxtools container
If you want to convert your cif file into the unified cif format without any more knowledge, there is an [example IPython notebook](https://github.com/QCrBox/QCrBox/blob/dev/wrapper/example_qcrboxtools.ipynb) that shows you how to do that, by using the exposed `to_unified_cif` command of that container.

## Converting CIF files using the QCrBoxTools Python Library
The QCrBoxTools library is available within the python environment of every QCrBox container. It can be called either via a command line interface or within a python script. Additionally you can also install the library outside of QCrBox by getting the source [here](https://github.com/QCrBox/QCrBoxTools) and installing it into your local python environment.

### Using the command line interface
The command line interface can be called by invoking:
```bash
python -m qcrboxtools.cif <cmd> <input_cif_path> <output_cif_path> <ARGS>
```
Invoke with `--help` instead of arguments to see the available options.

### Using the python library.
The required functions are located within the `qcrboxtools.cif.cif2cif` module if you want to work from and to files and in `qcrboxtools.cif.entries` and `qcrboxtools.cif.uncertainties` if you want to work with `iotbx.cif` objects. The docstrings of the functions should be covering the use cases. If they are unclear, please raise a GitHub issue.

## Working with QCrBox `config*.yml` files

This section will focus on how to work with the CIF capabilities of the yaml file. For the other aspects of parameter definition look into the [tutorial](../tutorials/wrap_python_command.md). The specification of cif entries is tied to a parameter of the type `"QCrBox.input_cif"` or `"QCrBox.output_cif"`.

### Defining input parameters.
```YAML
commands:
  - name: "my_command"
    implemented_as: "CLI/python_callable/GUI"
    parameters:
      - name: "example_input_parameter"
        type: "QCrBox.input_cif"
        required_entries: [
          "_some_entry",
          one_of: ["_some_other_entry", ["_set_entry_one", "_set_entry_two"]]
        ]
        optional_entries: ["_some_entry_su"]
        required_entry_sets: ["cell_data", "diffraction_data"]
        optional_entry_sets: ["atom_data"]
        merge_su: Yes
        custom_categories: ["iucr", "shelx"]
```

Let us go through the options of this input parameter line by line:

  - **`commands`**: Start of the command list. As specified in the YAML file, all following entries in the command list must be indended

  - **`name`**: The name of the first (and here only) command within the command list

  - **`parameters`**: List of parameters of `my_command`. For entries within the parameter list we need another level of indentation

    - **`name`**: Name of the parameter (here: `example_input_parameter`).

    - **`type`**: Type of the parameter. Special types that concert cif handling are `"QCrBox.input_cif"` and `"QCrBox.output_cif"`

    - **`required_entries`**: List of specific CIF entries to include (see [Nomenclature](#nomenclature-in-this-howto)). If the packaged program has more than one possibility to calculate an essential value, you can use the `one_of:` keyword demonstrated in the second line. Here we need either the entry `_some_other_entry` or all the entries within the second list, which means both `_set_entry_one` and `_set_entry_two` have to be present.

    - **`optional_entries`**: List of specific CIF entries to include when present (see [Nomenclature](#nomenclature-in-this-howto)). Can also include `one_of` to only include the first option that can be found.

    - **`required_entry_sets`**: List of CIF entry sets to include. All required entries will be treated as required and optional entries will be included as optional. (For definition of entry sets see next section).

    - **`optional_entry_sets`**: List of CIF entry sets to include. All required entries and optional entries will be included as optional. (For definition of entry sets see next section).

    - **`merge_su`**: If set to `Yes`, the standard uncertainty entries will be merged with the base entry using bracket notation, **unless the standard uncertainty is requested separately as its own entry**. So in the example above `_some_entry` would not be merged with a present standard uncertainty entry, both `_some_entry` and `_some_entry_su` are included separately. `_some_other_entry` would be merged if an SU was present.

    - **`custom_categories`**: List of custom CIF categories to include in the output cif file (see [Nomenclature](#nomenclature-in-this-howto)).

### Defining output parameters
```YAML
commands:
  - name: "my_command"
    implemented_as: "CLI/python_callable/GUI"
    parameters:
      - name: "example_output_parameter"
        type: "QCrBox.output_cif"
        required_entries: [
          "_meaningful_entry",
          one_of: ["_meaningful_other_entry", ["_set_entry_a", "_set_entry_b"]]
        ]
        required_entry_sets: ["diffraction_data"]
        optional_entry_sets: ["atom_data"]
        custom_categories: ["iucr", "shelx"]
        invalidated_entries: ["_calculation_remnant", "_everything_fitting_regex.*"]
```
QCrBox assumes that each command will only update part of the available information, while other information in the `input_cif` file remains valid. As such we need to define which entries from the `input_cif` should be kept and which values created by the executable within the command should be added.

The `invalidated_entries` section is a list of [python re](https://docs.python.org/3/library/re.html) RegExes that can be used to filter out values from the original cif file. For example a change in any of the parameters might invalidate the contained quality indicators within the `input_cif` file. We can filter them out using `"_refine.*"`. Invalidated entries only work on the `input_cif`.

The entries transferred from the cif file created during command execution can be chosen using `required` and `optional` cif entries. `required` in this context means that a missing value indicates that the calculation has failed (and therefore the result should not be used). Optional entries are copied but do not indicate a failure.

In future `required` entries will also be used to check whether a command can be run given its precesing commands.


### CIF entry sets in a YAML file
In order to keep the command definition somewhat compact and not redefine entries shared between commands, the YML also contains the possibility to define cif entry sets. The syntax is:

```YAML
cif_entry_sets:
  - name: "cell_data"
    required : ["_required_entry"]
    optional : ["_optional_entry"]
```

The `name` is the name of the set, which can be used in the command definition. The `required` and `optional` lists are lists of specific CIF entries to include in the set (see [Nomenclature](#nomenclature-in-this-howto)).
