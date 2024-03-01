"""
This module provides a comprehensive interface for interacting with the QCrBox server,
enabling the execution of commands, retrieval of application information, and management
of calculation statuses. It defines classes for wrapping the QCrBox API, representing
applications, commands, and calculations, alongside a utility class for path management
within QCrBox Docker containers. Additionally, it utilizes namedtuples for structured
representation of command parameters and calculation statuses.

Classes:
    QCrBoxWrapper: Interface to interact with the QCrBox server.
    QCrBoxApplication: Represents an application within QCrBox.
    QCrBoxCommand: Represents a command for execution on the QCrBox server.
    QCrBoxCalculation: Represents a calculation performed on the QCrBox server.
    QCrBoxPathHelper: Manages file paths within QCrBox Docker containers.

Namedtuples:
    QCrBoxParameter: Represents a parameter for QCrBoxCommand.
    QCrBoxCalculationStatus: Represents the status of a calculation in QCrBox.
"""

import json
import pathlib
import textwrap
import time
import urllib
import urllib.request
import webbrowser
from collections import namedtuple
from itertools import count
from typing import Dict, List, Tuple

QCrBoxParameter = namedtuple("QCrBoxParameter", ["name", "dtype"])
QCrBoxParameter.__doc__ = """
Represents a parameter for calling a QCrBoxCommand in QCrBox.

Attributes:
    name (str): Name of the parameter.
    dtype (str): Data type of the parameter.
"""

QCrBoxCalculationStatus = namedtuple(
    "QCrBoxCalculationStatus",
    ["calculation_id", "command_id", "started_at", "status", "status_details"],
)
QCrBoxCalculationStatus.__doc__ = """
Represents the status of a calculation in QCrBox.

Attributes:
    calculation_id (int): Unique identifier for the calculation.
    command_id (int): ID of the command that initiated the calculation.
    started_at (str): Timestamp when the calculation started.
    status (str): Status of the calculation (e.g., 'running', 'completed').
    status_details (dict): Status details of the calculation
"""


class QCrBoxWrapper:
    """
    Provides an interface to interact with the QCrBox server.
    """

    def __init__(
        self,
        server_addr: str,
        server_port: int,
        port_dict: Dict[str, str] = None,
        gui_commands: List[Tuple[str, str]] = None,
    ):
        """
        Initializes the QCrBoxWrapper instance.

        Args:
            server_addr: The address/ip of the QCrBox server.
            server_port: The port on which the QCrBox server is running.

        Raises:
            ConnectionError: If the connection to the QCrBox Registry Server fails.
        """
        self.server_addr = server_addr
        self.server_port = server_port
        if port_dict is None:
            self.port_dict = {}
        else:
            self.port_dict = port_dict
        if gui_commands is None:
            self.gui_commands = []
        else:
            self.gui_commands = gui_commands

        with urllib.request.urlopen(f"{self.server_url}") as r:
            answers = json.loads(r.read().decode("UTF-8"))

        if "QCrBox" not in answers:
            print(answers)
            raise ConnectionError(f"Cannot connect to QCrBox Registry Server at {self.server_url}")

    @property
    def server_url(self) -> str:
        """
        Constructs the full URL of the QCrBox server.

        Returns:
            str: The server URL.
        """
        return f"http://{self.server_addr}:{self.server_port}"

    @property
    def applications(self) -> List["QCrBoxApplication"]:
        """
        Retrieves a list of applications from the QCrBox server.

        Returns:
            List[QCrBoxApplication]: A list of QCrBoxApplication namedtuples.
        """
        with urllib.request.urlopen(f"{self.server_url}/applications/") as r:
            answers = json.loads(r.read().decode("UTF-8"))
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

        Returns:
            dict: A dictionary where keys are application names and values are
            QCrBoxApplication objects.
        """
        application_list = self.applications
        return {application.name: application for application in application_list}

    @property
    def commands(self) -> List["QCrBoxCommand"]:
        """
        Retrieves a list of commands from the QCrBox server.

        Returns:
            List[QCrBoxCommand]: A list of QCrBoxCommand objects.
        """

        with urllib.request.urlopen(f"{self.server_url}/commands/") as r:
            answers = json.loads(r.read().decode("UTF-8"))

        commands = [
            QCrBoxCommand(
                int(ans["id"]),
                ans["name"],
                int(ans["application_id"]),
                [QCrBoxParameter(key, dtype) for key, dtype in ans["parameters"].items()],
                self,
            )
            for ans in answers
        ]
        return commands

    def __repr__(self) -> str:
        return f"<QCrBoxWrapper(server_addr={self.server_addr}, server_port={self.server_port})>"


class QCrBoxApplication:
    """
    Represents an application in QCrBox packaged in its own container.

    Attributes:
        id (int): Unique identifier for the application.
        name (str): Name of the application.
        version (str): Version of the application.
        description (str): Description of the application.
        url (str): URL for the application.
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


class QCrBoxCommand:
    """
    Represents a command to be executed on the QCrBox server.
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
        Initializes the QCrBoxCommand instance.

        Args:
            id: Unique identifier for the command.
            name: Name of the command.
            application_id: ID of the application used by the command.
            parameters: List of parameters for the command.
            wrapper_parent: Parent wrapper object that instantiated the command.
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

        Returns:
            List[str]: A list containing the names of the parameters.
        """
        return [par.name for par in self.parameters]

    def __call__(self, *args, **kwargs) -> "QCrBoxCalculation":
        """
        Allows the command object to be called as a function with provided arguments.

        Args:
            *args: Command arguments
            **kwargs: Command arguments.

        Returns:
            QCrBoxCalculation: The resulting calculation object from executing the command.
        """
        arguments = {key: str(val) for key, val in zip(self.par_name_list, args)}

        invalid_args = [arg for arg in kwargs if arg not in self.par_name_list]
        if len(invalid_args) > 0:
            raise NameError(f'This method got one or more invalid keywords: {", ".join(invalid_args)}')

        overbooked_args = [arg for arg in kwargs if arg in arguments]

        if len(overbooked_args) > 0:
            raise NameError(f'One or more kwargs already set as args: {", ".join(overbooked_args)}')

        arguments.update({key: str(val) for key, val in kwargs.items()})

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
            print(answer)
            raise ConnectionError("Command not successfully send")

        # TODO Probably replace all of this with a returned adress from server
        def gui_address(app_id, cmd_name):
            app_id_to_name = {app.id: app.name for app in self.wrapper_parent.applications}
            app_name = app_id_to_name[app_id]
            if (app_name, cmd_name) in self.wrapper_parent.gui_commands:
                address = self.wrapper_parent.server_addr
                port = self.wrapper_parent.port_dict[app_name]
                return f"http://{address}:{port}/vnc.html?path=vnc&autoconnect=true&resize=remote"
            return None

        gui_addr = gui_address(self.application_id, self.name)
        if gui_addr is not None:
            webbrowser.open(gui_addr)

        return QCrBoxCalculation(answer["payload"]["calculation_id"], self)

    def __repr__(self) -> str:
        return f"QCrBoxCommand({self.name})"


class QCrBoxCalculation:
    """
    Represents a calculation performed on the QCrBox server.
    """

    def __init__(self, calc_id: int, calculation_parent: "QCrBoxCommand"):
        """
        Initializes the QCrBoxCalculation instance.

        Args:
            id: Unique identifier for the calculation.
            calculation_parent: Parent command object that instantiated the calculation.
        """
        self.id = calc_id
        self.calculation_parent = calculation_parent
        self._server_url = calculation_parent._server_url

    @property
    def status(self) -> QCrBoxCalculationStatus:
        """
        Retrieves the status of the calculation from the server.

        Returns:
            QCrBoxCalculationStatus: The status of the calculation.
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
        Blocks execution while the calculation is running, checking the status at regular
        intervals defined by `sleep_time`.

        Parameters
        ----------
        sleep_time : float
            Time in seconds to wait between status checks.
        """
        while self.status.status == "running":
            time.sleep(sleep_time)

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
        qcrbox_path: pathlib.Path = pathlib.PurePosixPath("/mnt/qcrbox/shared_files"),
        base_dir: pathlib.Path = None,
    ) -> None:
        """
        Initializes the QCrBoxPathHelper instance.

        Parameters
        ----------
        local_path : pathlib.Path
            The base path in the local file system.
        qcrbox_path : pathlib.Path, optional
            The base path in the QCrBox file system (default is '/mnt/qcrbox/shared_files').
        base_dir : pathlib.Path, optional
            A subdirectory within both the local and QCrBox base paths for scoped path
            management. Defaults to None, in which case the base paths are used directly.
        """
        if base_dir is None:
            self.local_path = pathlib.Path(local_path)
            self.qcrbox_path = pathlib.PurePosixPath(qcrbox_path)
        else:
            self.local_path = pathlib.Path(local_path) / base_dir
            self.qcrbox_path = pathlib.PurePosixPath(qcrbox_path) / base_dir

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
