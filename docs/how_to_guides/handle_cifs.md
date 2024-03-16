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

<a name="abcde">**Specific CIF**</a> CIF file create using specific keywords in a specific format, this can be the DDL1 style of keywords but it does not have to be.

**Specific CIF entry**: A name of a cif entry **in any convention** that is contained within the CIF dictionaries. `_atom_site_fract_x` and `_atom_site.fract_x` are both valid specific cif entries.

**Required CIF entry**: A specific CIF entry that is required to run a script or program. The QCrBoxTools functions will include the entry in the newly produced CIF file, if the unified CIF equivalent of that keyword is found. Otherwise they will throw an error.

**Optional CIF entry**: A specific CIF entry that might be used by a script or program. Will be included if the unified CIF equivalent is present and otherwise ignored.

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
This section will focus on how to work with the CIF capabilities of the yaml file. For parameter definition look into the [tutorial](../tutorials/wrap_python_command.md).

The yaml file can contain the following options in a command:

```YAML
commands:
  - name: "my_command"
    implemented_as: "CLI/python_callable/GUI"
    parameters:
      # Definition covered in tutorial
    required_cif_entries: ["_some_entry", "_some_other_entry"]
    optional_cif_entries: ["_some_entry_su"]
    required_cif_entry_sets: ["cell_data", "diffraction_data"]
    optional_cif_entry_sets: ["atom_data"]
    merge_cif_su: Yes
    custom_cif_categories: ["iucr", "shelx"]
```

Let us go through the options line by line:

  - **`name`**: The QCrBoxTools function working with CIF require a command name or command. This is that name

  - **`required_cif_entries`**: List of specific CIF entries to include (see [Nomenclature](#nomenclature-in-this-howto))

  - **`optional_cif_entries`**: List of specific CIF entries to include when present (see [Nomenclature](#nomenclature-in-this-howto))

  - **`required_cif_entry_sets`**: List of CIF entry sets to include. All required entries will be treated as required and optional entries will be included as optional. (For definition of entry sets see next section).

  - **`optional_cif_entry_sets`**: List of CIF entry sets to include. All required entries and optional entries will be included as optional. (For definition of entry sets see next section).

   - **`merge_cif_su`**: If set to `Yes`, the standard uncertainty entries will be merged with the base entry using bracket notation, **unless the standard uncertainty is requested separately as its own entry**. So in the example above `_some_entry` would not be merged with a present standard uncertainty entry, both `_some_entry` and `_some_entry_su` are included separately. `_some_other_entry` would be merged if an SU was present.
   
   - **`custom_cif_categories`**: List of custom CIF categories to include in the output cif file (see [Nomenclature](#nomenclature-in-this-howto)).

### CIF entry sets in a YAML file
In order to keep the command definition somewhat compact and not redefine entries shared between commands, the YML also contains the possibility to define cif entry sets. The syntax is:

```YAML
cif_entry_sets:
  - name: "cell_data"
    required : ["_required_entry"]
    optional : ["_optional_entry"]
```

The `name` is the name of the set, which can be used in the command definition. The `required` and `optional` lists are lists of specific CIF entries to include in the set (see [Nomenclature](#nomenclature-in-this-howto)).
