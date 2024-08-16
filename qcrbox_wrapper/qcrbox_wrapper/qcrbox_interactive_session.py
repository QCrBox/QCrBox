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
        run_cmd: QCrBoxCommand,
        prepare_cmd: QCrBoxCommand | None = None,
        finalise_cmd: QCrBoxCommand | None = None,
        kwargs: dict,
    ):
        self.application_slug = application_slug
        self.gui_url = gui_url
        self.prepare_cmd = prepare_cmd
        self.run_cmd = run_cmd
        self.kwargs = kwargs
        self.finalise_cmd = finalise_cmd

        self.prepare_calculation = None
        self.run_calculation = None
        self.finalise_calculation = None

    def start(self):
        logger.debug(f"Starting interactive session for {self.application_slug!r}")
        self.prepare_calculation = self.execute_prepare()
        logger.debug(f"{self.prepare_calculation=!r}")
        self.run_calculation = self.execute_run()
        logger.debug(f"{self.run_calculation=!r}")
        webbrowser.open(self.gui_url)

    def close(self):
        logger.debug("Closing session")
        self.finalise_calculation = self.execute_finalise()
        logger.debug(f"{self.finalise_calculation=!r}")
        logger.debug("Done.")

    def start_and_wait_for_user_input(self):
        self.start()
        input("Press enter when you have finished your interactive session")
        self.close()

    def execute_prepare(self):
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
        if self.prepare_cmd:
            # all_arguments = self.prepare_cmd.args_to_kwargs(**kwargs)
            prepare_arguments = {key: val for key, val in self.kwargs.items() if key in self.prepare_cmd.parameter_names}

            missing_arguments = set(self.prepare_cmd.parameter_names).difference(prepare_arguments.keys())
            if missing_arguments:
                raise ValueError(f"Missing arguments for 'prepare' command: {missing_arguments!r}")

            prepare_calculation = self.prepare_cmd(**prepare_arguments)
            prepare_calculation.wait_while_running(0.1)
            return prepare_calculation

    def execute_run(self) -> "QCrBoxCalculation":
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

    def execute_finalise(self):
        if self.finalise_cmd:
            # all_arguments = self.prepare_cmd.args_to_kwargs(**kwargs)
            finalise_arguments = {key: val for key, val in self.kwargs.items() if key in self.finalise_cmd.parameter_names}

            missing_arguments = set(self.finalise_cmd.parameter_names).difference(finalise_arguments.keys())
            if missing_arguments:
                raise ValueError(f"Missing arguments for 'prepare' command: {missing_arguments!r}")

            finalise_calculation = self.finalise_cmd(**finalise_arguments)
            return finalise_calculation
