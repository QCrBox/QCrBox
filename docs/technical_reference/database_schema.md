# Database Schema

There are two mechanisms for storing (persistent) data in QCrBox: 1) an in-memory SQLite database which is constructed
by and part of the QCrBox registry and 2) a distributed NATS data management system.

## Missing Functionality

- Applications cannot be updated in the NATS data manager or in SQL to reflect changes during development. A current
  limitation is that you must delete the NATS volume to see the changes in the NATS data manager. You *should* only need
  to restart *all* of QCrBox to see changes reflected in the SQL database.
- A new dataset is created at the end of a calculation after the finalise step has been run. This should probably
  use a key-value/object store put operation, instead, to both update and version the updated data files and/or dataset.
  This will create a revision history for us as well.
- We are not tracking revisions of things pushed to the NATS data manager, e.g., each calculation could have a data file
  and revision associated with it.
- The API (api_helpers) uses both SQL and NATS. For example, getting all calculations queries the SQL data but getting
  a specific calculation queries from NATS. However, AFAIK calculations are not be tracked in SQL as an application
  container updates the calculation status only in NATS (see later sections).

## NATS Data Manager

https://docs.nats.io/nats-concepts/jetstream/key-value-store
https://faststream.airt.ai/latest/nats/jetstream/key-value/
https://faststream.airt.ai/latest/public_api/faststream/nats/NatsBroker/#faststream.nats.NatsBroker.key_value
https://faststream.airt.ai/latest/public_api/faststream/nats/NatsBroker/#faststream.nats.NatsBroker.object_storage

The NATS data manager consists of two parts: 1) a key-value store, and 2) an object store. In QCrBox, the key-value
store is typically used to store JSON metadata about applications (e.g. Olex2, Crystal Explorer), currently running
interactive session and dataset and data file metadata. The object store is used to store the contents of data files
(e.g. such as CIF files).

The object store is conceptually similar to the key-value store. The key-value store, however, has a limitation of 1MB
per key, which is not enough for storing files. Both stores store data as bytes, you therefore need to decode data
when retrieving it from either.

Key-value store:

| Table                | Description                                                                                                                                               | QCrBox Model                                                                      |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| applications         | Stores the ApplicationSpec for each application which requests registration. This also contains the commands belonging to the application.                | `pyqcbox.sql_models.application_spec.ApplicationSpec`                             |
| calculation_status   | Tracks current and previous calculations, including their output (stdout, stderr and "extra_info").                                                       | `pyqcbox.sql_models.calculation_status_event.CalculationStatusDetails`            |
| data_file_metadata   | Stores metadata about files uploaded to the QCrBox registry and which are stored in the object store, including their key in the object store.            | `pyqcbox.data_management.data_file.DataFileMetadata`                              |
| datasets             | Stores metadata about a QCrBox dataset, including an ID and the data files which belong to it.                                                            | `pyqcbox.data_management.data_file.Dataset`                                       |
| interactive_sessions | Stores metadata about past and present interactive sessions, including the command invocation request and the NATS address for the application container. | `pyqcbox.sql_models.command_spec.interactive_session_spec.InteractiveSessionSpec` |

Object store:

| Table              | Description                                                                                                            |
|--------------------|------------------------------------------------------------------------------------------------------------------------|
| data_file_contents | Contains the contents of data files. The same key is shared for the same file in the object store and key-value store. |

### Code implementation

The NATS data manager is implemented in the `pyqcrbox.data_management`, split between an abstract `DataManager` and
a concrete `NatsDataManager` class. The abstract class defines the interface for the data manager, implementing
logic for, e.g., storing and retrieving data files from the object store or adding application specifications to the
key-value store. The concrete `NatsDataManager` implements the logic for getting data into and out of the NATS
key-value and object store.

The idea is that the abstract class can be used to implement other data managers, using the same concept of retrieving
values through passing a key. However, so-far, only a NATS implementation exists.

However, there are a few other places where the NATS data manager is used:

- `pyqcrbox.svcs.persistence.NatsPersistenceAdapter`: This only deals with adding to the applications to the QCrBox
  registry. It possibly exists as a way to separate the concerns of the data manager, which typically deals with just
  datasets and data files, from this interface. It uses the same NATS broker (from faststream) to interface with the
  key-value store.
- `pyqcrbox.registry.shared.calculation_status.update_calculation_status_in_nats_kv_NEW`: this is a function which
  updates the calculation status in the NATS key-value store. It uses the same NATS broker (from faststream) to
  interface with the key-value store.

## SQLite database

In addition to NATS, there is a SQLite database which is used to store the same data as the NATS data
manager, other than a table of calculations.

| Table                    | Description                                                                                                                            |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| application              | Contains a relationship to the command table, which stores the command specifications for applications.                                |
| calculation              | Contains metadata to link a calculation to a command and an application. Includes a relationship to the calculation_staus_event table. |
| command                  | Command specifications, can be linked back to an application.                                                                          |
| calculation_status_event | Used to track changes in status for a calculation, including the status and timestamp.                                                 |
| container_instance       | One row per live application container, kept up to date via client heartbeats (see below).                                             |

The `container_instance` table stores, per live application container: the client id, the container's NATS private
inbox (unique), a foreign key to the application, the status (`idle`/`busy`/`gone`), `registered_at`/`last_seen`
timestamps, and a reserved `owner_user_id` column for future per-user container binding. Rows are created when a
container self-registers, refreshed by client heartbeats, deleted on graceful client shutdown, and marked `gone` by
the registry's stale-instance sweeper when heartbeats stop arriving.

### Code implementation

The SQL database is implemented using SQLAlchemy and SQLModel. The models are defined in `pyqcrbox.sql_models` and are
used to create the tables in the SQLite database using SQLModel, which uses Pydanatic for data validation. By default
(and in tests) the database is in-memory; in the Docker deployments it is file-backed on the `qcrbox-registry-db`
volume (via the `QCRBOX__DB__URL` environment variable), so that application specs registered via `qcb register` /
`POST /api/applications` survive registry restarts.

!!! warning "No schema migrations"
    Tables are created via `metadata.create_all` only — there is no migration tooling (e.g. Alembic). Adding a new
    table is safe, but changing columns of an existing table requires wiping the `qcrbox-registry-db` Docker volume
    (`docker volume rm qcrbox_qcrbox-registry-db`) or introducing migrations.
