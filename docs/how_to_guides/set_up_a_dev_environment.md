# Setting up a development environment

## Check prerequisites

Make sure you have the necessary prerequisites installed.

!!! info inline end
    QCrBox has been tested with the versions of Python and Docker
    listed here, but other recent versions should also work. Please
    [raise an issue](https://github.com/QCrBox/QCrBox/issues/new){:target="_blank"}
    on GitHub if you experience any problems.

```
$ python --version
Python 3.11.5

$ docker --version
Docker version 24.0.6, build ed223bc

$ docker compose version
Docker Compose version v2.21.0
```

## Clone the QCrBox repository
```
$ git clone https://github.com/QCrBox/QCrBox.git
$ cd QCrBox
```

## Create a virtual environment

Create a virtual environment for the `qcrbox` Python package and activate it.

=== "Linux/Mac OS"
    ```
    $ python -m venv ./venv
    $ source ./venv/bin/activate
    ```

=== "Windows (Powershell)"
    ```
    $ python -m venv .\venv
    $ .\venv\Scripts\activate.ps1
    ```

=== "Windows (command line)"
    ```
    $ python -m venv .\venv
    $ .\venv\Scripts\activate.bat
    ```

!!! note
    In this guide we use a "vanilla" Python [virtual environment](https://docs.python.org/3/library/venv.html)
    because it does not require any additional dependencies.
    If you use a custom package manager such as `poetry` or `conda`
    you can of course adapt the previous step to your specific setup.

Let's also update `pip` to its latest version and install the `uv` package installer (which is *much* faster than the
standard `pip` installer).
```
(venv) $ python -m pip install --upgrade pip uv
```

## Install the `qcrbox` Python package

Next, install the `qcrbox` package itself.
```
$ uv pip install -e ./qcrbox[all]
```
This command installs the `qcb` command line tool, which acts as the command line interface for the
Quantum Crystallography Toolbox, together with all extra dependencies needed for  development. These
extra dependencies include developer tools for testing, code formatting and linting; packages needed
to run the QCrBox server & client locally, and packages needed to build and serve the documentation.

!!! note
    The above command uses the `-e` switch to install `qcrbox` in [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html).
    This means that any changes we make to the code during development are automatically picked up in our local installation
    without having to reinstall/upgrade the `qcrbox` package.


### Alternative: installation with minimal dependencies

If you only care about being able to run the `qcb` command line tool (which is needed in order to build and run the
QCrBox docker containers) but not about any other development capabilities, you can choose to install `qcrbox` with
only a minimal set of dependencies as follows.
```
(venv) $ uv pip install -e ./qcrbox
```

### Alternative: installation with targeted sets of extra dependencies

QCrBox comes with several other sets of additional dependencies which can be specified in square brackets after `qcrbox`.

If you only want to be able to build the documentation, for example, run the following command.
```
(venv) $ uv pip install -e ./qcrbox[docs]
```

If you plan on developing QCrBox, making modifications to the code and/or submitting merge requests,
you most likely want to install the `dev` dependencies, too.
```
(venv) $ uv pip install -e ./qcrbox[dev]
```

Two other sets of additional dependencies are `qcrbox[client]` and `qcrbox[server]`, but these are mostly relevant
for targeted installation inside the Docker containers.


## Installing pre-commit hooks (for development on `qcrbox`)

For development on `qcrbox`, you need to install the [pre-commit](https://pre-commit.com/) hooks for linting,
auto-formatting, etc. Make sure you have the dev dependencies installed (as described above), which ensures
that the `pre-commit` tool is installed. Then run:
```
(venv) $ pre-commit install
```
Now `pre-commit` will run automatically on `git commit`.


## Verify the installation

Verify that we can now run the `qcb` command line tool, which is the main CLI interface
for interacting with QCrBx from the command line.

```console exec="1" source="console"
$ qcb
```

```console exec="1" source="console"
$ qcb version
```

```console exec="1" source="console"
$ qcb list components
```

```console exec="1" source="console"
$ qcb list components --all
```

## Build a container to test the installation

Try building a component by typing:
```
$ qcb build qcrboxtools
```

!!! warning
    There were issues with running hatchling under Windows 11, especially when using a python version from the Windows Store. If ``qcb build`` fails during ``Building Python package: qcrbox`` with a code 106 error (or silent without ``-v``), try the following remedy:

      1. Uninstall the Windows Store python version using the app uninstall of windows
      2. Get a new installer from [python.org](https://www.python.org/)
      3. Install. Activate support for long paths and add python to path
      4. Delete the venv folder and create a new one with the new python version
