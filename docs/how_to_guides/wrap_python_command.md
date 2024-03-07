

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

## Editing the Dockerfile
We need to make sure that our module actually ends up in the Docker container so add the line
```Docker
COPY ./simple_cod_module.py ./
```
to the file before the two other commands. We also need to install the requests module that is a dependency of our module. There is actually to ways to do this. Both use the `RUN` command that executes a shell command within the docker container.

### Option 1: Installing the dependency with `conda`/`micromamba`
To install the package into the conda environment qcrbox itself uses we need to type `conda install -n qcrbox requests` in the terminal. We need to add this line to the Dockerfile:

```Docker
RUN conda install requests
```

### Option 2: Installing with pip



