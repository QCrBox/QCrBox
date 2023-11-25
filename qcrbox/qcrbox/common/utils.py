import os
from typing import Optional


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


