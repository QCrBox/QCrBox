# SPDX-License-Identifier: MPL-2.0
import importlib
import inspect
import multiprocessing.pool
import multiprocessing.process
import traceback
from typing import Union

import anyio
from pydantic._internal._validate_call import ValidateCallWrapper

from pyqcrbox import logger
from pyqcrbox.sql_models_NEW_v2 import PythonCallableSpec

from . import BaseCommand
from .python_callable_calculation import PythonCallableCalculation

__all__ = ["PythonCallable"]


class CalculationNotRunning(Exception):
    pass


class PythonCallable(BaseCommand):
    def __init__(self, cmd_spec: PythonCallableSpec):
        assert cmd_spec.implemented_as == "python_callable"
        assert cmd_spec.import_path is not None
        assert cmd_spec.callable_name is not None
        super().__init__(cmd_spec)

        module = importlib.import_module(cmd_spec.import_path)
        fn = getattr(module, cmd_spec.callable_name)
        assert inspect.isfunction(fn)
        if inspect.iscoroutinefunction(fn):
            raise TypeError("At present PythonCallable can only handle regular functions, not coroutine functions.")

        self.fn = fn
        self.signature = inspect.signature(fn)
        self.parameters = self._extract_parameters_from_callable_signature()
        self.parameter_names = list(self.parameters.keys())
        self._fn_with_call_args_validation = ValidateCallWrapper(
            self.fn,
            config=None,
            validate_return=False,
            namespace=None,
        )
        self.pool: Union[multiprocessing.pool.Pool, None] = None
        self.calc_finished_event = None

    def _extract_parameters_from_callable_signature(self) -> dict:
        return {name: p.annotation.__name__ for (name, p) in self.signature.parameters.items()}

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.fn.__name__}{self.signature!s}>"

    async def execute_in_background(
        self,
        *args,
        _calculation_id: str,
        # _stdin=None,
        # _stdout=subprocess.PIPE,
        # _stderr=subprocess.PIPE,
        _num_processes=1,
        _cwd=None,
        **kwargs,
    ):
        calc_finished_event = anyio.Event()

        def success_callback(result):
            nonlocal calc_finished_event
            logger.debug(f"Success: {result=} ({multiprocessing.process.current_process().name})")
            calc_finished_event.set()
            calc_finished_event = None

        def error_callback(exc):
            nonlocal calc_finished_event
            traceback_str = "\n".join(traceback.format_exception(exc))
            logger.error(
                f"Error: {exc=} ({multiprocessing.process.current_process().name})\n\nTraceback:\n\n{traceback_str}"
            )
            calc_finished_event.set()
            calc_finished_event = None

        self.pool = multiprocessing.pool.Pool(_num_processes)
        if _cwd:
            logger.warning(
                f"TODO: Change into working directory before executing "
                f"the python callable (and switch back afterwards)!"
            )
        pending_result = self.pool.apply_async(
            self._fn_with_call_args_validation,
            args,
            kwargs,
            callback=success_callback,
            error_callback=error_callback,
        )

        return PythonCallableCalculation(
            pending_result,
            pool=self.pool,
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
        )

    async def terminate(self):
        logger.debug(f"Terminating {self}")
        self.pool.terminate()
