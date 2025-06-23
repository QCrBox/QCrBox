# Glossary

The following table lists key terms used throughout QCrBox.

| Term                      | Description |
|---------------------------|-------------|
| API Client                | A Python client responsible for sending requests to and managing responses from the QCrBox registry. |
| Application               | A software application provided by QCrBox, such as Crystal Explorer or Olex2. |
| Application Container     | A (Docker) container in which an application runs, providing also a VNC server for interactive sessions. |
| Application Specification | A YAML file containing metadata that configures an Application Container to run a specific application. |
| Client                    | An instance of `QCrBoxClient` that manages the execution and management of an Application and command requests, by the user, within an Application Container. |
| Calculation               | A representation of a running or completed job. |
| Command                   | A specific functionality or operation provided by an Application available to users. |
| Command Specification     | A section within the Application Specification YAML file that defines the commands an Application exposes to QCrBox. |
| Dataset                   | A collection of data files grouped together. |
| Data File                 | An individual file, typically a .CIF file. |
| Data and Object Store     | The storage system for persistent data, such as datasets, data files, and metadata about applications and commands. Currently, this is provided by NATS. |
| Interactive Session       | A command that launches a GUI interface for user interaction. |
| Non-interactive Session   | A command that runs without requiring user interaction. |
| Registry                  | The central registry database and message bus that registers and launches applications and their commands in response to user requests. |
| Server                    | An instance of `QCrBoxServer` responsible for managing the registry. |
| Workflow                  | A sequence of commands executed in a specific order with designated datasets. |
