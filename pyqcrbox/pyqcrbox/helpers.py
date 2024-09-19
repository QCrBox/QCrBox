import os
import re
import time
from importlib import import_module
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pyqcrbox.logging import logger

__all__ = ["generate_correlation_id", "generate_data_file_id", "generate_private_routing_key"]


def generate_private_routing_key() -> str:
    result = create_unique_id(prefix="qcrbox_rk_")
    logger.debug(f"Generated private routing key: {result}")
    return result


def generate_correlation_id() -> str:
    result = create_unique_id(prefix="qcrbox_corr_id_")
    logger.debug(f"Generated random correlation id: {result}")
    return result


def generate_calculation_id() -> str:
    result = create_unique_id(prefix="qcrbox_calc_")
    logger.debug(f"Generated calculation id: {result}")
    return result


def generate_data_file_id() -> str:
    result = create_unique_id(prefix="qcrbox_df_")
    logger.debug(f"Generated data file id: {result}")
    return result


def create_unique_id(*, prefix="") -> str:
    return f"{prefix}0x{uuid4().hex}"


def greet_and_sleep(name: str, duration: float = 1.0):
    print(f"Hello {name}!")
    print(f"Going to sleep for {duration:.1f} seconds...")
    time.sleep(duration)
    print("Goodbye.")
    return f"Successfully slept for {duration:.1f} seconds"


def generic_dummy_command(msg: str, sleep_duration: float = 5.0):
    print(f"[DUMMY_COMMAND] {msg=!r}")
    print(f"[DUMMY_COMMAND] Going to sleep for {sleep_duration:.1f} seconds...")
    time.sleep(sleep_duration)
    print("[DUMMY_COMMAND] Waking up.")
    return f"[DUMMY_COMMAND] Successfully slept for {sleep_duration:.1f} seconds"


def get_qcrbox_registry_api_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
):
    host = host or os.environ.get("QCRBOX_REGISTRY_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_REGISTRY_PORT", 11000))
    url = f"http://{host}:{port}"
    return url


# def get_routing_key_for_command_invocation_requests(*, application_slug: str, application_version: str):
#     return f"qcrbox_rk_{application_slug}_{application_version}"


def sanitize_for_nats_subject(s: str):
    disallowed_chars = "[.]"
    return re.sub(disallowed_chars, "_", s)


def import_all_submodules(parent_dir: Path, parent_package_name: str):
    excluded_submodules = ["__init__", "__pycache__", "base_message_dispatcher"]

    submodules_imported = []
    for path in parent_dir.iterdir():
        submodule_name = path.name.removesuffix(".py")
        if submodule_name not in excluded_submodules:
            import_module(f".{submodule_name}", package=parent_package_name)
            submodules_imported.append(submodule_name)

    logger.debug(
        f"Found and imported the following submodules of {parent_package_name!r}: "
        f"{join_string_reprs(submodules_imported)}"
    )


def join_string_reprs(some_strings: list[str]):
    return ", ".join(repr(s) for s in some_strings)
