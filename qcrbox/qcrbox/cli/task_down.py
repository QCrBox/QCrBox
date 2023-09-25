from .utils_doit import make_task
from .utils_docker import spin_down_docker_containers


@make_task
def task_spin_down_docker_containers(compose_file: str):
    return {
        "name": f"task_spin_down_docker_containers",
        "actions": [(spin_down_docker_containers, [compose_file])],
    }
