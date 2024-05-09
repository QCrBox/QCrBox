import os
import time
from importlib import import_module
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pydantic

from pyqcrbox import logger

__all__ = ["generate_correlation_id", "generate_private_routing_key"]


def generate_private_routing_key():
    result = create_unique_id(prefix="qcrbox_rk_")
    logger.debug(f"Generated private routing key: {result}")
    return result


def generate_correlation_id():
    result = create_unique_id(prefix="qcrbox_corr_id_")
    logger.debug(f"Generated random correlation id: {result}")
    return result


def create_unique_id(*, prefix=""):
    return f"{prefix}0x{uuid4().hex}"


def print_and_sleep(duration: float = 1.0):
    print("Hello world!")
    time.sleep(duration)
    print("Goodbye.")
    return f"Successfully slept for {duration:.1f} seconds"


def get_rabbitmq_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    host = host or os.environ.get("QCRBOX_RABBITMQ_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_RABBITMQ_PORT", 5672))
    username = username or os.environ.get("QCRBOX_RABBITMQ_USERNAME", "guest")
    password = password or os.environ.get("QCRBOX_RABBITMQ_PASSWORD", "guest")
    url = f"amqp://{username}:{password}@{host}:{port}/"
    return url


def get_qcrbox_registry_api_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
):
    host = host or os.environ.get("QCRBOX_REGISTRY_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_REGISTRY_PORT", 11000))
    url = f"http://{host}:{port}"
    return url


def get_routing_key_for_command_invocation_requests(*, application_slug: str, application_version: str):
    return f"qcrbox_rk_{application_slug}_{application_version}"


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


def ensure_dict(value: dict | pydantic.BaseModel) -> dict:
    try:
        return value.model_dump()
    except AttributeError:
        return value
