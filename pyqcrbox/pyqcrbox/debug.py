import inspect
from collections.abc import Callable
from functools import wraps

from pyqcrbox import logger


def _log_enter(func_name: str) -> None:
    logger.debug(f"[EEL][ENTER] {func_name}")


def _log_exit(full_name: str) -> None:
    logger.debug(f"[EEL][EXIT] {full_name}")


def log_eel(func: Callable) -> Callable:
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
        class_name = f"{args[0].__class__.__name__}" if args and hasattr(args[0], "__class__") else ""
        return f"{module_name}.{class_name}::{func_name}"

    @wraps(func)
    async def _async_wrapper(*args, **kwargs):
        func_name = _get_func_name(args)

        _log_enter(func_name)
        result = await func(*args, **kwargs)
        _log_exit(func_name)

        return result

    @wraps(func)
    def _sync_wrapper(*args, **kwargs):
        func_name = _get_func_name(args)

        _log_enter(func_name)
        result = func(*args, **kwargs)
        _log_exit(func_name)

        return result

    return _async_wrapper if inspect.iscoroutinefunction(func) else _sync_wrapper
