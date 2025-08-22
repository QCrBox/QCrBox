from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import BaseParameter

if TYPE_CHECKING:
    from pyqcrbox.sql_models import CommandSpecDiscriminatedUnion

__all__ = ["BaseCommand"]


class BaseCommand(metaclass=ABCMeta):
    """Abstract base class for command execution.

    Parameters
    ----------
    cmd_spec : CommandSpecDiscriminatedUnion
        The command specification object describing the command to execute.

    """

    def __init__(self, cmd_spec: "CommandSpecDiscriminatedUnion"):
        self.cmd_spec = cmd_spec
        self.type = cmd_spec.implemented_as

    def __repr__(self):
        """Return a string representation of the command instance.

        Returns
        -------
        str
            String representation of the object.

        """
        clsname = self.__class__.__name__
        return f"<{clsname}: {self.cmd_spec.name!r}>"

    @abstractmethod
    async def prepare_params(
        self, working_dir: str | Path, command_arguments: dict[str, BaseParameter]
    ) -> dict[str, Any]:
        """Prepare the parameters required for the CLI command.

        Any optional arguments which are not included are found in the command
        specification default values list.

        Parameters
        ----------
        working_dir : str
            The working directory to potentially write any files to.
        command_arguments : dict[str, BaseParameter]
            The names and values of the parameters for the CLI command in a dict
            mapping of { param_name: param_value }

        """

    @abstractmethod
    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin: Any | None = None,
        _stdout: Any | None = None,
        _stderr: Any | None = None,
        _cwd: str | Path | None = None,
        **kwargs: dict[str, Any],
    ) -> BaseCalculation:
        """Execute the command asynchronously in the background.

        Parameters
        ----------
        _calculation_id : str
            Unique identifier for the calculation instance.
        _stdin : Any, optional
            Standard input stream or data (default is None).
        _stdout : Any, optional
            Standard output stream or handler (default is None).
        _stderr : Any, optional
            Standard error stream or handler (default is None).
        _cwd : str or Path, optional
            Working directory for command execution (default is None).
        **kwargs
            Additional keyword arguments for command execution.

        Returns
        -------
        BaseCalculation
            An instance representing the background calculation.

        """
        pass
