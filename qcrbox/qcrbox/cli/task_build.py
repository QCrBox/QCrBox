from pathlib import Path

from .utils_doit import make_task
from .utils_docker import get_dependency_chain, build_single_docker_image


@make_task
def task_build_service(service: str, compose_file: str, with_deps: bool):
    dependencies = get_dependency_chain(service, compose_file) if with_deps else []
    return {
        "name": f"task_build_services:{service}",
        "actions": [
            f"echo '[DDD] Building service: {service!r}'",
            (build_single_docker_image, (service, compose_file))
        ],
        "task_dep": [f"task_build_services:{dep}" for dep in dependencies],
    }
