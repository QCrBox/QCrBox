import inspect
import itertools
from functools import wraps
from typing import Callable

from pyqcrbox import logger

_global_count = itertools.count()  # Thread-safe unique ID generator


def _log_enter(id: int, func_name: str) -> None:
    logger.debug(f"[Enter {id}] {func_name}")


def _log_exit(id: int, full_name: str) -> None:
    logger.debug(f"[Exit  {id}] {full_name}")


def log_trace(func: Callable) -> Callable:
    """Log entry and exit for a function.

    Both synchronous and asynchronous functions are supported.

    Parameters
    ----------
    func : callable
        The function to wrap, to log its entry and exit.

    Returns
    -------
    callable
        The wrapped function with logging.
    """

    def _get_func_name(args):
        func_name = func.__name__
        module_name = func.__module__
        class_name = f"{args[0].__class__.__name__}." if args and hasattr(args[0], "__class__") else ""
        return f"{module_name}.{class_name}::{func_name}"

    @wraps(func)
    async def _async_wrapper(*args, **kwargs):
        count = next(_global_count)
        full_name = _get_func_name(args)

        _log_enter(count, full_name)
        result = await func(*args, **kwargs)
        _log_exit(count, full_name)

        return result

    @wraps(func)
    def _sync_wrapper(*args, **kwargs):
        count = next(_global_count)
        function_name = _get_func_name(args)

        _log_enter(count, function_name)
        result = func(*args, **kwargs)
        _log_exit(count, function_name)

        return result

    return _async_wrapper if inspect.iscoroutinefunction(func) else _sync_wrapper
