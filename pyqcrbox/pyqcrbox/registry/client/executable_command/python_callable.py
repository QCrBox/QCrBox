# SPDX-License-Identifier: MPL-2.0
import importlib
import inspect
import multiprocessing.pool
import multiprocessing.process
import traceback

import anyio
from pydantic._internal._validate_call import ValidateCallWrapper

from pyqcrbox import logger
from pyqcrbox.sql_models import PythonCallableSpec

from . import BaseCommand
from .python_callable_calculation import PythonCallableCalculation

__all__ = ["PythonCallable"]


class CalculationNotRunning(Exception):
    pass


class PythonCallable(BaseCommand):
    """Command class for executing Python callables as background calculations.

    Parameters
    ----------
    cmd_spec : PythonCallableSpec
        The command specification for the Python callable.

    """

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

        self.cmd_spec = cmd_spec
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
        self.pool: multiprocessing.pool.Pool | None = None
        self.calc_finished_event = None

    def _extract_parameters_from_callable_signature(self) -> dict:
        """Extract parameter names and types from the callable's signature.

        Returns
        -------
        dict
            Dictionary mapping parameter names to their type names.

        """
        return {name: p.annotation.__name__ for (name, p) in self.signature.parameters.items()}

    def __repr__(self):
        """Return a string representation of the PythonCallable instance.

        Returns
        -------
        str
            String representation of the object.

        """
        return f"<{self.__class__.__name__}: {self.fn.__name__}{self.signature!s}>"

    async def execute_in_background(
        self,
        *args,
        _calculation_id: str,
        _stdin=None,
        _stdout=None,
        _stderr=None,
        _cwd=None,
        _num_processes=1,
        **kwargs,
    ) -> PythonCallableCalculation:
        """Execute the Python callable asynchronously in the background.

        Parameters
        ----------
        *args
            Positional arguments to pass to the callable.
        _calculation_id : str
            Unique identifier for the calculation instance.
        _stdin : Any, optional
            Standard input stream or data (default is None).
        _stdout : Any, optional
            Standard output stream or handler (default is None).
        _stderr : Any, optional
            Standard error stream or handler (default is None).
        _cwd : Any, optional
            Working directory for command execution (default is None).
        _num_processes : int, optional
            Number of processes to use in the pool (default is 1).
        **kwargs
            Additional keyword arguments for callable execution.

        Returns
        -------
        PythonCallableCalculation
            An instance representing the background calculation.

        """
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
                f"PythonCallable Error: {exc=} ({multiprocessing.process.current_process().name})\n\n"
                + f"Traceback:\n\n{traceback_str}"
            )
            calc_finished_event.set()
            calc_finished_event = None

        self.pool = multiprocessing.pool.Pool(_num_processes)
        if _cwd:
            logger.warning(
                "TODO: Change into working directory before executing the python callable (and switch back afterwards)!"
            )
        param_values = {k: kwargs[k] for k in self.parameter_names if k in kwargs}

        pending_result = self.pool.apply_async(
            self._fn_with_call_args_validation,
            args,
            param_values,
            callback=success_callback,
            error_callback=error_callback,
        )

        return PythonCallableCalculation(
            pending_result,
            pool=self.pool,
            calculation_id=_calculation_id,
            calc_finished_event=calc_finished_event,
        )
