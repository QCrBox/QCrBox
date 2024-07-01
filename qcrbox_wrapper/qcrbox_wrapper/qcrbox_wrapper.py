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

Namedtuples
-----------
QCrBoxParameter : Represents a parameter for QCrBoxCommand.
QCrBoxCalculationStatus : Represents the status of a calculation in QCrBox.
"""

import json
import os
import pathlib
import textwrap
import time
import urllib
import urllib.request
import webbrowser
from collections import namedtuple
from functools import lru_cache
from itertools import count
from textwrap import dedent
from typing import Dict, List, Optional, Tuple, Union


@lru_cache(maxsize=5)
def get_time_cached_app_anwer(server_url: str, ttl_hash: Optional[int] = None) -> Dict[str, str]:
    """
    Retrieves cached application answers from the QCrBox server.

    This function is memoized to cache responses based on the server URL and a
    time-to-live (TTL) hash. It is designed to reduce the number of requests
    made to the server for the same information within a short period.

    Parameters
    ----------
    server_url : str
        The URL of the QCrBox server.
    ttl_hash : Optional[int]
        A hash value representing the time-to-live for the cache. This value
        controls the cache's validity period to prevent outdated information.

    Returns
    -------
    Dict[str, str]
        The response from the QCrBox server, typically a list of application details.

    Note
    ----
    The way this function is implemented the cached value is cached within fixed
    intervals, instead of for a fixed time.
    """
    del ttl_hash
    with urllib.request.urlopen(f"{server_url}/applications/") as r:
        answers = json.loads(r.read().decode("UTF-8"))
    return answers


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


QCrBoxParameter = namedtuple("QCrBoxParameter", ["name", "dtype"])
QCrBoxParameter.__doc__ = """
Represents a parameter for a QCrBoxCommand in QCrBox.

Attributes
----------
name : str
    Name of the parameter.
dtype : str
    Data type of the parameter.
"""

QCrBoxCalculationStatus = namedtuple(
    "QCrBoxCalculationStatus",
    ["calculation_id", "command_id", "started_at", "status", "status_details"],
)
QCrBoxCalculationStatus.__doc__ = """
Represents the status of a calculation in QCrBox.

Attributes
----------
calculation_id : int
    Unique identifier for the calculation.
command_id : int
    ID of the command that initiated the calculation.
started_at : str
    Timestamp when the calculation started.
status : str
    Status of the calculation (e.g., 'running', 'completed').
status_details : dict
    Detailed status information of the calculation.
"""


class UnsuccessfulCalculationError(Exception):
    def __init__(self, status: "QCrBoxCalculationStatus"):
        try:
            error_message = status.status_details["details"]["msg"]
        except KeyError:
            error_message = "No error message available"

        msg = dedent(f"""\
            Calculation with id {status.calculation_id} does not have the status completed but {status.status}.

            Potential error message:
            {error_message}
        """).strip()

        super().__init__(msg)


class InteractiveExecutionError(Exception):
    pass


class TimeoutError(Exception):
    pass


class QCrBoxWrapper:
    """
    Provides an interface to interact with the QCrBox server.

    Parameters
    ----------
    server_addr : str
        The address/IP of the QCrBox server.
    server_port : int
        The port on which the QCrBox server is running.
    gui_infos : Optional[Dict[str, Dict[str, Union[int, str]]]] = None
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
        server_addr: str,
        server_port: int,
        gui_infos: Optional[Dict[str, Dict[str, Union[int, str]]]] = None,
    ) -> None:
        """
        Initializes the QCrBoxWrapper instance.

        Parameters
        ----------
        server_addr : str
            The address/IP of the QCrBox server.
        server_port : int
            The port on which the QCrBox server is running.
        gui_infos : Optional[Dict[str, Dict[str, Union[int, str]]]] = None
            Dictionary containing the GUI information for applications, including ports
            and commands that have a GUI. For each application containing a GUI command,
            the application name should be the key, with another dict as the item. This
            dictionary needs the the entries "port" with the port the access the GUI,
            as well as an entry "commands" that containts a list of all the interactive
            commands.

        Raises
        ------
        ConnectionError
            If the connection to the QCrBox Registry Server fails.
        """
        self.server_addr = server_addr
        self.server_port = server_port

        # TODO Replace with commands reporting the port
        default_gui_infos = {
            "Eval1X": {"port": 12005, "commands": ["interactive"]},
            "Olex2 (Linux)": {"port": 12004, "commands": ["interactive"]},
            "CrystalExplorer": {"port": 12003, "commands": ["interactive"]},
            "CrysalisPro": {"port": 12001, "commands": ["interactive"]},
            "MoProSuite": {"port": 12006, "commands": ["interactive"]},
        }
        if gui_infos is None:
            self.gui_infos = default_gui_infos
        else:
            self.gui_infos = gui_infos.update(default_gui_infos)

        with urllib.request.urlopen(f"{self.server_url}") as r:
            answers = json.loads(r.read().decode("UTF-8"))

        if "QCrBox" not in answers:
            print(answers)
            raise ConnectionError(f"Cannot connect to QCrBox Registry Server at {self.server_url}")

    @property
    def server_url(self) -> str:
        """
        Constructs the full URL of the QCrBox server.

        Returns
        -------
        str
            The server URL.
        """
        return f"http://{self.server_addr}:{self.server_port}"

    @property
    def applications(self) -> List["QCrBoxApplication"]:
        """
        Retrieves a list of applications from the QCrBox server.

        Returns
        -------
        List[QCrBoxApplication]
            A list of QCrBoxApplication namedtuples.
        """
        answers = get_time_cached_app_anwer(self.server_url, get_ttl_hash())
        return [
            QCrBoxApplication(
                int(ans["id"]),
                ans["name"],
                ans["version"],
                ans["description"],
                ans["url"],
                self.commands,
            )
            for ans in answers
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
        application_list = self.applications
        return {application.name: application for application in application_list}

    @property
    def commands(self) -> List["QCrBoxCommandBase"]:
        """
        Retrieves a list of commands from the QCrBox server.

        Returns
        -------
        List[QCrBoxCommandBase]
            A list of QCrBoxCommand or QCrBoxInteractiveCommand objects.
        """
        answers = get_time_cached_app_anwer(self.server_url, get_ttl_hash())

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

    def __repr__(self) -> str:
        return f"<QCrBoxWrapper(server_addr={self.server_addr}, server_port={self.server_port})>"


class QCrBoxApplication:
    """
    Represents an application in QCrBox packaged in its own container.

    Parameters
    ----------
    app_id : int
        Unique identifier for the application.
    name : str
        Name of the application.
    version : str
        Version of the application.
    description : str
        Description of the application.
    url : str
        URL for the application documentation or homepage.
    server_commands : List[QCrBoxCommandBase]
        A list of commands available for this application.
    """

    def __init__(
        self,
        app_id: int,
        name: str,
        version: str,
        description: str,
        url: str,
        server_commands: List["QCrBoxCommand"],
    ) -> None:
        """
        Initializes the QCrBoxApplication instance.

        Parameters
        ----------
        app_id : int
            Unique identifier for the application.
        name : str
            Name of the application.
        version : str
            Version of the application.
        description : str
            Description of the application.
        url : str
            URL for the application documentation or homepage.
        server_commands : List[QCrBoxCommand]
            A list of commands available for this application.
        """
        self.id = app_id
        self.name = name
        self.version = version
        self.description = description
        self.url = url

        app_cmds = [cmd for cmd in server_commands if cmd.application_id == self.id]
        method_strings = []
        for cmd in app_cmds:
            parameter_strings = (f"{par.name}: {par.dtype}" for par in cmd.parameters)
            base_indent = "\n                    "
            all_par_string = base_indent + ("," + base_indent).join(parameter_strings) + "\n                "
            method_strings.append(f"{cmd.name}({all_par_string})")
            setattr(self, cmd.name, cmd)

        linker = "\n\n                "

        self.__doc__ = textwrap.dedent(
            f"""
            Represents the {self.name} application (v. {self.version}) in QCrBox

            Methods:
                {linker.join(method_strings)}
            """
        )

    def __repr__(self) -> str:
        return f"{self.name}()"


class QCrBoxCommandBase:
    """
    Base class for representing a command to be executed on the QCrBox server.

    Parameters
    ----------
    cmd_id : int
        Unique identifier for the command.
    name : str
        Name of the command.
    application_id : int
        ID of the application used by the command.
    parameters : List[QCrBoxParameter]
        List of parameters for the command.
    wrapper_parent : QCrBoxWrapper
        Parent wrapper object that instantiated the command.
    """

    def __init__(
        self,
        cmd_id: int,
        name: str,
        application_id: int,
        parameters: List[QCrBoxParameter],
        wrapper_parent: QCrBoxWrapper,
    ) -> None:
        """
        Initializes the QCrBoxCommandBase instance.

        Parameters
        ----------
        cmd_id : int
            Unique identifier for the command.
        name : str
            Name of the command.
        application_id : int
            ID of the application used by the command.
        parameters : List[QCrBoxParameter]
            List of parameters for the command.
        wrapper_parent : QCrBoxWrapper
            Parent wrapper object that instantiated the command.
        """
        self.id = cmd_id
        self.name = name
        self.application_id = application_id
        self.parameters = parameters
        self.wrapper_parent = wrapper_parent
        self._server_url = wrapper_parent.server_url

    @property
    def par_name_list(self) -> List[str]:
        """
        Retrieves the names of the parameters for the command.

        Returns
        -------
        List[str]
            A list containing the names of the parameters.
        """
        return [par.name for par in self.parameters]

    def args_to_kwargs(self, *args, **kwargs):
        """
        Converts positional and keyword arguments into a dictionary of only keyword
        arguments.

        This method ensures that the arguments match the parameter names
        defined for the command, raising errors for invalid or duplicate arguments.

        Parameters
        ----------
        *args : str
            Positional arguments for the command parameters.
        **kwargs : str
            Keyword arguments for the command parameters.

        Returns
        -------
        dict
            A dictionary mapping parameter names to their corresponding values.

        Raises
        ------
        NameError
            If invalid or duplicate keyword arguments are provided.
        """
        arguments = {key: str(val) for key, val in zip(self.par_name_list, args)}

        invalid_args = [arg for arg in kwargs if arg not in self.par_name_list]
        if len(invalid_args) > 0:
            raise NameError(f'This method got one or more invalid keywords: {", ".join(invalid_args)}')

        overbooked_args = [arg for arg in kwargs if arg in arguments]

        if len(overbooked_args) > 0:
            raise NameError(f'One or more kwargs already set as args: {", ".join(overbooked_args)}')

        arguments.update({key: str(val) for key, val in kwargs.items()})
        return arguments


class QCrBoxCommand(QCrBoxCommandBase):
    """
    Represents a command to be executed on the QCrBox server.

    Parameters
    ----------
    cmd_id : int
        Unique identifier for the command.
    name : str
        Name of the command.
    application_id : int
        ID of the application used by the command.
    parameters : List[QCrBoxParameter]
        List of parameters for the command.
    wrapper_parent : QCrBoxWrapper
        Parent wrapper object that instantiated the command.
    """

    def __call__(self, *args, **kwargs) -> "QCrBoxCalculation":
        """
        Executes the command on the QCrBox server with the provided arguments.

        Parameters
        ----------
        *args
            Positional arguments for the command parameters.
        **kwargs
            Keyword arguments for the command parameters.

        Returns
        -------
        QCrBoxCalculation
            The resulting calculation object from executing the command.

        Raises
        ------
        NameError
            If invalid or duplicate keyword arguments are provided.
        ConnectionError
            If the command cannot be successfully sent to the server.
        """
        arguments = self.args_to_kwargs(*args, **kwargs)

        data_dict = {
            "action": "invoke_command",
            "payload": {"command_id": self.id, "arguments": arguments},
        }
        req = urllib.request.Request(f"{self._server_url}/invoke_command/", method="POST")
        req.add_header("Content-Type", "application/json")
        data = json.dumps(data_dict)
        data = data.encode("UTF-8")
        r = urllib.request.urlopen(req, data=data)
        answer = json.loads(r.read())
        if not answer["status"] == "success":
            raise TimeoutError(f"Command not successfully send. Answer was {answer}")

        return QCrBoxCalculation(answer["payload"]["calculation_id"], self)

    def __repr__(self) -> str:
        return f"QCrBoxCommand({self.name})"


class QCrBoxInteractiveCommand(QCrBoxCommandBase):
    """
    Represents an interactive command to be executed on the QCrBox server.

    This class includes additional steps for preparation and finalization of
    the command execution, along with a GUI URL for interactive sessions.

    Parameters
    ----------
    cmd_id : int
        Unique identifier for the command.
    name : str
        Name of the command.
    application_id : int
        ID of the application used by the command.
    parameters : List[QCrBoxParameter]
        List of parameters for the command.
    gui_url : str
        URL for the GUI associated with the interactive command.
    wrapper_parent : QCrBoxWrapper
        Parent wrapper object that instantiated the command.
    run_cmd : QCrBoxCommand
        Command to be executed as the main run command.
    prepare_cmd : Optional[QCrBoxCommand], optional
        Command to be executed as the preparation command, by default None.
    finalise_cmd : Optional[QCrBoxCommand], optional
        Command to be executed as the finalization command, by default None.
    """

    def __init__(
        self,
        cmd_id: int,
        name: str,
        application_id: int,
        parameters: List[QCrBoxParameter],
        gui_url: str,
        wrapper_parent: QCrBoxWrapper,
        run_cmd: QCrBoxCommand,
        prepare_cmd: Optional[QCrBoxCommand] = None,
        finalise_cmd: Optional[QCrBoxCommand] = None,
    ) -> None:
        """
        Initializes the QCrBoxInteractiveCommand instance.

        Parameters
        ----------
        cmd_id : int
            Unique identifier for the command.
        name : str
            Name of the command.
        application_id : int
            ID of the application used by the command.
        parameters : List[QCrBoxParameter]
            List of parameters for the command.
        gui_url : str
            URL for the GUI associated with the interactive command.
        wrapper_parent : QCrBoxWrapper
            Parent wrapper object that instantiated the command.
        run_cmd : QCrBoxCommand
            Command to be executed as the main run command.
        prepare_cmd : Optional[QCrBoxCommand], optional
            Command to be executed as the preparation command (before run), by default None.
        finalise_cmd : Optional[QCrBoxCommand], optional
            Command to be executed as the finalization command (after trigger after run),
            by default None.
        """
        super().__init__(
            cmd_id=cmd_id,
            name=name,
            application_id=application_id,
            parameters=parameters,
            wrapper_parent=wrapper_parent,
        )
        self.gui_url = gui_url
        self._server_url = wrapper_parent.server_url
        self.run_cmd = run_cmd
        self.prepare_cmd = prepare_cmd
        self.finalise_cmd = finalise_cmd

    def execute_prepare(self, arguments: dict):
        """
        Executes the preparation command with the provided arguments.

        Parameters
        ----------
        arguments : dict
            Dictionary of arguments for the preparation command.

        Returns
        -------
        dict
            Updated arguments after preparation command execution.
        """
        prepare_calculation = None
        if self.prepare_cmd is not None:
            prepare_arguments = {key: val for key, val in arguments.items() if key in self.prepare_cmd.par_name_list}

            prepare_calculation = self.prepare_cmd(**prepare_arguments)
            try:
                prepare_calculation.wait_while_running(0.1)
            except UnsuccessfulCalculationError as e:
                raise InteractiveExecutionError(f"Prepare command of {self.name} failed") from e

    def execute_run(self, arguments: dict) -> Tuple["QCrBoxCalculation", dict]:
        """
        Executes the main run command with the provided arguments.

        Parameters
        ----------
        arguments : dict
            Dictionary of arguments for the run command.

        Returns
        -------
        Tuple[QCrBoxCalculation, dict]
            The resulting calculation object and the updated arguments.
        """
        run_arguments = {key: val for key, val in arguments.items() if key in self.run_cmd.par_name_list}
        run_calculation = self.run_cmd(**run_arguments)
        if run_calculation.status.status not in ("running", "completed"):
            raise UnsuccessfulCalculationError(run_calculation.status)
        return run_calculation

    def execute_finalise(self, arguments: dict) -> dict:
        """
        Executes the finalization command with the provided arguments.

        Parameters
        ----------
        arguments : dict
            Dictionary of arguments for the finalization command.

        Returns
        -------
        dict
            Updated arguments after finalization command execution
        """
        if self.finalise_cmd is not None:
            finalise_arguments = {key: val for key, val in arguments.items() if key in self.finalise_cmd.par_name_list}
            finalise_calculation = self.finalise_cmd(**finalise_arguments)
            try:
                finalise_calculation.wait_while_running(0.1)
            except UnsuccessfulCalculationError as e:
                raise InteractiveExecutionError(f"Finalise command of {self.name} failed") from e

    def __call__(self, *args, **kwargs) -> "QCrBoxCalculation":
        """
        Executes the interactive command with the provided arguments.

        Parameters
        ----------
        *args
            Positional arguments for the command parameters.
        **kwargs
            Keyword arguments for the command parameters.

        Returns
        -------
        QCrBoxCalculation
            The resulting calculation object from the run command.

        Raises
        ------
        NameError
            If invalid or duplicate keyword arguments are provided.
        ConnectionError
            If the command cannot be successfully sent to the server.
        """
        arguments = self.args_to_kwargs(*args, **kwargs)

        self.execute_prepare(arguments)
        if self.gui_url is not None:
            webbrowser.open(self.gui_url)
        run_calculation = self.execute_run(arguments)
        if self.gui_url is not None:
            input("Press enter when you have finished your interactive session")

        self.execute_finalise(arguments)

        return run_calculation


class QCrBoxCalculation:
    """
    Represents a calculation performed on the QCrBox server.

    Parameters
    ----------
    calc_id : int
        Unique identifier for the calculation.
    calculation_parent : QCrBoxCommand
        Parent command object that instantiated the calculation.
    """

    def __init__(self, calc_id: int, calculation_parent: "QCrBoxCommand") -> None:
        """
        Initializes the QCrBoxCalculation instance.

        Parameters
        ----------
        calc_id : int
            Unique identifier for the calculation.
        calculation_parent : QCrBoxCommand
            Parent command object that instantiated the calculation.
        """
        self.id = calc_id
        self.calculation_parent = calculation_parent
        self._server_url = calculation_parent._server_url

    @property
    def status(self) -> QCrBoxCalculationStatus:
        """
        Fetches and returns the current status of the calculation from the server.

        Returns
        -------
        QCrBoxCalculationStatus
            A namedtuple containing detailed status information of the calculation.
        """
        with urllib.request.urlopen(f"{self._server_url}/calculations/{self.id}") as r:
            answers = json.loads(r.read().decode("UTF-8"))

        return QCrBoxCalculationStatus(
            int(answers["id"]),
            int(answers["command_id"]),
            answers["started_at"],
            answers["status_details"]["status"],
            answers["status_details"],
        )

    def wait_while_running(self, sleep_time: float) -> None:
        """
        Periodically checks the calculation's status and blocks until it is no longer 'running'.

        Parameters
        ----------
        sleep_time : float
            The interval, in seconds, between status checks.

        Raises
        ------
        RuntimeError
            If the calculation finishes with a status other than 'completed'.
        """
        while self.status.status == "running":
            time.sleep(sleep_time)
        if self.status.status != "completed":
            raise UnsuccessfulCalculationError(self.status)

    def __repr__(self) -> str:
        return f"<QCrBoxCalculation(id={self.id}, parent_command={self.calculation_parent.name})>"


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
        self.local_path.mkdir(exist_ok=True, parents=True)

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

    def create_next_step_folder(self) -> Tuple[pathlib.Path, str]:
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
        Tuple[pathlib.Path, str]
            A tuple containing the newly created folder's path in the local file system
            (as a pathlib.Path object) and its equivalent in the QCrBox file system
            (as a POSIX-style string path).
        """
        next_folder = f"step_{next(self.step_counter)}"
        self.path_to_local(next_folder).mkdir(exist_ok=True)
        return self.path_to_pair(next_folder)
