import click

from ...helpers.docker_project import DockerProject


@click.command(name="down")
def shut_down_components():
    """
    Shut down QCrBox components.
    """
    docker_project = DockerProject(name="qcrbox")

    def shut_down_docker_containers():
        docker_project.run_docker_compose_command("down")

    return {
        "name": f"task_shut_down_docker_containers",
        "actions": [shut_down_docker_containers],
    }
