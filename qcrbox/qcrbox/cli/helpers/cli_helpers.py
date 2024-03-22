import functools
import sys

import click
from loguru import logger

from qcrbox.cli.helpers import DockerProject
from qcrbox.logging import set_cli_log_level


def add_verbose_option(f):
    @functools.wraps(f)
    def wrapper(ctx, verbose, *args, **kwargs):
        ctx.ensure_object(dict)  # ensure that ctx.obj exists and is a dict
        ctx.obj["VERBOSE"] = verbose or ctx.obj.get("VERBOSE", False)
        if ctx.obj["VERBOSE"]:
            set_cli_log_level("DEBUG")
        return f(*args, **kwargs)

    wrapper = click.option(
        "-v",
        "--verbose",
        is_flag=True,
        default=None,
        help="Enables verbose mode (will print debugging messages about actions performed). [default: False]",
    )(wrapper)
    wrapper = click.pass_context(wrapper)

    return wrapper


def add_cli_option_enable_disable_components(f):
    DEFAULT_EXPLICITLY_ENABLED_COMPONENTS = ()
    DEFAULT_EXPLICITLY_DISABLED_COMPONENTS = ("shelx", "qcrbox-nextflow")

    f = click.option(
        "--disable",
        "disabled_components",
        default=DEFAULT_EXPLICITLY_DISABLED_COMPONENTS,
        show_default=True,
        metavar="COMPONENT",
        help="Explicitly exclude the given component from the build.",
        multiple=True,
    )(f)

    f = click.option(
        "--enable",
        "enabled_components",
        default=DEFAULT_EXPLICITLY_ENABLED_COMPONENTS,
        show_default=True,
        metavar="COMPONENT",
        help=(
            "Explicitly include the given component in the build. This only "
            "has an effect for components that are disabled by default."
        ),
        multiple=True,
    )(f)

    f = click.option(
        "--all",
        "include_all_components",
        default=False,
        show_default=True,
        is_flag=True,
        help=(
            "Include all components. Note that any components that are disabled by default"
            "or explicitly disabled (via --disable=COMPONENT) will remain excluded."
        ),
    )(f)

    return f


def determine_components_to_include(
    docker_project: DockerProject,
    include_all_components: bool,
    enabled_components: list[str],
    disabled_components: list[str],
    components: list[str],
):
    if include_all_components:
        if not components:
            components = docker_project.services_including_base_images
        else:
            click.echo("The flag --all cannot be combined with explicit component names.")
            sys.exit(1)

    simultaneously_enabled_and_disabled = set(enabled_components).intersection(disabled_components)
    if simultaneously_enabled_and_disabled:
        click.echo(
            "The following components are simultaneously enabled and disabled, which is not allowed: "
            f"{', '.join(simultaneously_enabled_and_disabled)}"
        )
        sys.exit(1)

    components_to_include = set(components).union(enabled_components).difference(disabled_components)
    if not components_to_include:
        click.echo("Nothing to build. Consider using the --all flag or specify explicit component names.")
        sys.exit()

    if enabled_components:
        logger.debug(f"Explicitly enabled components: {', '.join(enabled_components)}")
    if disabled_components:
        logger.debug(f"Explicitly disabled components: {', '.join(disabled_components)}")
