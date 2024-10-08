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

This list contains three "core" components (`qcrbox-message-bus`, `qcrbox-registry`, `qcrbox-nextflow`).
You don't need to worry about these for using and interacting with QCrBox - they will be started automatically
when you spin up the crystallographic application components.

The remaining components represent existing crystallographic software packages that are accessible from QCrBox.
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

!!! warning
    If you want start up containers after previously shutting them down (using `qcb down` as described below),
    you must currently manually delete the Docker volume where the QCrBox server stores information about available
    components:

    ```
    # Step 1: Shut down all running containers
    $ qcb down

    # Step 2: Delete the Docker volume containing the QCrBox server database
    $ docker volume rm qcrbox_qcrbox-registry-db

    # Step 3: Now you can start up the components again and things should work as expected.
    $ qcb up --all
    ```

    This is of course less than ideal. The underlying issue is being addressed in a [refactoring branch](https://github.com/QCrBox/QCrBox/pull/128)
    that will be merged very soon, at which point you will be able to shut down and spin up components ad libitum
    without manual intervention.


## Shutting down containers

Run the following command to shut down all running QCrBox containers:
```
$ qcb down
```


## Next steps

- Navigate to the following URL to get a fully functioning Olex2 GUI running inside your browser:

    [http://localhost:12004/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true](http://localhost:12004/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true){:target="_blank"}

- Read the [Tutorials](../tutorials/contents.md) to see several examples showing how to interact programmatically with crystallographic software within QCrBox.
