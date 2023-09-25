from pathlib import Path

from loguru import logger

from .utils_doit import make_task
from .utils_docker import get_dependency_chain, build_single_docker_image


@make_task
def task_build_docker_service(service: str, compose_file: str, with_deps: bool, dry_run: bool):
    dependencies = get_dependency_chain(service, compose_file) if with_deps else []
    return {
        "name": f"task_build_service:{service}",
        "actions": [(build_single_docker_image, (service, compose_file, dry_run))],
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


@make_task
def task_build_qcrbox_python_package(dry_run: bool):
    qcrbox_module_root = Path(__file__).parent.parent.parent
    if dry_run:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [lambda: logger.debug("Building Python package: 'qcrbox'")],
        }
    else:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [
                f"cd {qcrbox_module_root.as_posix()} && "
                f"hatch build -t wheel && "
                f"cp dist/qcrbox-*.whl ../services/base_images/base_ancestor/"
            ],
        }
