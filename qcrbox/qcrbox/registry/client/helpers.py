# SPDX-License-Identifier: MPL-2.0

import os
from typing import Optional
from uuid import uuid4

__all__ = ["create_new_private_routing_key"]


def create_new_private_routing_key():
    return create_unique_id(prefix="qcrbox_rk_")


def create_unique_id(*, prefix=""):
    return f"{prefix}0x{uuid4().hex}"


def create_new_container_qcrbox_id(env_vars: Optional[dict] = None):
    env_vars = env_vars or os.environ
    qcrbox_container_id = env_vars.get("QCRBOX_CONTAINER_ID", None) or create_unique_id(prefix="qcrbox_container_")
    # with open("/opt/qcrbox/qcrbox_container_qcrbox_id.txt", "w") as f:
    #     f.write(qcrbox_container_id)
    return qcrbox_container_id
