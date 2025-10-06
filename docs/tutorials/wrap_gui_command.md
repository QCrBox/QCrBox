# Wrapping a Python module and exposing functionality to run within QCrBox

This guide walks you through the process of encapsulating a simple interactive graphical user interface (GUI) application within a QCrBox container under Linux.

## Prerequisites

Before starting, ensure your development environment is set up following the guide located [here](../how_to_guides/set_up_a_dev_environment.md), and that you have `devbox shell` running in your terminal. In addition, it's likely helpful to bring yourself up to speed on the platform's [Technical Reference documentation](../technical_reference/contents.md), in particular [Architecture & key components](../technical_reference/architecture.md).

This tutorial assumes a Linux (e.g. Ubuntu) platform, although Windows WSL2 should work fine.

During this tutorial you will work with Docker, Python, and an understanding of YAML configurations.  If you're new to these concepts you can just type in the commands as listed in the tutorial. Alternatively, you can consult additional resources on [Docker](https://docs.docker.com/get-started/overview/), [Python modules](https://docs.python.org/3/tutorial/modules.html), and [YAML](https://yaml.org/spec/1.2/spec.html) for foundational knowledge.

## Initial Setup

The first step is to create a new QCrBox application container to encapsulate our GUI application within QCrBox. Follow the instructions within the [tutorial to create a new QCrBox container](./create_new_qcrbox_container.md), using the following inputs to the commands in the guide (not using the ones shown in the guide):

- For creating the container, use `qcb init gui_application`.
- For application type, select `Interactive GUI (Linux)`.
- For application slug, enter `dummy_gui_tutorial`.
- For application name, enter `Dummy GUI`.
- For application version, enter `0.1.0`.
- For the remaining fields, feel free to add what you like.

For example:

```
lease provide some basic information about your application.
The following dialog will guide you through the relevant settings.
At any time you can press Ctrl+C to abort.

  [1/7] Select application_type
    1 - Non-interactive Command
    2 - Interactive GUI (Linux)
    3 - Interactive GUI (Windows)
    Choose from [1/2/3] (1): 2
  [2/7] application_slug (dummy_gui_tutorial): 
  [3/7] application_name (Dummy Gui Tutorial): Dummy GUI
  [4/7] application_version (x.y.z): 0.1.0
  [5/7] description (Brief description of the application.): Dummy GUI for testing of interactive applications
  [6/7] url (): 
  [7/7] email (): 

Created scaffolding for new application in '/home/user/QCrBox/services/applications/dummy_gui_tutorial'.
```

For the purposes of this tutorial, we'll also need to obtain two extra files, so download the following:

- [`dummy_gui.py`](./dummy_gui.py): This represents the GUI application we want to run within an interactive session. It's a simple Python program that takes an input CIF file and displays a bsic dialogue box with a selectable button. When the button is clicked, the program closes.
- [`dummy_gui_commands.py`](./dummy_gui_commands.py): This is a small support module that in this case contains a single function used by QCrBox for when the GUI program is closed, to prepare the output CIF file that is expected, and return the output filename from the function. In this case, for tutorial purposes it simply creates a copy of the input CIF file and uses that, but in a typical application, this would be the output CIF file saved by the application.

Ensure both of these files are placed in the `dummy_gui_tutorial` directory.

As a reminder, when invoked, a QCrBox command goes through three states:
  - `prepare` - to set up the application and stage in the input files (e.g. CIF file) to be processed by the application
  - `run` - to actually run the application until closure, controlled by the user interactively in this case
  - `finalise` - to do any last minute post-processing and ensure an output CIF file is ready to be staged out of the application back to QCrBox

It is during the `finalise` state that our function in `dummy_gui_commands.py` is called.

In this example container, we use a trivial application. Of course in practice, an interactive GUI program will obviously be more sophisticated, but the process remains the same: a QCrBox command is invoked on the container which opens an application, the user interacts with the application to accomplish some crystallography tasks, and when complete, the output is saved and the program is closed.

## Specifying our command in `config_dummy_gui_tutorial.yaml`

We next need to define the specifics of the command so it can be used by QCrBox. Amend the contents of this file to the following:

```yaml
name: "Dummy GUI Tutorial"
slug: "dummy_gui_tutorial"
version: "0.1.0"
description: "Dummy GUI for testing of interactive applications"
url: ""

commands:
  - name: "interactive_session"
    implemented_as: "interactive_session"
    description: "Start dummy GUI"
    parameters:
      - name: "input_file"
        dtype: "QCrBox.cif_data_file"
        description: "The file to open in the dummy GUI"
    interactive_lifecycle:
      run:
        implemented_as: "cli_command"
        description: "Run command for rendering the dummy GUI"
        call_pattern: "python dummy_gui.py {input_file}"
        used_basecommand_parameters: ["input_file"]
      finalise:
        implemented_as: "python_callable"
        description: "Finalise command for handling cleaning up afterwards"
        import_path: "dummy_gui_commands"
        callable_name: "finalise_interactive"
        used_basecommand_parameters: ["input_file"]

qcrbox_yaml_spec_version: "0.1"
```

In this case, we define a single command which will use an `interactive_session`. When invoked, a QCrBox interactive session will create a VNC browser window for the user to interact with the application. This command will take a single input, a `QCrBox.cif_data_file`.

In order for QCrBox to know what to do to during the `run` state, we need to specify how to run the application within the container. We define a `run` step as part of the command's `interactive_lifecycle`. Here, we indicate that this a `cli_command` and the command to run is `python dummy_gui.py {input_file}`. Note that `{input_file}` will be substituted with the actual input file name at runtime as specified in the `input_file` input parameter.

Similarly, we also need to specify what will happen when the command reaches its `finalise` step, when the application is completed. In this case, we specify a `python_callable` function `finalise_interactive` which is held in out `dummy_gui_commands` Python script. We also pass in the `input_file` as before.

We could also specify an additional `prepare` step here within the lifecycle, but other than staging in the input file, we don't need to do anything else for this particular application.

For a more comprehensive example of specifying a command in YAML that includes CIF parameter , see the [wrapping a Python module](./wrap_python_command.md) tutorial.

## Specifying the Python glue code for our command

We also need to specify glue code that informs QCrBox where the command YAML file is located, as well as any other functions that we may need to invoke prior to running the application (e.g. any other pre-processing steps on an input file, for example). This is specified in the `configure_dummy_gui_tutorial.py` file. Hwoever, in this case, we only need to pass the command YAML to QCrBox, and don't have any other processing steps:

```yaml
from pyqcrbox.registry.client import QCrBoxClient
from pyqcrbox.sql_models import ApplicationSpec

if __name__ == "__main__":
    application_spec = ApplicationSpec.from_yaml_file("config_dummy_gui_tutorial.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()
```

For a more sophisticated example of this, see the [wrapping a Python module](./wrap_python_command.md) tutorial.

## Configuring the Dockerfile

Our Dockerfile details the steps to install our application within the container. This may involve things like installing any needed operating system packages, copying over installation files, executing the installer, copying over any configuration files, setting up any virtual environment that the application will run within, and other aspects related to installation and setting up its environment. In our case, for this tutorial we only need to do the following, so amend the `Dockerfile` accordingly:

```Dockerfile
ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

COPY --chown=qcrbox:qcrbox configure_dummy_gui_tutorial.py config_dummy_gui_tutorial.yaml ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui_commands.py ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui.py ${QCRBOX_HOME}
```

So here, we specify the `SHELL` to use will be Bash, and our `*.py` files to `COPY` over to the container's `QCRBOX_HOME` directory where they'll be executed, setting their file permissions appropriately. We also copy over the `.yaml` file for completeness, although in this case it won't be used.

## Building the container

To create a QCrBox image for our application, we'll execute a specific build command using the application slug defined earlier. Open your terminal and input the following command to start the build process:

```bash
qcb build dummy_gui_tutorial
```

> **Important Note:** By default, `qcb build` without additional arguments performs a full rebuild of all dependencies to ensure everything is up-to-date. If you have recently completed a build and wish to save time, you can opt for the `--no-build-deps` argument. This option focuses solely on building the QCrBox image without updating the dependencies.

After completing the build process, you can launch your newly created QCrBox image with the following command:

```bash
qcb up dummy_gui_tutorial --no-build-deps
```

This command starts the container without recompiling the image or its dependencies, assuming they were recently built. If you aim to update both dependencies and the image before launching, simply omit the `--no-build-deps` flag. This ensures that your QCrBox image and all related components are fully up-to-date.


## What about a command line application?



## Conclusion and final remarks

We have now exposed two commands in QCrbox from a Python module. One that only analyses a cif file to produce some output, and another one that works from an input cif file to an output cif.

For more examples you might consider looking into the already implemented programs in `services/applications`. If this tutorial is unclear at any point please raise an issue on Github with the specific problem that you ran into.
