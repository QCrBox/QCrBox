import click


@click.group(name="docs")
def docs_group():
    """
    Build or serve the documentation.
    """
    pass


@docs_group.command()
def build():
    """
    asdfasdfsdfasdf
    """
    click.echo("This is the 'docs build' subcommand'")
