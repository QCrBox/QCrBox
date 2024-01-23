import inspect
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .calculation import PythonCallableCalculation


class PythonCallable:
    def __init__(self, fn: Callable):
        assert inspect.isfunction(fn)
        if inspect.iscoroutinefunction(fn):
            raise TypeError("At present PythonCallable can only handle regular functions, not coroutine functions.")

        self.fn = fn
        self.signature = inspect.signature(fn)
        self.parameter_names = list(self.signature.parameters.keys())

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.fn.__name__}{self.signature!s}>"

    async def execute_in_background(self, *args, _stdin=None, _stdout=subprocess.PIPE, _stderr=subprocess.PIPE, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.fn, *args, **kwargs)
        return PythonCallableCalculation(future)
