# Setting up a development environment

## Quick start

Make sure you have the necessary prerequisites installed (see [below](#prerequisites) for detailed instructions).

- Docker / Docker Compose
- WSL2 (Windows Subsystem for Linux 2) - _only required for Windows_

Then run the following command to download the setup script and install QCrBox.
```bash
$ bash <(curl -fsSL https://raw.githubusercontent.com/QCrBox/QCrBox/dev/scripts/qcrbox_setup.sh)
```

If you prefer to inspect the script before running it, you can download it first and then run it manually:
```bash
$ curl -fsSL https://raw.githubusercontent.com/QCrBox/QCrBox/dev/scripts/qcrbox_setup.sh > qcrbox_setup.sh
$ bash qcrbox_setup.sh
```

!!! info inline end
    If you are using Windows, make sure to run the above command in a WSL2 terminal,
    not in PowerShell or the Windows command prompt.

The setup script will give you the option to automatically install Devbox and Nix (if they are not already installed).
Then it will clone the QCrBox repository and create an isolated development environment inside it. This development
environment includes a virtual environment for the `pyqcrbox` Python package and all other dependencies needed to
run and develop QCrBox. Once installation is complete, you can activate the development shell by running `devbox shell`.

QCrBox relies on [Devbox](https://www.jetify.com/devbox/docs/) to provide a consistent development environment.
Internally, Devbox uses the [Nix package manager](https://nixos.org/) to install packages into isolated environments.

The QCrBox setup script will give you the option to automatically install Devbox and Nix if they are not already installed.


## Verify the installation

Verify that we can now run the `qcb` command line tool, which is the main CLI interface
for interacting with QCrBx from the command line.

```console exec="1" source="console"
$ qcb
```

```console exec="1" source="console"
$ qcb version
```

```console exec="1" source="console"
$ qcb list components
```

```console exec="1" source="console"
$ qcb list components --all
```

You can also test that the components build and run correctly by running a Devbox script,

```console
$ devbox run test-api
```

## Build a container to test the installation

Try building a component by typing:

```console exec="1" source="console"
$ qcb build qcrboxtools
```

## Restart QCrBox

In the event of disaster, it is possible to destroy the containers and restart QCrBox by using a Devbox script,

```console
devbox run restart
```

## Install QCrBox front-end

In order to drive the QCrBox platform, ensure you also have deployed the QCrBox web front-end. You can find instructions to deploy it [here](https://github.com/QCrBox/QCrBoxFrontend/blob/main/documentation/deployment_instructions.md).

## Prerequisites

The following dependencies need to be installed manually.

**Docker** and **Docker Compose**

The easiest way to install Docker is to use the [Docker Desktop](https://docs.docker.com/desktop/)
(scroll down to find the box titled "Install Docker Desktop" and click on the link for your operating system).

If you don't care about a graphical user interface (for example, if you are working on a remote server),
you can also manually install [Docker Engine](https://docs.docker.com/engine/install/) and
[Docker Compose](https://docs.docker.com/compose/install/).


!!! info inline end
    QCrBox has been tested with the version of Docker listed below, but other recent versions should
    also work. Please [create an issue](https://github.com/QCrBox/QCrBox/issues/new){:target="_blank"}
    on GitHub if you experience any problems.

    Note that QCrBox requires Docker Engine version 25.0 or later due to the use of `--start-interval`
    in container [health checks](https://docs.docker.com/reference/dockerfile/#healthcheck).

```
$ docker version
Client:
 Version:           24.0.9
 API version:       1.43
 Go version:        go1.22.5
 Git commit:        v24.0.9
 Built:             Thu Jan  1 00:00:00 1970
 OS/Arch:           linux/amd64
 Context:           default

Server: Docker Engine - Community
 Engine:
  Version:          27.1.1
  API version:      1.46 (minimum version 1.24)
  Go version:       go1.21.12
  Git commit:       cc13f95
  Built:            Tue Jul 23 19:57:01 2024
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          1.7.19
  GitCommit:        2bf793ef6dc9a18e00cb12efb64355c2c9d5eb41
 runc:
  Version:          1.7.19
  GitCommit:        v1.1.13-0-g58aa920
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0

$ docker compose version
Docker Compose version v2.21.0
```
