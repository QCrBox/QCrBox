# SPDX-License-Identifier: MPL-2.0

import asyncio
import inspect
import subprocess
from typing import Union

from .calculation import ExternalCmdCalculation


class Param:
    def __init__(self, name, default=None):
        self.name = name
        self.default = default
        self._python_param = inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, default=default)

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


def _make_cmd_constituent(x):
    if isinstance(x, Param):
        return x
    elif isinstance(x, str):
        return CmdLiteral(x)
    else:
        raise TypeError("")


class ExternalCommand:
    def __init__(self, *cmd: Union[str, Param]):
        self.cmd = cmd
        self.cmd_constituents = [_make_cmd_constituent(x) for x in self.cmd]
        self.cmd_params = [x for x in cmd if isinstance(x, Param)]
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
        bound_args = self.bind(*args, **kwargs)
        # current_workdir = os.getcwd()
        # logger.debug(f"{current_workdir=}")
        proc = await asyncio.create_subprocess_exec(
            *bound_args,
            stdin=_stdin,
            stdout=_stdout,
            stderr=_stderr,
        )
        return ExternalCmdCalculation(proc)
