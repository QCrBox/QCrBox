import json
import urllib.request
from collections import namedtuple

from pyqcrbox import sql_models

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


class QCrBoxCalculation:
    """
    Represents a calculation performed on the QCrBox server.
    """


class QCrBoxCommandBase:
    """
    Base class for representing a command to be executed on the QCrBox server.
    """

    def __init__(
        self,
        cmd_spec: sql_models.CommandSpecWithParameters,
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
        self.cmd_spec = cmd_spec
        # self.id = cmd_id
        self.name = cmd_spec.name
        # self.application_id = application_id
        # self.parameters = parameters
        # self.wrapper_parent = wrapper_parent
        # self._server_url = wrapper_parent.server_url
        self.parameters = [
            QCrBoxParameter(param_dict["name"], param_dict["dtype"]) for param_dict in self.cmd_spec.parameters.values()
        ]

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

        return QCrBoxCalculation(answer["payload"]["calculation_id"], self)

    def __repr__(self) -> str:
        return f"QCrBoxCommand({self.name!r})"
