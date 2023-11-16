import click
import doit.task

from qcrbox.cli.helpers import run_tasks


@click.command()
@click.argument("target")
def purge(target):
    """
    Purge the given target. Currently, the only supported target is "qcrbox-registry-db".
    """
    match target:
        case "qcrbox-registry-db":
            task = doit.task.dict_to_task(
                {
                    "name": "purge-qcrbox-registry-db",
                    "actions": [f"echo 'TODO: implement me'"],
                }
            )
            run_tasks([task])
        case _:
            click.echo(f"Unsupported target: {target}")
