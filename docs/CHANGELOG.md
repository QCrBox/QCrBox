---
hide:
  - navigation
---

# Changelog

All notable changes to this project will be documented in this file.

This project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
However, there will be an initial period of stabilisation where this is not adhered to
(releases with version numbers `0.0.x`).

## [v0.1.0]

### New Features

- Added a brief guide on writing a test plan for an application container.
- Added a tutorial on adding a GUI container application to QCrBox.
- Added a troubleshooting and FAQ page.
- Included support for non-interactive commands, including stopping any long-running commands.
- Added `--prebuilt-images` option to `qcb up` to bring QCrBox up using tested images from the QCrBox container
  repository.
- Datasets can now contain multiple data files (of any type). When downloading a dataset with multiple files, a zip file
  will be returned instead of each file individually.
- Data files now track which dataset they belong to, so deleting a data file will remove it from the dataset it is in
  similar to how deleting a dataset will delete its data files.
- The version of `pyqcrbox` an application is based on is validated against the version the registry is built on to
  ensure compatibility.
- Validation criteria can optionally be set for command parameters, which validates a user's input for the value of a
  parameter.
- CIF files can be transformed between formats required for command execution. When a command has completed, the output
  CIF is merged with the original CIF to create a unified file.

### Removed Features

- We have removed the dev, docs, invoke and status options from the `qcb` CLI.
- Removed `qcrbox-nextflow` container which was unused.
- `cli_command` is no longer a valid `implemented_as` type for non-interactive commands.

### Enhancements

- Split the Python container tutorial into two, so the application creation part is more generic and reusable for the interactive GUI tutorial.
- Added link to front-end deployment instructions at the end of the development environment set up documentation.
- Added validation steps to the QCrBox Python application wrapping tutorial.
- The registry API now uses LiteStar dependency injection, improving management of the NATS server.
- Renamed `DataFileManager` to `DataManager` to better reflect that is manages more than just data files
- Added a new tests to test the DataManager service, non-interactive commands and new API endpoints.
- Additional fields have been added to the payload for the dataset API endpoints.
- Parameter parsing and preparation are not deal with by commands, rather than the registry.
- Command execution has been cleaned up into smaller, more testable, methods to streamline execution.
- Inputs and outputs for commands are stored in their own temporary directories, to prevent situations where
  input/output form previous commands would interfere. These directories are removed once a command has finished.
- The application types in `qcb init` have been given more descriptive names: "CLI" -> "Non-interactive Command" and
  "GUI (Linux)" -> "Interactive GUI (Linux)". We have also reintroduced the "Interactive GUI (Windows)" application
  which lets you build an interactive application based on a Windows application running via Wine.
- Improved error message return from command invocation/ending API endpoints when NATS is the reason for failure.
- `PythonCallable` commands can now also return a `pathlib.Path` object in addition to a `str` of a file path.
- Additional automated developer tests have been added for the CIF2CIF translation for command execution.
- The Robot Framework test suites have been cleaned up and refactored.
- And lots more!

### Issues Fixed

- Updated tutorial docs to match the core QCrBox platform changes.
- Fixed an unneeded and failing type validation check in the COD Check example service due to parameter handling updates.
- Fixed an issue where the `DataManager` would lose connection to the NATS server when it had too many files.
- Replaces an obscure error message when a wrong `QCrBox.cif_data_file` or `QCrBox.data_file` parameter with a more
  helpful one.
- Fixed an issue where `qcb up` would use the wrong version ID for `pyqcrbox` when building service containers.
- Fixed an issue where `qcb list` would use the wrong URL and port number for the registry API.
- Fixed linting issues raised by `ruff` for `qcb`.
- Fixed an issue where the `base-ancestor` image wouldn't build because `conda` couldn't resolve the environment
  dependencies.
- Fixed an issue where environment variables were unset causing applications not to launch
- Fixed an issue where the output cif parameter was not being used correctly
- Fixed an issue where `qcb init` would not create a valid template for interactive applications
- Fixed an issue where cif files would become lost during command execution, which resulted in incorrect unified cifs
  being returned to the registry.
- And lots more!

### Documentation

- Added how to guide on using the QCrBox Azure Container Repository.
- Updated the how to guide on testing QCrBox.
- Added a technical reference page on parameter specification.
- Added further in-code and developer documentation.

## [icdm-2025]

### New Features

- Implemented persistence of imported data files and associated metadata. ([#352](https://github.com/QCrBox/QCrBox/issues/352))
- Added data quality container ([#301](https://github.com/QCrBox/QCrBox/issues/301)))
- Added deployment script (`scripts/deploy.sh`). ([#381](https://github.com/QCrBox/QCrBox/issues/381))
- Interactive GUI sessions can now be started with input files that were previously imported.
  ([#345](https://github.com/QCrBox/QCrBox/issues/345), [#354](https://github.com/QCrBox/QCrBox/issues/354))
- And lots more!

### Enhancements

- Added template for pull requests. ([#356](https://github.com/QCrBox/QCrBox/issues/356))

### Issues Fixed

- Fixed an error when running `qcb build`. ([#335](https://github.com/QCrBox/QCrBox/issues/335))
- Fixed formatting checks in CI runs. ([#370](https://github.com/QCrBox/QCrBox/issues/370))
- Fixed missing dependency, leading to startup errors. ([#368](https://github.com/QCrBox/QCrBox/issues/368))
- Fixed a bug that prevented pre-build scripts from being run if the build is invoked from a subdirectory. ([#385](https://github.com/QCrBox/QCrBox/issues/385))
- Fixed an issue that prevented the deployment script from running. ([#393](https://github.com/QCrBox/QCrBox/issues/393))
- Fixed an issue that prevented the Olex2 docker image from being built. ([#394](https://github.com/QCrBox/QCrBox/issues/394))

### Other changes

- By default, containers now listen on all interfaces rather than just localhost.

### Development

- Added dummy GUI application for testing of interactive sessions. ([#364](https://github.com/QCrBox/QCrBox/issues/364))

## [v0.0.2]

### New Features

- Added Traefik as a dynamic reverse proxy. ([#225](https://github.com/QCrBox/QCrBox/issues/225))
- Added Devbox configuration to enable reproducible, automated setup. ([#258](https://github.com/QCrBox/QCrBox/issues/258))
- Added script for a guided, automated installation of the QCrBox development environment.
- Added 'qcb validate' command to convenient allow validation of application config yaml files.
- Added support for 'one_of' in application config yaml files to specify alternative options for cif entries.
- Added a (non-interactive) dummy application for testing and debugging. ([#281](https://github.com/QCrBox/QCrBox/issues/281))
- Added a devbox command to run the QCrBox server in "dev" mode (outside a Docker container and with auto-reloading enabled). ([#308](https://github.com/QCrBox/QCrBox/issues/308))

### Enhancements

- CLI command outputs now use rich text formatting by default (this can be disabled by setting `QCRBOX__CLI__DISABLE_RICH=true`).
- Improved interaction between WSL and Windows (powered by [wslu](https://github.com/wslutilities/wslu)). ([#274](https://github.com/QCrBox/QCrBox/issues/274)

### Issues Fixed

- Browser windows now open correctly under WSL. ([#274](https://github.com/QCrBox/QCrBox/issues/274)
- Fixed a build issue under WSL. ([#335](https://github.com/QCrBox/QCrBox/issues/335))

### Documentation

- How-to guide on building and running components using the `qcb` command line tool. ([#167](https://github.com/QCrBox/QCrBox/issues/167))
- Output of code blocks is now coloured correctly. ([#194](https://github.com/QCrBox/QCrBox/issues/194))
- Updated instructions for setting up a development environment using the new installation script. ([#287](https://github.com/QCrBox/QCrBox/issues/287))
- The website has been extended with a landing page and a description of the project phases and roadmap.

## [v0.0.1]

### New Features

- Docker base images:
  - `base-application`
  - `base-novnc` [#39](https://github.com/QCrBox/QCrBox/issues/39)
- Core components:
  - `qcrbox-message-bus` [#9](https://github.com/QCrBox/QCrBox/issues/9)
  - `qcrbox-registry` [#13](https://github.com/QCrBox/QCrBox/issues/13)
  - `qcrbox-nextflow` [#60](https://github.com/QCrBox/QCrBox/issues/60)
  - `qcrboxtools` [#120](https://github.com/QCrBox/QCrBox/issues/120)
- Crystallographic applications:
  - CrystalExplorer [#44](https://github.com/QCrBox/QCrBox/issues/44)
  - Olex2 [#46](https://github.com/QCrBox/QCrBox/issues/46)
  - Eval [#116](https://github.com/QCrBox/QCrBox/issues/116)
  - XHARPy ([#124](https://github.com/QCrBox/QCrBox/issues/124))
- CLI tool (`qcb`) for common development and deployment tasks. ([#10](https://github.com/QCrBox/QCrBox/issues/10), [#164](https://github.com/QCrBox/QCrBox/issues/164))
- Python package (`qcrbox`) to interact with QCrBox from Python code. ([#14](https://github.com/QCrBox/QCrBox/issues/14))
- The base image now includes [cctbx](https://cci.lbl.gov/docs/cctbx/) and [QCrBoxTools](https://github.com/Niolon/QCrBoxTools.git). ([#53](https://github.com/QCrBox/QCrBox/issues/53))
- Support for creating boilerplate scaffolding for new applications to be integrated with a QCrBox instance. ([#75](https://github.com/QCrBox/QCrBox/issues/75))

### Documentation

- Created documentation skeleton. ([#2](https://github.com/QCrBox/QCrBox/issues/2))
- Set up GitHub Actions for continuous deployment of the [docs](https://qcrbox.github.io/QCrBox/) to GitHub pages. ([#11](https://github.com/QCrBox/QCrBox/issues/11))
- Added README file. ([#139](https://github.com/QCrBox/QCrBox/issues/139))
- How-to guide on how to set up a development environment. ([#24](https://github.com/QCrBox/QCrBox/issues/24))
- How-to guide for using the cif building blocks provided by QCrBoxTools. ([#71](https://github.com/QCrBox/QCrBox/issues/71))
- Tutorial on how to integrate a command line program into QCrBox. ([#79](https://github.com/QCrBox/QCrBox/issues/79))
- Tutorial on how to integrate Python functionality into QCrBox. ([#80](https://github.com/QCrBox/QCrBox/issues/80)
- Jupyter notebooks with examples on how to interact with commands exposed by QCrBox (for Olex2, Eval14/15, XHARPy, CrystalExplorer, QCrBoxTools). ([#126](https://github.com/QCrBox/QCrBox/issues/126))

### Bugs fixed

- Ensured that the `qcb` tool works cross-platform, including on Windows. ([#76](https://github.com/QCrBox/QCrBox/issues/76))
- Line endings of text files checked out in the git working tree are always normalised to `LF` to avoid runtime errors on Windows. ([#132](https://github.com/QCrBox/QCrBox/issues/132))
- Command registration and internal error handling by the server. ([#172](https://github.com/QCrBox/QCrBox/issues/172))
- The build process using `qcb` on Windows has been fixed and made more robust. ([#156](https://github.com/QCrBox/QCrBox/issues/156))

### Internal changes & improvements

- The base images now use the [mamba](https://mamba.readthedocs.io/) package manager, resulting in much faster build times than using `conda`.
- All QCrBox-specific Python packages are now installed in the base mamba environment. The separate Python virtual environment has been removed. ([#54](https://github.com/QCrBox/QCrBox/issues/54))
- Python code is linted and auto-formatted using [ruff](https://docs.astral.sh/ruff/). [#64](https://github.com/QCrBox/QCrBox/issues/64)
- Each application's docker compose configuration now lives in its dedicated subfolder (`services/application/<application_folder>`) instead of in the toplevel `docker-compose.yml` file. ([#78](https://github.com/QCrBox/QCrBox/issues/78))
- The folder structure in `qcrbox/cli/subcommands` has been simplified by removing an extra level of subfolders. ([#90](https://github.com/QCrBox/QCrBox/issues/90))

[unreleased]: https://github.com/QCrBox/QCrBox/compare/v0.0.2...master
[v0.0.2]: https://github.com/QCrBox/QCrBox/compare/v0.0.1...v0.0.2
[v0.0.1]: https://github.com/QCrBox/QCrBox/compare/initial_commit...v0.0.1
