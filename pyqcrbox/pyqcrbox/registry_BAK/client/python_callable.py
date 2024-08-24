# SPDX-License-Identifier: MPL-2.0
import importlib
import inspect
import multiprocessing
import subprocess
from typing import Callable

from loguru import logger

from .calculation import PythonCallableCalculation


class PythonCallable:
    def __init__(self, fn: Callable):
        assert inspect.isfunction(fn)
        if inspect.iscoroutinefunction(fn):
            raise TypeError("At present PythonCallable can only handle regular functions, not coroutine functions.")

        self.fn = fn
        self.signature = inspect.signature(fn)
        self.parameter_names = list(self.signature.parameters.keys())

    @classmethod
    def from_command_spec(cls, cmd_spec) -> "PythonCallable":
        assert cmd_spec.implemented_as == "python_callable"
        assert cmd_spec.import_path is not None
        module = importlib.import_module(cmd_spec.import_path)
        fn = getattr(module, cmd_spec.name)
        return cls(fn)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.fn.__name__}{self.signature!s}>"

    async def execute_in_background(
        self,
        *args,
        _stdin=None,
        _stdout=subprocess.PIPE,
        _stderr=subprocess.PIPE,
        _num_processes=1,
        **kwargs,
    ):
        def success_callback(result):
            logger.debug(f"Success: {result=} ({multiprocessing.current_process().name})")

        def error_callback(exc):
            logger.error(f"Error: {exc=} ({multiprocessing.current_process().name})")

        pool = multiprocessing.Pool(_num_processes)
        result = pool.apply_async(self.fn, args, kwargs, callback=success_callback, error_callback=error_callback)
        return PythonCallableCalculation(result)
