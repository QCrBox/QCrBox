from .utils_doit import make_task
from .utils_docker import start_up_docker_containers


@make_task
def task_start_up_docker_containers(target_containers: list[str], compose_file: str, rebuild_deps: bool, dry_run: bool):
    return {
        "name": f"task_start_up_docker_containers",
        "actions": [(start_up_docker_containers, (target_containers, compose_file, dry_run))],
    }
