import textwrap

from pyqcrbox import sql_models

from .qcrbox_command import QCrBoxCommand


class QCrBoxApplication:
    """
    Represents an application in QCrBox packaged in its own container.
    """

    def __init__(
        self,
        application_spec: sql_models.ApplicationSpecWithCommands,
    ) -> None:
        """
        Initializes the QCrBoxApplication instance.

        Parameters
        ----------
        application_spec: sql_models.ApplicationSpecWithCommands
            The application spec as returned by the API endpoint `/applications`.
        """
        self.application_spec = application_spec
        self.name = self.application_spec.name
        self.slug = self.application_spec.slug
        self.version = self.application_spec.version
        self.commands = [QCrBoxCommand(cmd_spec) for cmd_spec in self.application_spec.commands]
        self.__doc__ = self._construct_docstring()

    def __repr__(self) -> str:
        return f"<{self.name}>"

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
