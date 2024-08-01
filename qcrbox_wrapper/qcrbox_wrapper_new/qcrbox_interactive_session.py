__all__ = ["QCrBoxInteractiveSession"]

import webbrowser
from typing import Any, Sequence, TYPE_CHECKING

from pyqcrbox import logger
from .qcrbox_command import QCrBoxCommand

if TYPE_CHECKING:
    from .qcrbox_calculation import QCrBoxCalculation


class QCrBoxInteractiveSession:
    def __init__(
        self,
        *,
        application_slug: str,
        gui_url: str,
        prepare_cmd: str,
        run_cmd: str,
        kwargs: dict,
    ):
        self.application_slug = application_slug
        self.gui_url = gui_url
        self.prepare_cmd = prepare_cmd
        self.run_cmd = run_cmd
        self.kwargs = kwargs
        # self.finalise_cmd = finalise_cmd

    def start(self):
        logger.debug(f"Starting interactive session for {self.application_slug!r}")
        self.prepare_calculation = self.execute_prepare()
        logger.debug(f"{self.prepare_calculation=!r}")
        self.run_calculation = self.execute_run()
        logger.debug(f"{self.run_calculation=!r}")
        webbrowser.open(self.gui_url)

    def close(self):
        logger.debug("TODO: close session")

    def start_and_wait_for_user_input(self):
        self.start()
        input("Press enter when you have finished your interactive session")
        self.close()

    def execute_prepare(self, **kwargs):
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
        # all_arguments = self.prepare_cmd.args_to_kwargs(**kwargs)
        prepare_arguments = {key: val for key, val in self.kwargs.items() if key in self.prepare_cmd.parameter_names}

        missing_arguments = set(self.prepare_cmd.parameter_names).difference(prepare_arguments.keys())
        if missing_arguments:
            raise ValueError(f"Missing arguments for 'prepare' command: {missing_arguments!r}")

        prepare_calculation = self.prepare_cmd(**prepare_arguments)
        return prepare_calculation

    def execute_run(self, **kwargs) -> "QCrBoxCalculation":
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
        # all_arguments = self.run_cmd.args_to_kwargs(**kwargs)
        run_arguments = {key: val for key, val in self.kwargs.items() if key in self.run_cmd.parameter_names}

        missing_arguments = set(self.run_cmd.parameter_names).difference(run_arguments.keys())
        if missing_arguments:
            raise ValueError(f"Missing arguments for 'run' command: {missing_arguments!r}")
        run_calculation = self.run_cmd(**run_arguments)
        # if run_calculation.status.status not in ("running", "completed"):
        #     raise UnsuccessfulCalculationError(run_calculation.status)
        return run_calculation
