import click

__all__ = ["print_command_help_string_and_exit", "exit_with_msg"]


def print_command_help_string_and_exit():
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()


def exit_with_msg(msg):
    ctx = click.get_current_context()
    ctx.fail(msg)
