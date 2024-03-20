# SPDX-License-Identifier: MPL-2.0
import inspect
import re
import subprocess

import anyio

from pyqcrbox.sql_models import ParameterSpecCreate

from ...sql_models.call_pattern import CallPattern
from .calculation import ExternalCmdCalculation


class Param:
    def __init__(self, name, default=None):
        self.name = name
        self.default = default
        self._python_param = inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, default=default)

    @classmethod
    def from_parameter_spec(cls, param_spec: ParameterSpecCreate):
        return cls(name=param_spec.name, default=param_spec.default_value)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self._python_param!s}>"

    def __str__(self):
        return f"<{self.name}>"

    def bind(self, bound_args: inspect.BoundArguments):
        return bound_args.arguments[self.name]


class FormattedParam(Param):
    def __init__(self, name, default=None, format_string=None):
        super().__init__(name=name, default=default)
        self.format_string = format_string

    def bind(self, bound_args: inspect.BoundArguments):
        arg_val = super().bind(bound_args)
        if self.format_string is not None:
            return self.format_string.format(arg_val)
        return arg_val


class CmdLiteral:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.text!s}>"

    def __str__(self):
        return self.text

    def bind(self, bound_args: inspect.BoundArguments):
        return self.text


def _make_cmd_constituent(value: str):
    m = re.match(r"{(?P<param_name>.*)}", value)
    if m:
        return Param(m.group("param_name"))
    else:
        return CmdLiteral(value)


class ExternalCommand:
    def __init__(self, call_pattern: "CallPattern"):
        # assert isinstance(call_pattern, CallPattern)
        self.call_pattern = call_pattern
        self.cmd_constituents = [_make_cmd_constituent(x) for x in self.call_pattern.split()]
        self.cmd_params = [x for x in self.cmd_constituents if isinstance(x, Param)]
        self.parameter_names = [x.name for x in self.cmd_params]
        self.signature = inspect.Signature(parameters=[x._python_param for x in self.cmd_params])

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{str(self)}'>"

    def __str__(self):
        cmd_str = " ".join(str(x) for x in self.cmd_constituents)
        return cmd_str

    def bind(self, *args, **kwargs):
        bound_args = self.signature.bind(*args, **kwargs)
        return [str(x.bind(bound_args)) for x in self.cmd_constituents]

    async def execute_in_background(
        self, *args, _stdin=None, _stdout=subprocess.PIPE, _stderr=subprocess.PIPE, **kwargs
    ) -> ExternalCmdCalculation:
        cmd = self.bind(*args, **kwargs)
        # current_workdir = os.getcwd()
        # logger.debug(f"{current_workdir=}")
        proc = await anyio.open_process(
            cmd,
            stdin=_stdin,
            stdout=_stdout,
            stderr=_stderr,
        )
        return ExternalCmdCalculation(proc)
