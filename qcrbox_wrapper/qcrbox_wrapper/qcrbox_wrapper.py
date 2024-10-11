# Copyright 2024 Paul Niklas Ruth.
# SPDX-License-Identifier: MPL-2.0
"""
This file is licenced under the MPL-2.0 license. For more information see the LICENSE file
at https://github.com/QCrBox/QCrBox/blob/dev/LICENSE.

This module provides a comprehensive interface for interacting with the QCrBox server,
enabling the execution of commands, retrieval of application information, and management
of calculation statuses. It defines classes for wrapping the QCrBox API, representing
applications, commands, and calculations, alongside a utility class for path management
within QCrBox Docker containers. Additionally, it utilizes namedtuples for structured
representation of command parameters and calculation statuses.

Classes
-------
QCrBoxWrapper : Interface to interact with the QCrBox server.
QCrBoxApplication : Represents an application within QCrBox.
QCrBoxCommand : Represents a command for execution on the QCrBox server.
QCrBoxCalculation : Represents a calculation performed on the QCrBox server.
QCrBoxPathHelper : Manages file paths within QCrBox Docker containers.
"""

import json
import os
import pathlib
import time
import urllib
import urllib.request
from functools import lru_cache
from itertools import count
from typing import Any, Optional, Union

import httpx

from pyqcrbox import sql_models

from .qcrbox_application import QCrBoxApplication
from .qcrbox_command import QCrBoxCommand, QCrBoxCommandBase, QCrBoxInteractiveCommand, QCrBoxParameter


@lru_cache(maxsize=5)
def get_time_cached_app_answer(web_client: httpx.Client, ttl_hash: int) -> list[dict[str, Any]]:
    """
    Retrieves cached application answers from the QCrBox server.

    This function is memoized to cache responses based on the server URL and a
    time-to-live (TTL) hash. It is designed to reduce the number of requests
    made to the server for the same information within a short period.

    Parameters
    ----------
    web_client : httpx.Client
        The web client to use for connecting to the QCrBox server.
    ttl_hash : int
        A hash value representing the time-to-live for the cache. This value
        controls the cache's validity period to prevent outdated information.

    Returns
    -------
    dict[str, str]
        The response from the QCrBox server, typically a list of application details.

    Note
    ----
    The way this function is implemented the cached value is cached within fixed
    intervals, instead of for a fixed time.
    """
    del ttl_hash
    response = web_client.get("/applications")
    return response.json()


def get_ttl_hash(seconds: int = 20) -> int:
    """
    Generates a hash based on the current time and a specified number of seconds.

    This function divides the current UNIX timestamp by the specified number of
    seconds and rounds the result to produce a hash. This hash can be used to
    implement caching mechanisms where cached values expire after a certain duration.

    Parameters
    ----------
    seconds : int, optional
        The number of seconds to divide the current UNIX timestamp by, by default 20.

    Returns
    -------
    int
        The generated hash value.
    Note
    ----
    The way this function is implemented the cached value is cached within fixed
    intervals, where the rounded seconds value is the sameinstead of for a fixed
    time.
    """
    return round(time.time() / seconds)


class QCrBoxWrapper:
    """
    Provides an interface to interact with the QCrBox server.

    Parameters
    ----------
    server_addr : str
        The address/IP of the QCrBox server.
    server_port : int
        The port on which the QCrBox server is running.
    gui_infos : Optional[dict[str, dict[str, Union[int, str]]]] = None
        GUI information for applications, including ports and commands that have a GUI.
        For each application containing a GUI command, the Application name should be
        the key, with another dict as the item. This dictionary needs the the entries
        "port" with the port the access the GUI, as well as an entry "commands" that
        containts a list of all the interactive commands.

    Raises
    ------
    ConnectionError
        If the connection to the QCrBox Registry Server fails.
    """

    def __init__(
        self,
        web_client: httpx.Client,
        gui_infos: Optional[dict[str, dict[str, Union[int, str]]]] = None,
    ) -> None:
        """
        Initializes the QCrBoxWrapper instance.

        Parameters
        ----------
        web_client: httpx.Client
            The web client to use for interacting with the QCrBox server.
        gui_infos : Optional[dict[str, dict[str, Union[int, str]]]] = None
            Dictionary containing the GUI information for applications, including ports
            and commands that have a GUI. For each application containing a GUI command,
            the application name should be the key, with another dict as the item. This
            dictionary needs the entries "port" with the port the access the GUI,
            as well as an entry "commands" that containts a list of all the interactive
            commands.

        Raises
        ------
        ConnectionError
            If the connection to the QCrBox Registry Server fails.
        """
        self.web_client = web_client
        self.server_url = str(web_client.base_url)
        self.server_host = self.web_client.base_url.host
        self.server_port = self.web_client.base_url.port

        # TODO Replace with commands reporting the port
        default_gui_infos = {
            "Eval1X": {"port": 12005, "commands": ["interactive"]},
            "Olex2 (Linux)": {"port": 12004, "commands": ["interactive"]},
            "CrystalExplorer": {"port": 12003, "commands": ["interactive"]},
            "CrysalisPro": {"port": 12001, "commands": ["interactive"]},
        }
        if gui_infos is None:
            self.gui_infos = default_gui_infos
        else:
            self.gui_infos = gui_infos.update(default_gui_infos)

        response = web_client.get("/")

        if "QCrBox" not in response.text:
            print(response.text)
            raise ConnectionError(f"Cannot connect to QCrBox Registry Server at {self.server_url}")

    @classmethod
    def from_server_addr(
        cls,
        server_addr: str,
        server_port: Optional[int] = None,
        gui_infos: Optional[dict[str, dict[str, Union[int, str]]]] = None,
    ) -> "QCrBoxWrapper":
        server_api_url = f"http://{server_addr}" + (f":{server_port}" if server_port is not None else "") + "/api"
        web_client = httpx.Client(base_url=server_api_url)

        # with urllib.request.urlopen(f"{server_url}") as r:
        #     response = r.read().decode("UTF-8")
        #
        # if "QCrBox" not in response:
        #     print(response)
        #     raise ConnectionError(f"Cannot connect to QCrBox Registry Server at {server_url}")

        return cls(web_client, gui_infos)

    def __repr__(self) -> str:
        return f"<QCrBoxWrapper({self.server_url!r}')>"

    @property
    def applications(self) -> list["QCrBoxApplication"]:
        """
        Retrieves a list of applications from the QCrBox server.

        Returns
        -------
        list[qcrbox_wrapper.qcrbox_wrapper_new.QCrBoxApplication]
            A list of QCrBoxApplication namedtuples.
        """
        response = get_time_cached_app_answer(self.web_client, get_ttl_hash())
        return [
            QCrBoxApplication(application_spec=sql_models.ApplicationSpecWithCommands(**app_spec), wrapper_parent=self)
            for app_spec in response
        ]

    @property
    def application_dict(self) -> dict:
        """
        Constructs a dictionary of applications for easy lookup.

        Returns
        -------
        dict
            A dictionary where keys are application names and values are
            QCrBoxApplication objects.
        """
        return {application.name: application for application in self.applications}

    @property
    def commands(self) -> list["QCrBoxCommandBase"]:
        """
        Retrieves a list of commands from the QCrBox server.

        Returns
        -------
        list[QCrBoxCommandBase]
            A list of QCrBoxCommand or QCrBoxInteractiveCommand objects.
        """
        answers = get_time_cached_app_answer(self.web_client, get_ttl_hash())

        # with urllib.request.urlopen(f"{self.server_url}/applications/") as r:
        #    answers = json.loads(r.read().decode("UTF-8"))
        app_id2name = {ans["id"]: ans["name"] for ans in answers}

        def to_gui_url(app_id, cmd_name):
            # TODO replace this with information provided from QCrBox itself.
            app_name = app_id2name[app_id]
            if app_name in self.gui_infos and cmd_name in self.gui_infos[app_name]["commands"]:
                port = self.gui_infos[app_name]["port"]
                web_url = f"http://{self.server_addr}:{port}/vnc.html?path=vnc&autoconnect=true&resize=remote"
                return web_url
            return None

        with urllib.request.urlopen(f"{self.server_url}/commands/") as r:
            answers = json.loads(r.read().decode("UTF-8"))

        prepare_commands = {
            (ans["name"][9:], int(ans["application_id"])): QCrBoxCommand(
                cmd_id=int(ans["id"]),
                name=ans["name"],
                application_id=int(ans["application_id"]),
                parameters=[QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()],
                wrapper_parent=self,
            )
            for ans in answers
            if ans["name"].startswith("prepare__")
        }

        finalise_commands = {
            (ans["name"][10:], int(ans["application_id"])): QCrBoxCommand(
                cmd_id=int(ans["id"]),
                name=ans["name"],
                application_id=int(ans["application_id"]),
                parameters=[QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()],
                wrapper_parent=self,
            )
            for ans in answers
            if ans["name"].startswith("finalise__")
        }

        commands = []
        for ans in answers:
            if any([ans["name"].startswith("prepare__"), ans["name"].startswith("finalise__")]):
                continue
            if to_gui_url(ans["application_id"], ans["name"]) is not None:
                parameters = [QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()]

                application_id = int(ans["application_id"])
                prepare_command = prepare_commands.get((ans["name"], application_id), None)
                if prepare_command is not None:
                    parameters += [par for par in prepare_command.parameters if par not in parameters]

                finalise_command = finalise_commands.get((ans["name"], application_id), None)
                if finalise_command is not None:
                    parameters += [par for par in finalise_command.parameters if par not in parameters]

                commands.append(
                    QCrBoxInteractiveCommand(
                        cmd_id=int(ans["id"]),
                        name=ans["name"],
                        application_id=int(ans["application_id"]),
                        parameters=parameters,
                        gui_url=to_gui_url(ans["application_id"], ans["name"]),
                        wrapper_parent=self,
                        run_cmd=QCrBoxCommand(
                            int(ans["id"]),
                            ans["name"],
                            int(ans["application_id"]),
                            [QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()],
                            self,
                        ),
                        prepare_cmd=prepare_command,
                        finalise_cmd=finalise_command,
                    )
                )
            else:
                commands.append(
                    QCrBoxCommand(
                        cmd_id=int(ans["id"]),
                        name=ans["name"],
                        application_id=int(ans["application_id"]),
                        parameters=[QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()],
                        wrapper_parent=self,
                    )
                )

        return commands


class QCrBoxPathHelper:
    """
    A helper class for managing file paths within QCrBox Docker containers.

    This class provides methods to convert a path to both local and QCrBox-specific
    file system paths.

    Attributes
    ----------
    local_path : pathlib.Path
        The base path in the local file system.
    qcrbox_path : pathlib.Path
        The base path in the QCrBox file system, defaults to '/mnt/qcrbox/shared_files'.

    Methods
    -------
    path_to_local(path: pathlib.Path) -> pathlib.Path
        Converts a given path to its equivalent in the local file system.
    path_to_qcrbox(path: pathlib.Path) -> str
        Converts a given path to its equivalent in the QCrBox file system, returned
        as a POSIX-style string path.
    path_to_pair(path: pathlib.Path) -> tuple
        Returns a tuple of the given path's local and QCrBox equivalents.
    """

    step_counter = count()

    def __init__(
        self,
        local_path: pathlib.Path,
        qcrbox_path: pathlib.PurePosixPath = pathlib.PurePosixPath("/mnt/qcrbox/shared_files"),
        base_dir: Optional[pathlib.Path] = None,
    ) -> None:
        """
        Initializes the QCrBoxPathHelper instance.

        Parameters
        ----------
        local_path : pathlib.Path
            The base path in the local file system.
        qcrbox_path : pathlib.PurePosixPath, optional
            The base path in the QCrBox file system (default is '/mnt/qcrbox/shared_files').
        base_dir : pathlib.Path, optional
            A subdirectory within both the local and QCrBox base paths for scoped path
            management. Defaults to None, in which case the base paths are used directly.
        """
        if str(local_path).startswith("\\wsl$\\"):
            local_path = "\\" + str(local_path)
        if base_dir is None:
            self.local_path = pathlib.Path(local_path)
            self.qcrbox_path = pathlib.PurePosixPath(qcrbox_path)
        else:
            self.local_path = pathlib.Path(local_path) / base_dir
            self.qcrbox_path = pathlib.PurePosixPath(qcrbox_path) / base_dir
        self.local_path.mkdir(exist_ok=True)

    @classmethod
    def from_dotenv(cls, dotenv_name: str, base_dir: Optional[pathlib.Path] = None) -> "QCrBoxPathHelper":
        """
        Creates an instance of QCrBoxPathHelper from environment variables defined in a .env file.

        This class method reads the specified .env file to extract the base paths for the local and
        QCrBox file systems. It then initializes and returns a new instance of QCrBoxPathHelper using
        these paths.
        Parameters
        ----------
        dotenv_name : str
            The name of the .env file to be loaded.
        base_dir : pathlib.Path, optional
            A subdirectory within both the local and QCrBox base paths for scoped path management.
            Defaults to None, in which case the base paths provided in the .env file are used directly.

        Returns
        -------
        QCrBoxPathHelper
            An instance of QCrBoxPathHelper initialized with the paths read from the .env file.

        Raises
        ------
        FileNotFoundError
            If the .env file specified by `dotenv_name` cannot be found or the required environment
            variables are not set.
        """
        import dotenv

        dotenv_path = pathlib.Path(dotenv.find_dotenv(dotenv_name))

        if not dotenv.load_dotenv(dotenv_path):
            raise FileNotFoundError(
                ".dot.env file could not be loaded. Create the pathhelper from the"
                + "__init__ method by using \n"
                + "pathhelper = QCrBoxPathhelper(\n"
                + "    local_path=<local_path_on_disc>\n"
                + f"    base_dir={base_dir}\n"
                + ")"
            )

        shared_files_path = pathlib.Path(os.environ["QCRBOX_SHARED_FILES_DIR_HOST_PATH"])
        if str(shared_files_path).startswith(r"\wsl"):
            shared_files_path = pathlib.Path("\\" + str(shared_files_path))
        elif not shared_files_path.is_absolute():
            shared_files_path = dotenv_path.parent / shared_files_path

        return cls(shared_files_path, os.environ["QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH"], base_dir)

    def path_to_local(self, path: pathlib.Path) -> pathlib.Path:
        """
        Converts a given path to its equivalent in the local file system.

        Parameters
        ----------
        path : pathlib.Path
            The path to be converted, relative to the QCrBox base path.

        Returns
        -------
        pathlib.Path
            The equivalent path in the local file system.
        """
        return self.local_path / path

    def path_to_qcrbox(self, path: pathlib.Path) -> str:
        """
        Converts a given path to its equivalent in the QCrBox file system and
        returns it as a POSIX-style string path.

        Parameters
        ----------
        path : pathlib.Path
            The path to be converted, relative to the local base path.

        Returns
        -------
        str
            The equivalent path in the QCrBox file system as a POSIX-style string.
        """
        new_path = self.qcrbox_path / path
        return pathlib.PurePosixPath(new_path)

    def path_to_pair(self, path: pathlib.Path) -> tuple:
        """
        Returns a tuple containing the given path's equivalents in both the local
        and QCrBox file systems.

        Parameters
        ----------
        path : pathlib.Path
            The path to be converted.

        Returns
        -------
        tuple
            A tuple of pathlib.Path and str, representing the local and QCrBox
            file system paths respectively.
        """
        return self.path_to_local(path), self.path_to_qcrbox(path)

    def create_next_step_folder(self) -> tuple[pathlib.Path, str]:
        """
        Creates a new folder for the next step in a sequence within the local file system
        and returns its path equivalents in both the local and QCrBox file systems.

        This method automatically increments an internal counter to keep track of the
        "step" folders (e.g., "step_1", "step_2", etc.). Each call to this method results
        in the creation of a new folder with the next step number in the local file system
        and returns both the local system path and the QCrBox file system path as a POSIX-style
        string.

        Returns
        -------
        tuple[pathlib.Path, str]
            A tuple containing the newly created folder's path in the local file system
            (as a pathlib.Path object) and its equivalent in the QCrBox file system
            (as a POSIX-style string path).
        """
        next_folder = f"step_{next(self.step_counter)}"
        self.path_to_local(next_folder).mkdir(exist_ok=True)
        return self.path_to_pair(next_folder)
