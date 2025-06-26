import asyncio
import os
import re
import subprocess

import anyio

from pyqcrbox import logger
from pyqcrbox.sql_models import CLICommandSpec

from .base_command import BaseCommand
from .cli_command_calculation import CLICmdCalculation

__all__ = ["CLICommand"]


class QCrBoxCmdArgumentMismatch(Exception):
    pass


class CLICommand(BaseCommand):
    def __init__(self, cmd_spec: CLICommandSpec):
        assert cmd_spec.implemented_as == "cli_command"
        super().__init__(cmd_spec)
        self.call_pattern = cmd_spec.call_pattern
        self.call_pattern_parameter_names = list(set(re.findall("{(.*?)}", self.call_pattern)))
        self.parameter_names = [p.name for p in cmd_spec.parameters]
        logger.warning(
            "TODO: validate that the call_pattern_parameter_names are a subset(?) of the yaml spec parameters"
        )

        self.proc: asyncio.subprocess.Process | None = None

    def __repr__(self):
        return f"<{self.__class__.__name__}: '{str(self)}'>"

    def __str__(self):
        return self.call_pattern

    async def bind(self, working_dir: str, **param_values):
        return self.call_pattern.format(**param_values)

    async def execute_in_background(
        self,
        _calculation_id: str,
        _stdin=None,
        _stdout=subprocess.PIPE,
        _stderr=subprocess.PIPE,
        _cwd=None,
        **kwargs,
    ) -> CLICmdCalculation:
        calc_finished_event = anyio.Event()

        working_dir = _cwd or os.getcwd()
        param_values = {k: kwargs[k] for k in self.parameter_names if k in kwargs}

        try:
            cmd_with_bound_args = await self.bind(working_dir, **param_values)
        except KeyError as exc:
            raise QCrBoxCmdArgumentMismatch(exc.args[0]) from None

        self.proc = await asyncio.create_subprocess_shell(
            cmd_with_bound_args, stdin=_stdin, stdout=_stdout, stderr=_stderr, cwd=working_dir, preexec_fn=os.setsid
        )

        return CLICmdCalculation(self.proc, calculation_id=_calculation_id, calc_finished_event=calc_finished_event)
