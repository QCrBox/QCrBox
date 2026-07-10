# Building and running QCrBox components using the `qcb` command line tool

!!! note
    Make sure you have followed the steps in [Setting up a development environment](set_up_a_dev_environment.md)
    and you can run `qcb --help` successfully. As a general rule, `qcb` should be run from within the cloned
    QCrBox git repository (typically from the toplevel folder, although this is not required).

## Listing available QCrBox components

Let's check which components are available in QCrBox.
```console exec="1" source="console" result="ansi"
$ qcb list components
```

This list contains the services available in QCrBox, including core components such as "qcrbox-registry", "qcrbox-nats"
and so on. The remaining components represent existing crystallographic software packages that are accessible from
QCrBox.

```
crystal-explorer
eval1x
olex2
qcrboxtools
shelx
xharpy-gpaw
```

## Building components

You can build the Docker image for a given component by running `qcb build`. For example, let's build the docker image
for Olex2. Before we run the actual build, let's use the `--dry-run` flag to inspect what would happen.
```console exec="1" source="console" result="ansi"
$ qcb build --dry-run olex2
```

You will notice that the logging output mentions additional Python packages and docker images. These are prerequisites
for running application containers such as Olex2. The `qcb` tool knows about their dependencies and builds them
automatically. You can pass the `--no-deps` flag to only build Olex2 itself (this can speed up the build during
development if you are certain that the dependencies are already up-to-date).
```console exec="1" source="console" result="ansi"
$ qcb build --dry-run --no-deps olex2
```

Ok, let's run the actual build process by removing the `--dry-run` flag. Note that the first time this command is
executed it may take a few minutes to complete.
```
$ qcb build olex2
```

Alternatively, if you want to build all available components, run:
```
$ qcb build --all
```

!!! note
    Certain components such as SHELX and Eval are disabled by default because they require password access
    for downloading executables or source code. These components will be skipped (even when using `--all`)
    unless the `--enable` flag is passed explicitly for each of these components that you'd like to enable.
    For example:
    ```
    $ qcb build --all --enable=shelx --enable=evl1x
    ```

!!! warning
    Building components that are disabled by default may require you to set certain environment variables
    or download password-protected files manually and placing them in the correct location. We will provide
    much better support for this in the future as part of the `qcb` toolchain. For the time being, please
    [get in touch](https://discord.com/invite/eU2ya5psxH) if you would like to build these and need support.


## Starting up containers

You can start the Docker container for Olex2 by running:
```
$ qcb up olex2
```
As above, if you want to start all (enabled) components, use the `--all` flag:
```
$ qcb up --all
```

`qcb up` starts a **long-running container** for each selected application ("pool"
containers). This is the right mode for container development: the container is there,
you can watch its logs, exec into it, and iterate.

## Serving QCrBox (on-demand containers)

To run QCrBox *for users* — e.g. behind the web frontend — application containers do not
need to be running in advance. `qcb serve` builds and registers the selected applications
but starts **only the core services**; the registry's orchestrator then spawns a container
on demand (per user) when an application is actually used, and reaps it again after
`QCRBOX__ORCHESTRATOR__IDLE_TIMEOUT` (default 30 min) of inactivity:

```
$ qcb serve --all
```

This requires `QCRBOX__ORCHESTRATOR__ENABLED=true` in the env file (`qcb serve` warns
otherwise). The two modes compose: you can `qcb up dummy_gui` a pool container for
development while the same stack serves other applications on demand.


## Registering application specs

Application specs are registered with the QCrBox registry automatically: `qcb up` pushes the
`config_*.yaml` spec of each started application component once the registry is healthy, and
application containers also (re-)register themselves on startup. You can also register specs
manually — for example to make an application known to the registry before (or without) starting
its container:
```
$ qcb register olex2
$ qcb register services/applications/olex2_linux/config_olex2.yaml
```
Registration is idempotent; re-registering an existing application (same slug and version) updates
its commands if they changed.

## Listing running application containers

Every running application container is tracked by the registry as a *container instance*
(kept up to date via heartbeats). To list them:
```
$ qcb list containers
```
Instances whose heartbeats stop arriving (e.g. after `docker kill`) are marked as `gone` after a
short timeout.

## On-demand container spawning

With `QCRBOX__ORCHESTRATOR__ENABLED=true` in the env file, the registry spawns application
containers on demand via the Docker API (through a locked-down socket proxy): invoking a
command — interactive or not — for an application that is registered but has no suitable
running container starts one automatically (the request blocks until the container has
registered, up to `QCRBOX__ORCHESTRATOR__SPAWN_TIMEOUT`, default 90s). Requests carrying a
user identity get a container *owned by that user*: it serves only their invocations, its
GUI route (`https://<slug>-<id>.gui.<domain>/`) is only accessible to them, and it is
reaped after `QCRBOX__ORCHESTRATOR__IDLE_TIMEOUT` (default 30 min) of sitting idle.
Containers can also be started and stopped explicitly via `POST /api/container-instances`
and `DELETE /api/container-instances/{id}`; quotas (`MAX_INSTANCES_PER_APP`,
`MAX_INSTANCES_PER_USER`, `MAX_TOTAL_INSTANCES`) and per-container resource limits
(`CONTAINER_MEMORY_LIMIT_MB`, `CONTAINER_CPU_LIMIT`, `CONTAINER_PIDS_LIMIT`) are
configurable via `QCRBOX__ORCHESTRATOR__*` env vars. Spawning requires the application's
docker image to be known to the registry, which happens automatically when specs are
registered via `qcb register` / `qcb up` / `qcb serve`. Spawned containers are labelled
`org.qcrbox.spawned=true`; a full `qcb down` removes them.

## Shutting down containers

Run the following command to shut down all running QCrBox containers:
```
$ qcb down
```


## Next steps

- Navigate to the following URL to get a fully functioning Olex2 GUI running inside your browser:

    [http://localhost:12345/gui/olex2/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true](http://localhost:12345/gui/olex2/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true){:target="_blank"}

- Read the [Tutorials](../tutorials/contents.md) to see several examples showing how to interact programmatically with crystallographic software within QCrBox.
