import json
import textwrap
import time
import urllib.request
from collections import namedtuple
from typing import TYPE_CHECKING, Union

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.shared.calculation_status import CalculationStatusDetails
from pyqcrbox.sql_models_NEW_v2.calculation_status_event import CalculationStatusEnum

if TYPE_CHECKING:
    from .qcrbox_wrapper import QCrBoxWrapper

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
    def __init__(self, status: "CalculationStatusDetails"):
        try:
            error_message = status.extra_info["msg"]
        except KeyError:
            error_message = "No error message available"

        msg = textwrap.dedent(
            f"""\
            Calculation with id {status.calculation_id} does not have the status completed but {status.status}.

            Potential error message:
            {error_message}
            
            Command stdout:
            {status.stdout}

            Command stderr:
            {status.stderr}
        """
        ).strip()

        super().__init__(msg)


class QCrBoxCalculation:
    """
    Represents a calculation performed on the QCrBox server.
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
            response_data = json.loads(r.read().decode("UTF-8"))

        return CalculationStatusDetails(**response_data)
        #
        # return QCrBoxCalculationStatus(
        #     int(response["id"]),
        #     int(response["command_id"]),
        #     response["started_at"],
        #     response["status_details"]["status"],
        #     response["status_details"],
        # )

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
        while self.status.status == CalculationStatusEnum.RUNNING:
            time.sleep(sleep_time)
        if self.status.status != CalculationStatusEnum.COMPLETED:
            raise UnsuccessfulCalculationError(self.status)


class QCrBoxCommandBase:
    """
    Base class for representing a command to be executed on the QCrBox server.
    """

    def __init__(
        self,
        *,
        application_slug: str,
        application_version: str,
        cmd_spec: sql_models_NEW_v2.CommandSpecWithParameters,
        wrapper_parent: "QCrBoxWrapper",
    ) -> None:
        """
        Initializes the QCrBoxCommandBase instance.

        Parameters
        ----------
        cmd_spec : pyqcrbox.sql_models_NEW_v2.CommandSpecWithParameters
            Pydantic model representing the command specification.
        server_url : str
            URL of the QCrBox server
        """
        self.cmd_spec = cmd_spec
        self.application_slug = application_slug
        self.application_version = application_version
        self.name = self.cmd_spec.name
        self.wrapper_parent = wrapper_parent
        self._server_url = self.wrapper_parent.server_url
        self.parameters = [
            QCrBoxParameter(param_dict["name"], param_dict["dtype"]) for param_dict in self.cmd_spec.parameters.values()
        ]

    @property
    def is_interactive(self) -> bool:
        return self.cmd_spec.is_interactive

    @property
    def par_name_list(self) -> list[str]:
        """
        Retrieves the names of the parameters for the command.

        Returns
        -------
        list[str]
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

        data_dict = sql_models_NEW_v2.CommandInvocationCreate(
            application_slug=self.application_slug,
            application_version=self.application_version,
            command_name=self.name,
            arguments=arguments,
        ).model_dump()
        req = urllib.request.Request(f"{self._server_url}/commands/invoke", method="POST")
        req.add_header("Content-Type", "application/json")
        data = json.dumps(data_dict)
        data = data.encode("UTF-8")
        r = urllib.request.urlopen(req, data=data)
        response = json.loads(r.read())
        if not response["status"] == "ok":
            print(response)
            raise ConnectionError("Command not successfully sent")

        return QCrBoxCalculation(response["payload"]["calculation_id"], self)

    def __repr__(self) -> str:
        return f"QCrBoxCommand({self.name!r})"


class QCrBoxInteractiveCommand(QCrBoxCommandBase):
    """
    Represents an interactive command to be executed on the QCrBox server.

    This class includes additional steps for preparation and finalization of
    the command execution, along with a GUI URL for interactive sessions.
    """

    def __init__(
        self,
        cmd_id: int,
        name: str,
        application_id: int,
        parameters: list[QCrBoxParameter],
        gui_url: str,
        wrapper_parent: "QCrBoxWrapper",
        run_cmd: QCrBoxCommand,
        prepare_cmd: Union[QCrBoxCommand, None] = None,
        finalise_cmd: Union[QCrBoxCommand, None] = None,
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
        # super().__init__(
        #     cmd_id=cmd_id,
        #     name=name,
        #     application_id=application_id,
        #     parameters=parameters,
        #     wrapper_parent=wrapper_parent,
        # )
        # self.gui_url = gui_url
        # self._server_url = wrapper_parent.server_url
        # self.run_cmd = run_cmd
        # self.prepare_cmd = prepare_cmd
        # self.finalise_cmd = finalise_cmd
        pass

    # def execute_prepare(self, arguments: dict):
    #     """
    #     Executes the preparation command with the provided arguments.
    #
    #     Parameters
    #     ----------
    #     arguments : dict
    #         Dictionary of arguments for the preparation command.
    #
    #     Returns
    #     -------
    #     dict
    #         Updated arguments after preparation command execution.
    #     """
    #     prepare_calculation = None
    #     if self.prepare_cmd is not None:
    #         prepare_arguments = {key: val for key, val in arguments.items() if key in self.prepare_cmd.par_name_list}
    #
    #         prepare_calculation = self.prepare_cmd(**prepare_arguments)
    #         try:
    #             prepare_calculation.wait_while_running(0.1)
    #         except UnsuccessfulCalculationError as e:
    #             raise InteractiveExecutionError(f"Prepare command of {self.name} failed") from e
    #
    # def execute_run(self, arguments: dict) -> Tuple["QCrBoxCalculation", dict]:
    #     """
    #     Executes the main run command with the provided arguments.
    #
    #     Parameters
    #     ----------
    #     arguments : dict
    #         Dictionary of arguments for the run command.
    #
    #     Returns
    #     -------
    #     Tuple[QCrBoxCalculation, dict]
    #         The resulting calculation object and the updated arguments.
    #     """
    #     run_arguments = {key: val for key, val in arguments.items() if key in self.run_cmd.par_name_list}
    #     run_calculation = self.run_cmd(**run_arguments)
    #     if run_calculation.status.status not in ("running", "completed"):
    #         raise UnsuccessfulCalculationError(run_calculation, f"Run command of {self.name} failed")
    #     return run_calculation
    #
    # def execute_finalise(self, arguments: dict) -> dict:
    #     """
    #     Executes the finalization command with the provided arguments.
    #
    #     Parameters
    #     ----------
    #     arguments : dict
    #         Dictionary of arguments for the finalization command.
    #
    #     Returns
    #     -------
    #     dict
    #         Updated arguments after finalization command execution
    #     """
    #     if self.finalise_cmd is not None:
    #         finalise_arguments = {
    #             key: val for key, val in arguments.items() if key in self.finalise_cmd.par_name_list
    #         }
    #         finalise_calculation = self.finalise_cmd(**finalise_arguments)
    #         try:
    #             finalise_calculation.wait_while_running(0.1)
    #         except UnsuccessfulCalculationError as e:
    #             raise InteractiveExecutionError(f"Finalise command of {self.name} failed") from e
    #
    # def __call__(self, *args, **kwargs) -> "QCrBoxCalculation":
    #     """
    #     Executes the interactive command with the provided arguments.
    #
    #     Parameters
    #     ----------
    #     *args
    #         Positional arguments for the command parameters.
    #     **kwargs
    #         Keyword arguments for the command parameters.
    #
    #     Returns
    #     -------
    #     QCrBoxCalculation
    #         The resulting calculation object from the run command.
    #
    #     Raises
    #     ------
    #     NameError
    #         If invalid or duplicate keyword arguments are provided.
    #     ConnectionError
    #         If the command cannot be successfully sent to the server.
    #     """
    #     arguments = self.args_to_kwargs(*args, **kwargs)
    #
    #     self.execute_prepare(arguments)
    #     run_calculation = self.execute_run(arguments)
    #     if self.gui_url is not None:
    #         webbrowser.open(self.gui_url)
    #
    #         input("Press enter when you have finished your interactive session")
    #
    #     self.execute_finalise(arguments)
    #
    #     return run_calculation
