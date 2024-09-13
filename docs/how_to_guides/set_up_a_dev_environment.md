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

## Build a container to test the installation

Try building a component by typing:

```console exec="1" source="console"
$ qcb build qcrboxtools
```


## Improving File Access Speed on Windows

When using Docker on Windows with WSL2 (Windows Subsystem for Linux 2), file access in shared folders can be slow,
which can cause problems for processes like data reduction. By default, the shared files are stored in
`<project_folder>/shared_files/` on your Windows drive. You should move the shared files to your WSL2 partition for faster access.

### Steps

1. Open WSL2:
   - Open a Windows command prompt
   - Type `wsl` and press Enter

2. Create a new folder in your WSL2 home directory using the `mkdir` command:
   - **Important**: Use lowercase letters only for the folder name!
   - Example: `mkdir qcrbox_shared_files`

3. Locate your Linux username:
   - Look at the command prompt; your username is before the @ symbol
   - Example: If you see `john@DESKTOP-123:~$`, your username is "john"

4. Update your QCrBox's `.env.dev` file in the QCrBox base directory:
   - Find the line starting with `QCRBOX_SHARED_FILES_DIR_HOST_PATH`
   - Replace it with one of these options:
     - For Windows 10:

       ```text
       QCRBOX_SHARED_FILES_DIR_HOST_PATH='\\wsl$\Ubuntu\home\<your_linux_username>\<folder_name>'
       ```

     - For Windows 11:

       ```text
       QCRBOX_SHARED_FILES_DIR_HOST_PATH='\\wsl.localhost\Ubuntu\home\<your_linux_username>\<folder_name>'
       ```

   - Example:

     ```text
     QCRBOX_SHARED_FILES_DIR_HOST_PATH='\\wsl$\Ubuntu\home\john\qcrbox_shared_files'
     ```

   - Make sure to use single quotes around the path


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
