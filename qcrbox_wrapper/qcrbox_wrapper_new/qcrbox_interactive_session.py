__all__ = ["QCrBoxInteractiveSession"]

import webbrowser
from typing import Any, Sequence, TYPE_CHECKING

from pyqcrbox import logger
from .qcrbox_command import QCrBoxCommand

if TYPE_CHECKING:
    from .qcrbox_calculation import QCrBoxCalculation


class QCrBoxInteractiveSession:
    def __init__(self, *, application_slug: str, gui_url: str, run_cmd: QCrBoxCommand):
        self.application_slug = application_slug
        self.gui_url = gui_url
        self.run_cmd = run_cmd

    # , args: Sequence, kwargs: dict[str, Any]

    def start(self, *args, **kwargs):
        logger.debug(f"Starting interactive session for {self.application_slug!r}")
        webbrowser.open(self.gui_url)

        run_calculation = self.execute_run(*args, **kwargs)
        logger.debug(f"{run_calculation=!r}")

    def close(self):
        logger.debug("TODO: close session")

    def start_and_wait_for_user_input(self):
        self.start()
        input("Press enter when you have finished your interactive session")
        self.close()

    def execute_run(self, *args, **kwargs) -> "QCrBoxCalculation":
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
        all_arguments = self.run_cmd.args_to_kwargs(*args, **kwargs)
        run_arguments = {key: val for key, val in all_arguments.items() if key in self.run_cmd.parameter_names}
        run_calculation = self.run_cmd(**run_arguments)
        # if run_calculation.status.status not in ("running", "completed"):
        #     raise UnsuccessfulCalculationError(run_calculation.status)
        return run_calculation
