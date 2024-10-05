# Project Phases / Roadmap

## Project Phases and Achievements

- Identification and negotiation of requirements combined with explorative prototyping, resulting in iterative refinement of the project vision and scope.

- Empowering developers of crystallographic applications to package up their software and plug it into the QCrBox platform. Our key achievement is being able to support both of the following goals at the same time:

    - Isolation of individual software’s dependencies and installation and the way in which applications expect input (data & parameters); support for both command line and interactive GUI applications, both Linux/Mac and Windows.

    - Consistent integration in the QCrbox platform so that disparate applications can exchange data and be combined into coherent workflows.

    We have optimised the process to eliminate the need for specialised technical knowledge as much as possible. We are continuously improving the tooling and reducing the amount of work needed by developers to integrate their software into QCrBox.

- Robust architectural design. We used the integration of the following existing crystallographic applications to inform the design process and validation:

    - Olex2
    - CrysAlisPro
    - CrystalExplorer
    - MoPro
    - Eval
    - XHARPy
    - ... _integration of further software is ongoing_ ...


- Graphical User Interface (GUI): initial design -> prototypes -> formal frontend development

- Tooling to ensure an easy and smooth experience for developers
    - Easy script-based installation
    - Automatic setup of development environment
    - Interactive dialog-driven templating for integrating new software into QCrBox
    - Command line tool as the “entrypoint” for interacting with any aspects of QCrBox (e.g. deployment, starting/stopping containerised applications; invoking non-interactive commands)
    - Python module for high-level programmatic interaction with QCrBox (via the API)

- Documentation (incl. project overview, tutorials, how-to guides)


## Ongoing Work / Roadmap

- Development of the user-facing graphical interface to build and run crystallographic workflows via the QCrBox platform
- Data management & decentralised data handling
- Gathering feedback from users & developers and enhancing the experience of working with QCrBox
- Optimising the deployment experience & support for multi-user setups
- Enhancing support for different deployment scenarios, e.g:
    - Cloud-based deployments
    - Dedicated server hosted & managed by a university department or group
    - Installation on personal devices (laptop or desktop computer)
