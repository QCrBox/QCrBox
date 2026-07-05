# SPDX-License-Identifier: MPL-2.0
"""Resolve the docker image name for an application from its compose file.

The compose files are the single source of truth for image names (which do
not necessarily match the application slug, e.g. slug `olex2` uses the image
`qcrbox/olex2-linux`). The CLI loads compose YAML without variable
interpolation, so `image:` values like `qcrbox/dummy_cli:${QCRBOX_DOCKER_TAG}`
are interpolated here against the same env file that `docker compose` would
use.
"""

import os
import re
from pathlib import Path

from dotenv import dotenv_values
from loguru import logger

__all__ = ["interpolate_compose_value", "resolve_docker_image_for_spec_file"]

# ${VAR}, ${VAR:?message}, ${VAR:-default}, ${VAR-default}
_COMPOSE_VARIABLE_REGEX = re.compile(
    r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:(?P<op>:\?|\?|:-|-)(?P<arg>[^}]*))?\}"
)


def load_compose_env_vars(docker_project) -> dict[str, str]:
    """Load the env file that `docker compose` would use for this project config."""
    env_file_name = ".env.prod" if docker_project.config_name == "prebuilt" else ".env.dev"
    env_file = Path(docker_project.repo_root) / env_file_name
    return {key: value for key, value in dotenv_values(env_file).items() if value is not None}


def interpolate_compose_value(raw_value: str, env_vars: dict[str, str]) -> str:
    """Interpolate `${VAR}`-style references the way docker compose would."""

    def lookup(name: str) -> str | None:
        # Real environment variables take precedence over the env file,
        # mirroring docker compose behaviour.
        return os.environ.get(name, env_vars.get(name))

    def replace(match: re.Match) -> str:
        name, op, arg = match.group("name"), match.group("op"), match.group("arg")
        value = lookup(name)
        if value:
            return value
        if op in (":-", "-"):
            return arg
        if op in (":?", "?"):
            raise ValueError(f"Required variable {name!r} is not set: {arg or 'no message'}")
        return value or ""

    return _COMPOSE_VARIABLE_REGEX.sub(replace, raw_value)


def resolve_docker_image_for_spec_file(docker_project, spec_file) -> str | None:
    """Resolve the (interpolated) docker image for the application whose spec lives in `spec_file`.

    Matches the compose service whose build context is the spec file's
    directory; if no service has a build context there (e.g. the prebuilt
    config), falls back to services defined in a compose file located in that
    directory. Returns None (with a warning) if no image can be determined.
    """
    spec_dir = Path(spec_file).resolve().parent
    compose_config = docker_project.compose_file_config
    repo_root = Path(docker_project.repo_root)

    raw_image = _find_image_by_build_context(compose_config, repo_root, spec_dir)
    if raw_image is None:
        raw_image = _find_image_by_compose_file_location(compose_config, repo_root, spec_dir)
    if raw_image is None:
        logger.warning(
            f"Could not determine the docker image for the application spec in {str(spec_dir)!r}; "
            "on-demand spawning will not be available for it."
        )
        return None

    try:
        return interpolate_compose_value(raw_image, load_compose_env_vars(docker_project))
    except ValueError as exc:
        logger.warning(f"Could not interpolate docker image {raw_image!r}: {exc}")
        return None


def _find_image_by_build_context(compose_config, repo_root: Path, spec_dir: Path) -> str | None:
    for service_metadata in compose_config._full_service_metadata["services"].values():
        raw_image = service_metadata.get("image")
        build_section = service_metadata.get("build")
        if raw_image is None or build_section is None:
            continue
        context = build_section.get("context") if isinstance(build_section, dict) else build_section
        if context is not None and (repo_root / context).resolve() == spec_dir:
            return raw_image
    return None


def _find_image_by_compose_file_location(compose_config, repo_root: Path, spec_dir: Path) -> str | None:
    for compose_file, compose_data in compose_config._service_metadata_by_compose_file.items():
        if (repo_root / compose_file).parent.resolve() != spec_dir:
            continue
        for service_metadata in compose_data.get("services", {}).values():
            raw_image = service_metadata.get("image")
            if raw_image is not None:
                return raw_image
    return None
