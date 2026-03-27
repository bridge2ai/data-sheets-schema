"""D4D Command-Line Interface.

Unified CLI for D4D data sheets schema operations.

Usage:
    d4d --help
    d4d download sources --project AI_READI
    d4d evaluate presence --project AI_READI --method gpt5
    d4d utils status --quick
"""

import click

@click.group()
@click.version_option()
def cli():
    """D4D command-line interface for dataset documentation."""
    pass

# Import and register subcommands
from . import download, evaluate, utils, rocrate, schema, render

cli.add_command(download.download)
cli.add_command(evaluate.evaluate)
cli.add_command(utils.utils)
cli.add_command(rocrate.rocrate)
cli.add_command(schema.schema)
cli.add_command(render.render)

if __name__ == "__main__":
    cli()
