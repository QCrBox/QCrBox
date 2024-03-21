# Setting up a development environment

## Check prerequisites

Make sure you have the necessary prerequisites installed.

!!! warning inline end "TODO"
    List all prerequisites and their minimum required versions.

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

```
$ python -m venv ./venv

# For Linux and Mac users:
$ source ./venv/bin/activate

# For Windows users (command line)
$ .\venv\Scripts\activate.bat

# For Windows users (Powershell)
$ .\venv\Scripts\activate.ps1
```
!!! note
    In this guide we use a "vanilla" Python [virtual environment](https://docs.python.org/3/library/venv.html)
    because it does not require any additional dependencies.
    If you use a custom package manager such as `poetry` or `conda`
    you can of course adapt the previous step to your specific setup.

Let's also update/install some core packages to ensure they are up-to-date.
```
(venv) $ python -m pip install -U pip wheel setuptools
```

## Install the `qcrbox` Python package

Next, install the `qcrbox` package itself. The following command installs the minimum required dependencies to run
the `qcb` command line tool, which acts as the command line interface for the Quantum Crystallography Toolbox.
```
(venv) $ pip install -e ./qcrbox
```
!!! note
    Here we used the `-e` switch to install `qcrbox` in [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html).
    This means that any changes we make to the code during development are automatically picked up in our local installation
    without having to reinstall/upgrade the `qcrbox` package.

### Installation with (optional) extra dependencies

QCrBox comes with several sets of additional dependencies which can be specified in square brackets after `qcrbox`.

If you want to build the documentation, for example, run the following command - this will install `MkDocs`
and a few other packages needed to build and serve the documentation.
```
(venv) $ pip install -e ./qcrbox[docs]
```

In addition, if you plan on developing QCrBox, making modifications to the code and/or submitting merge requests,
you most likely want to install the `dev` dependencies, too.
```
(venv) $ pip install -e ./qcrbox[dev]
```

Two other sets of additional dependencies are `qcrbox[client]` and `qcrbox[server]`, but these are mostly relevant
for installation inside the Docker containers (unless you want to run the QCrBox registry server or client outside
of docker during development).

Finally, you can install *all* additional dependencies by running
```
$ pip install qcrbox[all]
```


### Installing pre-commit hooks (for development on `qcrbox`)

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
```
$ qcb
Usage: qcb [OPTIONS] COMMAND [ARGS]...

  Command line interface for the Quantum Crystallography Toolbox.

Options:
  --help  Show this message and exit.

Commands:
  build    Build QCrBox components.
  docs     Build/serve the documentation.
  down     Shut down QCrBox components.
  invoke   Invoke a registered command with given arguments.
  list     List registered resources (applications, commands, etc.)
  up       Start up QCrBox components.
  version  Print the qcrbox version.
```

```
(venv) $ qcb version
0.1.dev223+gf1e848b
```

```
(venv) $ qcb list components
qcrbox-message-bus
qcrbox-registry
shelx
crystal-explorer
olex2-linux
```

```
(venv) $ qcb list components --all
base-ancestor
base-application
qcrbox-message-bus
qcrbox-registry
shelx
crystal-explorer
olex2-linux
```
