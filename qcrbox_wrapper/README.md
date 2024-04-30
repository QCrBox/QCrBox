# qcrbox_wrapper

[![License](https://img.shields.io/badge/license-MPL2.0-blue.svg)](https://github.com/QCrBox/QCrBox/blob/dev/LICENSE)

## Description

`qcrbox_wrapper` is a Python package that provides a wrapper for the QCrBox libraries WebAPI, allowing easy integration of QCrBox functionality into your Python projects. It is meant to use a minimal amount of external dependencies. At the moment the only dependency is the `python-dotenv` package if you want to load from a `.env.dev` file. Howeever, the `qcrbox_wrapper` package can also be used without that functionality.

## Installation

To install qcrbox_wrapper, you can use pip:

```bash
pip install -e ./qcrbox_wrapper
```

However, all the functionality is contained within a single file (qcrbox_wrapper.py). So you can also just copy that file to your project, if that makes working with QCrBox more convenient.

## Use

There are two main classes two start the interaction with the `qcrbox_wrapper`: Use `QCrBoxWrapper` for the interaction with your QCrBox Registry and `QCrBoxPathHelper` to more easily work with the two paths QCrBox uses. The one that that your local operating system sees and the one that the QCrBox containers see.

### Interacting with QCrBox

Just create a new object from the class `QCrBoxWrapper` using the address of the QCrBox Inventory you want to use as well as its port (default: 11000).

```python
from qcrbox_wrapper import QCrBoxWrapper

# Create a new object from the class QCrBoxWrapper
qcrbox = QCrBoxWrapper("127.0.0.1", port=11000)

# print a list of available application containers
print(qcrbox.application_dict.keys())

# access an application by name
application = qcrbox.application_dict["application_name"]

# print the available commands in that application:
print(help(application))

# Call a command and get the calculation object.
calc = application.command_name(*args, **kwargs)

# commands are executed asynchonously, if you want to wait until the calculation is done:
calc.wait_while_running(1.0)

# print the status of the calculation
print(calc.status)
```

### Using the `QCrBoxPathHelper`
```python
# Create a new object by providing the local path
# Base dir is an additional subfolder, that you might use for that step etc.
path_helper = QCrBoxPathHelper('local/shared_files/path', 'base_dir')

# ALTERNATIVELY use the path from the .dot.env file
path_helper = QCrBoxPathHelper.from_dotenv('path/to/.env.dev', 'base_dir')

# get the local and container path to a file in base_dir
local_path, container_path = path_helper.path_to_pair('example_file.cif')

# If you work with multiple steps and want to create a step_0 folder
local_path, container_path = path_helper.create_next_step_folder()

# The path helper has an internal counter so creating step one is the same
local_path, container_path = path_helper.create_next_step_folder()
```