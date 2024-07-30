__all__ = ["QCrBoxInteractiveSession"]

import webbrowser
from typing import Any, Sequence

from pyqcrbox import logger
from .qcrbox_command import QCrBoxInteractiveCommand


class QCrBoxInteractiveSession:
    def __init__(self, cmd: QCrBoxInteractiveCommand, gui_url: str, args: Sequence, kwargs: dict[str, Any]):
        self.cmd = cmd
        self.gui_url = gui_url
        self.arguments = cmd.args_to_kwargs(*args, **kwargs)

    def start(self):
        logger.debug(f"Starting interactive session for {self.cmd.application_slug!r}")
        webbrowser.open(self.gui_url)

        #run_calculation = self.execute_run(arguments)
        logger.debug(f"TODO: execute 'run' command")

    def close(self):
        logger.debug("TODO: close session")

    def start_and_wait_for_user_input(self):
        self.start()
        input("Press enter when you have finished your interactive session")
        self.close()
