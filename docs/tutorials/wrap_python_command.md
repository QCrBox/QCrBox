

# Wrap a python module and expose functionality to run within QCrBox

Imagine you have written a small python module that allows us to search how many structures with similar elements and unit cell parameters is contained within the [crystallographic open database (COD)](https://www.crystallography.net/cod/). Now we want to put the functionality of that module into its own QCrBox container.

If you want to follow along, just get a usable python file from [here](./example_support/simple_cod_module.py)

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

We will now go through these files step by step and make the necessary changes to expose our COD search functionality. But first copy the `simple_cod_module.py` into the `cod_check` folder.

## The existing Dockerfile
Let us go through the created docker to see what the individual commands mean.  In general, there is an extensive number of tutorials and documentation about Docker on the internet to see how things are implemented.

The first two lines mean that we build our application container based on the qcrbox/baseapplication container. The first line loads the environment variable containing the current version of qcrbox and the second line loads the base-application image of that newest version. The clever thing about Docker is that the base image data is only stored once, no matter how many other images are based on it! So even if we have a large number of containers. If they are based on the same base image the total harddisk space is much lower than expected.

``` Docker
ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
```

Use the `/bin/bash` shell for running any future commands.

``` Docker
SHELL ["/bin/bash", "-c"]
```

Copy the example executable to `/opt/cod_check/bin`. Delete that line as we will write our own implementation.

```Docker
COPY sample_cmd.sh /opt/cod_check/bin/
```

Copy the `/configure_*.py` to our container. We will use modify the python file to implement our logic. Delete that line as we will write our own implementation.

``` Docker
COPY configure_cod_check.py ./
```

Add the path to the executable to the PATH variable to make it available. We can also delete that line.

```Docker
ENV PATH="$PATH:/opt/cod_check/bin/"
```


## Editing the Dockerfile
We need to make sure that our module actually ends up in the Docker container so add the line
```Docker
COPY ./simple_cod_module.py ./
```
to the file before the other commands `COPY` command. We also need to install the requests module that is a dependency of our module. There is actually to ways to do this. Both use the `RUN` command that executes a shell command within the docker container.

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
 2. `cellpar_deviation_perc` (float): Will be the maximum difference between COD structures and our structure in percent. Default, 2.0 %.
 3. `listed_elements_only` (bool): If this boolean is True, we will only search for entries containing the element in the `input_cif` file. Otherwise, the elements from the `input_cif` have to be present, but other elements could be present as well. Default, false.

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

That is all we need to do within the yaml file for the time being.

## Writing the python glue code.

> **Note:**
> At the moment we need to implement some functionality that will be automated in the very near future, namely the registering of application and the commands in python and the handling and conversion of cif files. However, we finally wanted to give out something to actually explore, so we decided to postpone that implementation after the developer release.

