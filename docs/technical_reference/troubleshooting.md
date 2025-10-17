# Troubleshooting & FAQ

If you encounter any problems or questions when developing application containers, look below for potential solutions.

## How can I speed up the building of core QCrBox containers?

You can [use prebuilt images from a container repository](../how_to_guides/updating_container_registry.md) to reduce build times.

## Why are the core QCrBox containers taking so long to build despite having been built before?

There's a known Docker caching issue in the Developer Release with the `base-novnc` and `base-wine` containers (see [this issue](https://github.com/QCrBox/QCrBox/issues/556)), which means that cached versions of these built containers aren't used.

## When building QCrBox components, encounter the following error (with ... representing hashes and IDs):

```
ERROR: failed to prepare sha256:... as ...: max depth exceeded
```

This is caused by the Docker build process erroneously performing an infinitely recursive search of container dependencies due to an outdated `base-ancestor` QCrBox components. To resolve, remove all QCrBox containers and build images from the Docker cache (using `docker container rm` and `docker image rm` for each one), and then rebuild all the QCrBox components.

- If you are modiyfing the core QCrBox platform Pydantic models (held in `pyqcrbox.sql_models`), and your services YAML definitions are failing validation checks from the registry when they start up, this can be caused by older cached Pydantic models being held by the registry service in its Docker volume. You can resolve this by:

1. Shutting down all QCrBox services using `qcb down`
1. Removing the volume, using `docker volume rm qcrbox_qcrbox-registry-db`
1. Restarting the core QCrBox services using `qcb up --all`
1. Restarting your custom services using, e.g. `qcb up your-service-name`

For more information, see https://github.com/QCrBox/QCrBox/issues/611.

## What if I want to pass two separate CIF files to a single container command using QCrBox?

If you have a command which needs two independent CIFs, then only one of those can be a `QCrBox.cif_data_file`. The other has to be a `QCrBox.data_file`, meaning it loses the Cif2Cif translation. The reason why only one can be a `QCrBox.cif_data_file` is because a second `QCrBox.cif_data_file` in the frontend is assumed to be an ancestor of the first CIF, so you are unable to upload a second CIF. The workaround is for the second CIF to be treated as a generic `QCrBox.data_file` instead.

## What if I want to use to use the cif2cif translation functions from within an application container?

In order to operate, the cif2cif translation functions require access to the application container YAML configuration file. In this scenario, you may call the cif2cif functions from within your own Python code (that is invoked when a command executes), but the location of the YAML file needs to be referenced using an absolute path in in this instance, to ensure that these functions are able to find it. This is because commands execute from within their own separate working directory, so please use something like the Python `pathlib` library to construct an absolute file path if you need to use the YAML.
