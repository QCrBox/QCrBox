import textwrap
from typing import TYPE_CHECKING

from pyqcrbox import logger, sql_models_NEW_v2

from .qcrbox_command import QCrBoxCommand
from .qcrbox_interactive_session import QCrBoxInteractiveSession

if TYPE_CHECKING:
    from .qcrbox_wrapper import QCrBoxWrapper


class QCrBoxApplication:
    """
    Represents an application in QCrBox packaged in its own container.
    """

    def __init__(
        self,
        application_spec: sql_models_NEW_v2.ApplicationSpecWithCommands,
        wrapper_parent: "QCrBoxWrapper",
    ) -> None:
        """
        Initializes the QCrBoxApplication instance.

        Parameters
        ----------
        application_spec: sql_models_NEW_v2.ApplicationSpecWithCommands
            The application spec as returned by the API endpoint `/applications`.
        """
        self.wrapper_parent = wrapper_parent
        self.application_spec = application_spec
        self.name = self.application_spec.name
        self.slug = self.application_spec.slug
        self.version = self.application_spec.version
        if self.wrapper_parent.server_host == "127.0.0.1":
            self.gui_url = f"http://localhost/gui/{self.slug}"
        else:
            self.gui_url = f"http://{self.wrapper_parent.server_host}/gui/{self.slug}"
        logger.debug("TODO: implement proper construction and validation of gui_url")

        self.commands = [
            QCrBoxCommand(
                application_slug=self.slug,
                application_version=self.version,
                cmd_spec=cmd_spec,
                wrapper_parent=wrapper_parent,
            )
            for cmd_spec in self.application_spec.commands
        ]
        self._cmds_by_name: dict[str, QCrBoxCommand] = {cmd.name: cmd for cmd in self.commands}
        for cmd in self.commands:
            setattr(self, cmd.name, cmd)

    def __repr__(self) -> str:
        return f"<{self.name}>"

    @property
    def non_interactive_commands(self) -> list[QCrBoxCommand]:
        return [cmd for cmd in self.commands if not cmd.is_interactive]

    @property
    def interactive_commands(self) -> list[QCrBoxCommand]:
        return [cmd for cmd in self.commands if cmd.is_interactive]

    def _construct_docstring(self):
        method_strings = []
        for cmd in self.commands:
            parameter_strings = (f"{par.name}: {par.dtype}" for par in cmd.parameters)
            base_indent = "\n                    "
            all_par_string = base_indent + ("," + base_indent).join(parameter_strings) + "\n                "
            method_strings.append(f"{cmd.name}({all_par_string})")
            setattr(self, cmd.name, cmd)

        separator = "\n\n" + (" " * 16)

        return textwrap.dedent(
            f"""
            Represents the {self.name} application (v. {self.version}) in QCrBox

            Methods:
                {separator.join(method_strings)}
            """
        )

    def interactive_session(self, **kwargs):
        assert (
            len(self.interactive_commands) == 1
        ), "interactive_session currently assumes that the application exposes exactly one interactive command"

        # cmd_interactive = self.interactive_commands[0]
        # run_cmd = self.application_spec.cmds_by_name["__interactive_run"]
        # prepare_cmd = self.application_spec.cmds_by_name["__interactive_prepare"]
        prepare_cmd = self._cmds_by_name.get("__interactive_prepare", None)
        run_cmd = self._cmds_by_name["__interactive_run"]
        finalise_cmd = self._cmds_by_name.get("__interactive_finalise", None)

        session = QCrBoxInteractiveSession(
            application_slug=self.slug,
            gui_url=self.gui_url,
            run_cmd=run_cmd,
            prepare_cmd=prepare_cmd,
            finalise_cmd=finalise_cmd,
            kwargs=kwargs,
        )
        # session.start_and_wait_for_user_input()
        return session
