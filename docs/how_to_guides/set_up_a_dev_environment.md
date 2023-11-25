# Set up a development environment

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
$ source ./venv/bin/activate
```
!!! note
    In this guide we use a "vanilla" Python [virtual environment](https://docs.python.org/3/library/venv.html)
    because it does not require any additional dependencies.
    If you use a custom package manager such as `poetry` or `conda`
    you can of course adapt the previous step to your specific setup.


## Install the `qcrbox` Python package

Let's install/update some core packages before installing the `qcrbox` dependencies (including dev dependencies).
```
(venv) $ pip install -U pip wheel setuptools
```

Next, install the `qcrbox` package itself. We start with the minimum required dependencies to run the `qcb` command line tool.
```
(venv) $ pip install -e qcrbox
```
!!! note
    Here we used the `-e` switch to install `qcrbox` in [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html).
    This means that any changes we make to the code during development are automatically picked up in our local installation
    without having to reinstall/upgrade the `qcrbox` package.

QCrBox comes with several sets of additional dependencies. If you want to build the documentation, for example, you need to run
```
(venv) $ pip install -e qcrbox[docs]
```
This will install mkdocs and a few other packages needed to build and serve the documentation.

Two other sets of additional dependencies are `qcrbox[client]` and `qcrbox[server]`, but these are mostly relevant for installation inside the Docker containers (unless you want to run the QCrBox registry server or client outside of docker during development).

Finally, you can install *all* additional dependencies by running
```
$ pip install qcrbox[all]
```


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
```

```
(venv) $ qcb list components --all
base-ancestor
base-application
qcrbox-message-bus
qcrbox-registry
shelx
```
