import logging


def get_log_level_int(log_level: int | str):
    if isinstance(log_level, int):
        log_level_int = log_level
    elif isinstance(log_level, str):
        log_level_int = logging.getLevelName(log_level)
        if not isinstance(log_level_int, int):
            raise ValueError(f"Unkown log level: {log_level}")
    else:
        raise TypeError(f"Invalid log level (must be a valid string or integer): {log_level}")

    return log_level_int
