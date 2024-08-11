import re

import anyio

from pyqcrbox import sql_models_NEW_v2

__all__ = ["CLICommand"]


# SPDX-License-Identifier: MPL-2.0

import asyncio
import inspect
import subprocess

from pyqcrbox import logger

from .base_command import BaseCommand
from .calculation import CLICmdCalculation


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
        raise TypeError(f"Invalid constituent of CLI command: {x!r} (type: {type(x)})")


class QCrBoxCmdArgumentMismatch(Exception):
    pass


class CLICommand(BaseCommand):
    def __init__(self, cmd_spec: sql_models_NEW_v2.command_spec.command_spec.CommandSpecDiscriminatedUnion):
        super().__init__(cmd_spec)
        self.call_pattern = cmd_spec.call_pattern
        self.call_pattern_parameter_names = list(set(re.findall("{(.*?)}", self.call_pattern)))
        self.parameter_names = [p.name for p in cmd_spec.parameters]
        logger.warning(
            f"TODO: validate that the call_pattern_parameter_names are a subset(?) of the yaml spec parameters"
        )

        self.proc: asyncio.subprocess.Process | None = None

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{str(self)}'>"

    def __str__(self):
        return self.call_pattern

    def bind(self, **kwargs):
        logger.debug(f"[DDD] {self.call_pattern=!r}")
        logger.debug(f"[DDD] {kwargs=!r}")
        return self.call_pattern.format(**kwargs)

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin=None,
        _stdout=subprocess.PIPE,
        _stderr=subprocess.PIPE,
        **kwargs,
    ) -> CLICmdCalculation:
        calc_finished_event = anyio.Event()

        try:
            cmd_with_bound_args = self.bind(**kwargs)
        except KeyError as exc:
            raise QCrBoxCmdArgumentMismatch(exc.args[0])

        self.proc = await asyncio.create_subprocess_shell(
            cmd_with_bound_args,
            stdin=_stdin,
            stdout=_stdout,
            stderr=_stderr,
        )

        return CLICmdCalculation(self.proc, calculation_id=_calculation_id, calc_finished_event=calc_finished_event)

    async def terminate(self):
        if self.proc:
            logger.debug("Terminating process running CLI command.")
            self.proc.terminate()
            logger.trace("Process terminated.")
        else:
            logger.trace(f"No process running for {self} - nothing to terminate.")
