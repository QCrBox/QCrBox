# SPDX-License-Identifier: MPL-2.0
import sys
import time
from pathlib import Path

import click
import requests

from pyqcrbox import settings
from pyqcrbox.sql_models import ApplicationSpec

from ..helpers import ClickCommandCls, DockerProject
from ..helpers.image_resolution import resolve_docker_image_for_spec_file


def find_spec_file_for_component(docker_project: DockerProject, component: str) -> Path | None:
    """Locate the `config_*.yaml` application spec in a component's build context."""
    try:
        build_context = docker_project.get_build_context(component)
    except Exception:
        return None
    spec_files = sorted(Path(build_context).glob("config_*.yaml"))
    return spec_files[0] if spec_files else None


def collect_spec_files(docker_project: DockerProject, targets: tuple[str, ...]) -> list[Path]:
    """Resolve CLI arguments (spec file paths or component names) to spec files."""
    spec_files = []
    for target in targets:
        target_path = Path(target)
        if target_path.is_file():
            spec_files.append(target_path)
            continue
        spec_file = find_spec_file_for_component(docker_project, target)
        if spec_file is None:
            click.echo(f"Error: {target!r} is neither a spec file nor a component with a config_*.yaml")
            sys.exit(1)
        spec_files.append(spec_file)
    return spec_files


def register_spec_file(spec_file: Path, docker_image: str | None = None) -> tuple[bool, str]:
    """Parse a spec YAML file and register it with the registry API."""
    application_spec = ApplicationSpec.from_yaml_file(spec_file)
    application_spec.docker_image = docker_image
    try:
        r = requests.post(
            settings.registry.server.api_url + "/applications",
            json=application_spec.model_dump(mode="json"),
        )
    except requests.exceptions.ConnectionError:
        return False, f"could not connect to QCrBox registry at {settings.registry.server.api_url}"

    if r.status_code == 201:
        return True, f"registered {application_spec.slug!r} (version {application_spec.version!r})"
    try:
        error_message = r.json()["error"]["message"]
    except Exception:
        error_message = r.text
    return False, f"registration of {application_spec.slug!r} failed ({r.status_code}): {error_message}"


def wait_for_registry_api(timeout: float = 60.0, poll_interval: float = 2.0) -> bool:
    """Poll the registry health endpoint until it responds or the timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = requests.get(settings.registry.server.api_url + "/healthz", timeout=5)
            if r.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(poll_interval)
    return False


def register_specs_for_components(docker_project: DockerProject, components: list[str]) -> None:
    """Best-effort registration of application specs after `qcb up` (warns, never fails)."""
    components = components or docker_project.services_excluding_base_images
    spec_files = []
    for component in components:
        spec_file = find_spec_file_for_component(docker_project, component)
        if spec_file is not None:
            spec_files.append(spec_file)

    if not spec_files:
        return

    if not wait_for_registry_api():
        click.echo(
            "Warning: QCrBox registry did not become healthy in time; "
            "application specs were not registered. Run 'qcb register' manually."
        )
        return

    for spec_file in spec_files:
        try:
            docker_image = resolve_docker_image_for_spec_file(docker_project, spec_file)
            success, message = register_spec_file(spec_file, docker_image=docker_image)
        except Exception as exc:
            success, message = False, f"failed to register spec {str(spec_file)!r}: {exc}"
        click.echo(message if success else f"Warning: {message}")


@click.command(name="register", cls=ClickCommandCls)
@click.argument("targets", nargs=-1, required=True)
def register_application_specs(targets: tuple[str, ...]):
    """Register application specs with the QCrBox registry.

    TARGETS can be paths to application spec files (config_*.yaml) or
    component names (as listed by 'qcb list components'). The registry
    must be running. Registration is idempotent.
    """
    docker_project = DockerProject()
    spec_files = collect_spec_files(docker_project, targets)

    any_failed = False
    for spec_file in spec_files:
        docker_image = resolve_docker_image_for_spec_file(docker_project, spec_file)
        success, message = register_spec_file(spec_file, docker_image=docker_image)
        click.echo(("✔ " if success else "× ") + message)
        any_failed = any_failed or not success

    if any_failed:
        sys.exit(1)
