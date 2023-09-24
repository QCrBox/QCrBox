from pathlib import Path

from .utils_doit import make_task
from .utils_docker import get_dependency_chain, build_single_docker_image


@make_task
def task_build_docker_service(service: str, compose_file: str, with_deps: bool):
    dependencies = get_dependency_chain(service, compose_file) if with_deps else []
    return {
        "name": f"task_build_service:{service}",
        "actions": [
            f"echo '[DDD] Building service: {service!r}'",
            (build_single_docker_image, (service, compose_file))
        ],
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


@make_task
def task_build_qcrbox_python_package():
    qcrbox_module_root = Path(__file__).parent.parent.parent
    return {
        "name": f"task_build_qcrbox_python_module",
        "actions": [
            f"cd {qcrbox_module_root.as_posix()} && hatch build -t wheel"
        ],
    }
