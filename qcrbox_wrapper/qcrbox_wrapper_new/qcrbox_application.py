import textwrap

from pyqcrbox import sql_models


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

        method_strings = []
        for cmd in self.application_spec.commands:
            # parameter_strings = (f"{par.name}: {par.dtype}" for par in cmd.parameters)
            parameter_strings = (f"{par['name']}: {par['type']}" for par in cmd.parameters.values())
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
