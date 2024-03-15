

# Wrap a python module and expose functionality to run within QCrBox

For this tutorial we will implement functionality from a small python module that allows us to search how many structures with similar elements and unit cell parameters is contained within the [crystallographic open database (COD)](https://www.crystallography.net/cod/). Now we want to put the functionality of that module into its own QCrBox container.

If you have set up you dev environment you can now initialise the new container by typing `qcb init cod_check` and fill out the following dialogue:

```
Please provide some basic information about your application.
The following dialog will guide you through the relevant settings.

  [1/7] Select application_type
    1 - CLI
    Choose from [1] (1): 1
  [2/7] application_slug (cod_check):
  [3/7] application_name (Cod Check): COD Check
  [4/7] application_version (x.y.z): 0.0.1
  [5/7] description (Brief description of the application.): Can be used to check whether there is a similar structure in the crystallographic open database and output similar structures.
  [6/7] url (): https://my.official.module.url
  [7/7] email (): module_contact@university.somewhere

Created scaffolding for new application in 'T:\QCrBox_location\services\applications\cod_check'.
```

As the boilerplate CLI has told us we have created some scaffolding in the applications folder. Let us have a look into the created files in that folder.

 - The two `docker-compose.cod_check.*.yml` files. For a non GUI application these can remain untouched
 - `sample_cmd.sh` is an example bash file for CLI applications. You can delete this one.
 - The `Dockerfile`: This contains the instructions to build the container
 - `config_cod_check.yaml`: In future this will the way to define exposed functions in QCrbox. At the moment the file will be used to request cif keywords.
 - `configure_cod_check.py`: This is where we will implement our functionality and register it with QCrBox

We will now go through these files step by step and make the necessary changes to expose our COD search functionality. If you want to implement the container alongside the tutorial, first download the python file from [here](./example_support/simple_cod_module.py), then copy the `simple_cod_module.py` into the `cod_check` folder.

## The Dockerfile
Let us go through the created docker to see what the individual commands mean and delete some entries we do not need. In general, there is an extensive number of tutorials and documentation about Docker on the internet on how to build containers so we will only tackle a very simple case here.

The first two lines mean that we build our application container based on the qcrbox/baseapplication container. The first line loads the environment variable containing the current version of qcrbox and the second line loads the base-application image of that newest version. The clever thing about Docker is that the base image data is only stored once, no matter how many other images are based on it!

``` Docker
ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
```

The next line triggers the use of the `/bin/bash` shell for running any future commands.

``` Docker
SHELL ["/bin/bash", "-c"]
```

The next line would copy the example executable to `/opt/cod_check/bin`. Delete that line as we will write our own implementation.

```Docker
COPY sample_cmd.sh /opt/cod_check/bin/
```

The following lines will copy the `/configure_*.py` and the `/config_*.yaml` to our container. We will modify these files to implement our logic.

``` Docker
COPY configure_cod_check.py ./
COPY config_cod_check.yaml ./

```

The next line adds the path to the executable to the PATH variable to make it available. We can also delete that line.

```Docker
ENV PATH="$PATH:/opt/cod_check/bin/"
```

Next, we need to make sure that our module actually ends up in the Docker container so add the line
```Docker
COPY ./simple_cod_module.py ./
```
to the file before the other `COPY` command.

We also need to install the requests module that is a dependency of our module. There is actually to ways to do this. Both use the `RUN` command that executes a shell command within the docker container.

### Option 1: Installing the dependency with `conda`/`micromamba`
To install the package into the conda environment qcrbox itself uses we need to type `conda install -n qcrbox requests` in the terminal. We need to add this line to the Dockerfile:

```Docker
RUN micromamba install -n qcrbox requests --yes
```

> **Note:**
> If you have a large number of packages to install it might be more reasonable to create a .yml file. Then update the qcrbox conda environment by adding the line
>
>```Docker
>micromamba install -n qcrbox --file environment.yml --yes
>```

### Option 2: Installing with pip

```Docker
RUN pip install requests
```

Again larger modules and dependencies can be installed just as normal within the container itself by using `RUN`.


## Add the first command to the `config_cod_check.yaml`
We want to add a command to output the number of structures that have a matching unit cell and contain the elements listed in the cif to a json file in the work folder. Have a look into the `simple_cod_module.py`. We
will want to generate the search_parameters with `cif_to_search_pars` and then search for the number of
fitting structures with `get_number_fitting_cod_entries`.

While the top has been populated by `qcb init`, we now need to replace the content of the commands from the
boilerplate example to our entries.
First replace the `name` from the sample_name to `"get_number_fitting_cod_entries"` and the `implemented_as` from `"cli"` to `"python_callable"`.

We will want our command to have three different parameters
 1. `input_cif_path` (str): Will determine, which cif file used to check for similar structures.
 2. `cellpar_deviation_perc` (float): Will be the maximum difference of unit cell parameters between COD structures and our structure in percent. Default, 2.0 %.
 3. `listed_elements_only` (bool): If this boolean is True, we will only search for entries containing the exact elements in the `input_cif` file. Otherwise, the elements from the `input_cif` have to be present, but other elements could be present as well. Default, false.

Adding the parameters, our commands entry in the yaml file file should look something like this:

```yaml
commands:
  - name: "get_number_fitting_cod_entries"
    implemented_as: "python_callable"
    parameters:
      - name: "input_cif_path"
        type: "str"
        default_value: None
      - name: "cellpar_deviation_perc"
        type: "float"
        default_value: 2.0
        required: false
      - name: "listed_elements_only"
        type: "bool"
        default_value: false
        required: false
```

### Adding cif entries to our command
We now need to define, which cif entries our command needs to work and can look into the `cif_to_search_pars` function for that information. All of these entries are required (the function will not work without them).
If we have only one command, we can add the required entries as a list. Make sure `required_cif_entries:` is at the same indentation level as `parameters:`!

```yaml
    required_cif_entries: [
      "_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha",
      "_cell_angle_beta", "_cell_angle_gamma", "_chemical_formula_sum"
    ]
```

If you have entries, that would be used, but are not required, you can add them as optional_cif_entries in their own list. However, this is not he case here, so this is all we need to do within the yaml file for the time being.

## Writing the python glue code.

> **Note:**
> At the moment we need to implement some functionality that will be automated in the very near future, namely the registering of out application and the commands in python instead of using the yaml file, as well as the handling and conversion of cif files. However, we finally wanted to give out something to actually explore, and therefore decided to postpone that implementation to a point in time after the developer alpha release.

Next we need to open the `configure_cod_check.py` file. We start by importing three functions from two modules:

```python
from qcrboxtools.cif.cif2cif import cif_file_unified_yml_instr
from simple_cod_module import cif_to_search_pars, get_number_fitting_cod_entries
```

The `cif_file_unified_yml_instr` function is used to handle the input and output of cif files from the cif keywords that QCrBox uses to the required cif keywords of `simple_cod_module`. Additionally we need two functions from `simple_cod_module` for the logic we want to implement.

We can now write the python function we need and add it to the `configure_cod_check.py` file:
```python
YAML_PATH = "./config_cod_check.yaml"

def parse_input(input_cif_path, cellpar_deviation_perc, listed_elements_only):
    # have a pathlib.Path instead of a string, makes handling much easier
    input_cif_path = Path(input_cif_path)

    # All input variables will probably be strings and convert to percent
    cellpar_deviation = float(cellpar_deviation_perc) / 100.0

    # make sure this is actually a valid boolean value
    if listed_elements_only.lower() not in ("true", "false"):
        raise ValueError("not a boolean representing string for listed_elements_only")

    # Parse to boolean
    listed_elements_only = listed_elements_only.lower() == "true"

    # get the folder the cif file is in and use it as work folder
    work_folder = input_cif_path.parent

    # create a path for the converted cif
    work_cif_path = work_folder / "work.cif"

    # write a new cif with the entries in the format simple_cod_module needs
    cif_file_unified_yml_instr(
        input_cif_path=input_cif_path,
        output_cif_path=work_cif_path,
        yml_path=YAML_PATH,  # Path to the yaml file we edited in the last step
        command="get_number_fitting_cod_entries",  # name of the command in the yaml file
    )
    return work_cif_path, cellpar_deviation, listed_elements_only

def qcb_get_number_fitting_cod_entries(
    input_cif_path, cellpar_deviation_perc, listed_elements_only
):
    # cast the input parameters from strings to python objects
    work_cif_path, cellpar_deviation, listed_elements_only = parse_input(
        input_cif_path, cellpar_deviation_perc, listed_elements_only
    )

    # get the number of entries
    elements, cell_dict = cif_to_search_pars(work_cif_path)
    n_entries = get_number_fitting_cod_entries(
        elements, cell_dict, cellpar_deviation, listed_elements_only
    )

    # output the retrieved number into a json file.
    with open(work_cif_path.parent / "nentries.json", "w", encoding="UTF-8") as fobj:
        json.dump({"n_entries": n_entries}, fobj)

```

In future we aim to make the local implementation of `parse_input` obsolete as QCrBox will handle these transformations for you. However, for the time being, it is needed.

## Registering the python function as a QCrBox command
At the moment we need to register our command at QCrBox. so we need to modify the lines at the end of the file to

```python
client = QCrBoxRegistryClient()
application = client.register_application(
    "COD Check",
    version="0.0.1",
)

# First string in this command is the exposed command name, second argument is a python function
application.register_python_callable("get_number_fitting_cod_entries", qcb_get_number_fitting_cod_entries)

client.run()
```

QCrbox will automatically read the parameters from the passed python function and will use it for its own parameter names.

## Building the container with the first command exposed

To build a docker image, we need to run the following command, where the argument is the application slug we have defined at the beginning:
```bash
qcb build cod_check
```

> **Note:** When called without other argument `qcb build` will rebuild all dependencies to ensure all dependencies are up to date. If you have very recently rebuild everything, you can save time by using the `--no-deps` argument to just build the container.

We can then start our new container using:
```bash
qcb build cod_check --no-rebuild-deps
```

Again, we do not need to rebuild the image or any of its dependencies, if we have just build it. To build the dependencies, the image and then start the container from it leave the flag.

## Build a function to load in a structure from the best matching unit cell

We now want to insert the atomic parameters from the best fitting structure in the COD into our cif. If the information already is available, we can skip structure solution. So let us add another command to the `config_cod_check.yaml` file. We add these lines at the end of the file

```YAML
  - name: "merge_closest_cod_entry"
    implemented_as: "python_callable"  # other options: "python_callable"
    parameters:
      - name: "input_cif_path"
        type: "str"
        default_value: None
      - name: "cellpar_deviation_perc"
        type: "float"
        default_value: 2.0
        required: false
      - name: "listed_elements_only"
        type: "bool"
        default_value: false
        required: false
    required_cif_entries: [
      "_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha",
      "_cell_angle_beta", "_cell_angle_gamma", "_chemical_formula_sum"
    ]
```

You might notice that our required cif entries are exactly the same, as they are used by the same function within the `simple_cod_module.py` file. This might be fine in this case, as the number of entries is rather low, but ideally we would like to only define the set of entries once. In QCrBox we can do that using cif_entry_sets. At the end of the file we create a new entry set for our commands:

```YAML
cif_entry_sets:
  - name: "cell_elements"
    required: [
      "_cell_length_a", "_cell_length_b", "_cell_length_c", "_cell_angle_alpha",
      "_cell_angle_beta", "_cell_angle_gamma", "_chemical_formula_sum"
    ]
```

Instead of writing the entries into the individual functions we now replace the `required_cif_entry` sections to have our command definition look like this:

```YAML
  - name: "merge_closest_cod_entry"
    implemented_as: "python_callable"  # other options: "python_callable"
    parameters:
      - name: "input_cif_path"
        type: "str"
        default_value: None
      - name: "cellpar_deviation_perc"
        type: "float"
        default_value: 2.0
        required: false
      - name: "listed_elements_only"
        type: "bool"
        default_value: false
        required: false
    required_cif_entry_sets: ["cell_elements"]
```

Try to update the definition of the `get_number_fitting_cod_entries` as well. Note that you can have multiple cif entry sets to mix and match whatever your commands need.

## Writing the python glue code for our merge command.

We will now modify the `configure_cod_check.py` file to add the new functionality. We will use more functionality from both QCrBoxtools and our COD module. Our input section should now look like this:

```python
from qcrbox.registry.client import QCrBoxRegistryClient
from qcrboxtools.cif.cif2cif import (
    cif_file_unified_yml_instr,
    cif_file_unify_split,
)
from qcrboxtools.cif.merge import replace_structure_from_cif

from simple_cod_module import (
    cif_to_search_pars,
    get_number_fitting_cod_entries,
    get_fitting_cod_entries,
    download_cod_cif,
)
```

The `cif_file_unify_split` is the counterpart of the first function from cif2cif. We can use it to convert a non-unified cif to the unified set of entries. The `replace_structure_from_cif` function will do the actual replacement. The function `get_fitting_cod_entries` returns a list of dictionaries of cod entries, sorted by the sum of squared differences in the unit cell parameters. Finally, `download_cod_cif` can be used to download an entry from the cod.

We can now implement our function

```python
def merge_closest_cod_entry(input_cif_path, cellpar_deviation_perc, listed_elements_only):
    # cast the input parameters from strings to python objects
    work_cif_path, cellpar_deviation, listed_elements_only = parse_input(
        input_cif_path, cellpar_deviation_perc, listed_elements_only
    )

    # get the list of fitting entries
    elements, cell_dict = cif_to_search_pars(work_cif_path)
    entry_lst = get_fitting_cod_entries(elements, cell_dict, cellpar_deviation, listed_elements_only)

    # if no fitting entries found, raise an error
    if len(entry_lst) == 0:
        raise ValueError("No fitting entries found")

    # download the cif file of the most fitting entry
    cod_cif_path = work_cif_path.parent / "cod.cif"
    download_cod_cif(entry_lst[0]["file"], cod_cif_path)

    # convert to unified format
    unified_cod_path = work_cif_path.parent / "cod_unified.cif"
    cif_file_unify_split(
        cod_cif_path,
        unified_cod_path,
        custom_categories=["cod", "iucr", "olex2", "shelx"],
    )

    # replace structure from input cif with the one from cod cif
    replace_structure_from_cif(input_cif_path, 0, unified_cod_path, 0, work_cif_path.parent / "output.cif")
```

And finally we register that function with QCrBox by adding

```python
application.register_python_callable("merge_closest_cod_entry", merge_closest_cod_entry)
```

right before `client.run()`

## Starting the container again
If you have not done so you can shut down QCrBox by typing `qcb down`. You can now restart and rebuild the container by typing. Rebuilding without dependencies might be faster if you have just rebuid everything.

```bash
qcb up cod_check
```

## Conclusion and final remarks
We have now exposed two commands in QCrbox from a python module. One that only analyses a cif file to produce some output, and another one that works from an input cif file to an output cif. For more examples you might consider looking into the already implemented programs in `services/applications`. If this tutorial is unclear at any point please raise an issue on Github with the specific problem that you ran into.