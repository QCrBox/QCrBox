from typing import Optional
from .utils_doit import make_task


@make_task
def task_build_service(service: str, deps: Optional[list[str]] = None):
    deps = deps or []
    return {
        "name": f"task_build_services:{service}",
        "actions": [f"echo '[DDD] Building services: {service!r}'"],
        "task_dep": [f"task_build_services:{dep}" for dep in deps],
    }
