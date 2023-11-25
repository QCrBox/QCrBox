import atexit
import shutil
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path

import click
import doit.task

from ...helpers import run_tasks, NaturalOrderGroup

try:
    import mkdocs
except ImportError:
    click.echo(
        "MkDocs is not installed. Please run 'pip install qcrbox[docs]' "
        "to install mkdocs and other documentation-related dependencies."
    )
    sys.exit(1)

@click.group(name="docs", cls=NaturalOrderGroup)
def docs_build_and_serve():
    """
    Build/serve the documentation.
    """
    pass


def get_mkdocs_config_file_path():
    return Path(__file__).parent.parent.parent.parent.parent.parent.joinpath("mkdocs.yml").resolve().as_posix()


@docs_build_and_serve.command()
def build():
    """
    Build the documentation.
    """
    task = doit.task.dict_to_task(
        {
            "name": "build-docs",
            "actions": [f"mkdocs build -f {get_mkdocs_config_file_path()}"],
        }
    )
    run_tasks([task])


@docs_build_and_serve.command()
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

    def build_and_serve_docs():
        mkdocs_executable = shutil.which("mkdocs")
        proc = subprocess.Popen([mkdocs_executable, "serve", "-a", dev_addr, "-f", get_mkdocs_config_file_path()])
        atexit.register(wait_for_mkdocs_server_shutdown, proc)

    def wait_for_mkdocs_server_shutdown(proc):
        print("Waiting for mkdocs server to shut down...")
        proc.wait()
        print("Done.")

    def open_url(url):
        webbrowser.open(url, new=2)

    dev_addr = f"{host}:{port}"
    url = f"http://{dev_addr}"
    task1 = doit.task.dict_to_task(
        {
            "name": "build-and-serve-docs",
            "actions": [(build_and_serve_docs,)],
        }
    )
    task2 = doit.task.dict_to_task(
        {
            "name": "open-browser",
            "actions": [(open_url, [url])],
        }
    )
    run_tasks([task1, task2])

    signal.pause()
