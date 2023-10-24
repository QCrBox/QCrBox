import click
import doit.task
import webbrowser

from ..helpers import run_tasks


@click.group(name="docs")
def docs_group():
    """
    Build or serve the documentation.
    """
    pass


@docs_group.command()
def build():
    """
    Build the documentation.
    """
    task = doit.task.dict_to_task(
        {
            "name": "build-docs",
            "actions": ["mkdocs build"],
        }
    )
    run_tasks([task])


@docs_group.command()
@click.option(
    "-h",
    "--host",
    "host",
    type=click.STRING,
    default="localhost",
    help="Host to serve documentation locally (default: localhost)",
)
@click.option(
    "-p",
    "--port",
    "port",
    type=click.INT,
    default=8000,
    help="Port to serve documentation locally (default: 8000)",
)
def serve(host, port):
    """
    Serve the documentation using the MkDocs development server.
    """
    dev_addr = f"{host}:{port}"
    url = f"http://{dev_addr}"
    task1 = doit.task.dict_to_task(
        {
            "name": "serve-docs",
            "actions": [f"mkdocs serve -a {dev_addr}"],
        }
    )
    task2 = doit.task.dict_to_task(
        {"name": "open-browser", "actions": [webbrowser.open(url, new=2)]}
    )
    run_tasks([task1, task2])
