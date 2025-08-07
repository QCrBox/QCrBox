import functools
import sys

import click
from loguru import logger


def add_verbose_option(f):
    @functools.wraps(f)
    def wrapper(ctx, verbose, *args, **kwargs):
        ctx.ensure_object(dict)  # ensure that ctx.obj exists and is a dict
        ctx.obj["VERBOSE"] = verbose or ctx.obj.get("VERBOSE", False)
        # if ctx.obj["VERBOSE"]:
        #     set_log_level("DEBUG")
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


def add_cli_option_to_enable_or_disable_components(f):
    DEFAULT_ALL_COMPONENTS = ("olex2", "crystal-explorer", "mopro", "qcrbox_quality", "xharpy-gpaw", "qcrboxtools")
    DEFAULT_TEST_COMPONENTS = ("olex2", "dummy_cli")
    DEFAULT_EXPLICITLY_ENABLED_COMPONENTS = ()
    DEFAULT_EXPLICITLY_DISABLED_COMPONENTS = ("shelx", "qcrbox-nextflow", "eval1x")

    @functools.wraps(f)
    def wrapper(
        ctx,
        include_all_default_components: bool,
        include_default_test_components: bool,
        enabled_components: list[str] | None,
        disabled_components: list[str] | None,
        *args,
        **kwargs,
    ):
        ctx.ensure_object(dict)  # ensure that ctx.obj exists and is a dict
        ctx.obj["DEFAULT_ALL_COMPONENTS"] = DEFAULT_ALL_COMPONENTS
        ctx.obj["DEFAULT_TEST_COMPONENTS"] = DEFAULT_TEST_COMPONENTS
        ctx.obj["DEFAULT_EXPLICITLY_ENABLED_COMPONENTS"] = DEFAULT_EXPLICITLY_ENABLED_COMPONENTS
        ctx.obj["DEFAULT_EXPLICITLY_DISABLED_COMPONENTS"] = DEFAULT_EXPLICITLY_DISABLED_COMPONENTS

        default_components = ctx.obj["DEFAULT_ALL_COMPONENTS"]
        test_components = ctx.obj["DEFAULT_TEST_COMPONENTS"]
        if enabled_components is None:
            enabled_components = DEFAULT_EXPLICITLY_ENABLED_COMPONENTS
        if disabled_components is None:
            disabled_components = set(DEFAULT_EXPLICITLY_DISABLED_COMPONENTS).difference(enabled_components)

        components = kwargs.pop("components")
        components_to_include = determine_components_to_include(
            include_all_default_components,
            include_default_test_components,
            default_components,
            test_components,
            enabled_components,
            disabled_components,
            components,
        )
        kwargs["components"] = components_to_include

        return f(*args, **kwargs)

    wrapper = click.option(
        "--disable",
        "disabled_components",
        default=None,
        show_default=True,
        metavar="COMPONENT",
        help="Explicitly exclude the given component from the build.",
        multiple=True,
    )(wrapper)

    wrapper = click.option(
        "--enable",
        "enabled_components",
        default=None,
        show_default=True,
        metavar="COMPONENT",
        help=(
            "Explicitly include the given component in the build. This only "
            "has an effect for components that are disabled by default."
        ),
        multiple=True,
    )(wrapper)

    wrapper = click.option(
        "--all",
        "include_all_default_components",
        default=False,
        show_default=True,
        is_flag=True,
        help=(
            "Include all default components. Note that any components that are disabled by default"
            "or explicitly disabled (via --disable=COMPONENT) will remain excluded."
        ),
    )(wrapper)

    wrapper = click.option(
        "--test",
        "include_default_test_components",
        default=False,
        show_default=True,
        is_flag=True,
        help="Include only the minimum required components to test QCrBox.",
    )(wrapper)

    wrapper = click.pass_context(wrapper)

    return wrapper


def determine_components_to_include(
    include_all_default_components: bool,
    include_default_test_components: bool,
    default_components: list[str],
    test_components: list[str],
    enabled_components: list[str],
    disabled_components: list[str],
    components: list[str],
) -> set[str]:
    if include_all_default_components and include_default_test_components:
        click.echo("The flags --all and --test-only cannot be used together.")
        sys.exit(1)
    if include_all_default_components:
        if not components:
            components = default_components
        else:
            click.echo("The flag --all cannot be combined with explicit component names.")
            sys.exit(1)
    if include_default_test_components:
        if not components:
            components = test_components
        else:
            click.echo("The flag --test-only cannot be combined with explicit component names.")
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
        click.echo(
            "Nothing to build. Consider using the --all or --test-only flags or specify explicit component names."
        )
        sys.exit()

    if enabled_components:
        logger.debug(f"Explicitly enabled components: {', '.join(enabled_components)}")
    if disabled_components:
        logger.debug(f"Explicitly disabled components: {', '.join(disabled_components)}")

    return components_to_include
