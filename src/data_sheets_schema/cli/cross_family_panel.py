"""Offline declaration and reconstruction of an exact semantic rating panel."""
from pathlib import Path

import click

from data_sheets_schema import cross_family_panel as panels
from data_sheets_schema.cli.support_results import _call
from data_sheets_schema.support_plan import canonical


@click.group("cross-family-panel")
def cross_family_panel():
    """Capture a fixed panel before ratings; never dispatch or score requests."""


@cross_family_panel.command("prepare")
@click.option("--declaration", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--root", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Explicit base directory for the declaration's local evidence paths.")
@click.option("--output", required=True, type=click.Path(path_type=Path),
              help="New panel directory; existing artifacts are preserved.")
def prepare(declaration, root, output):
    """Bind selected records, instruments and attempts; retain pending decisions."""
    click.echo(canonical(_call(panels.prepare_panel, declaration, output, root=root)).decode())


@cross_family_panel.command("recheck")
@click.option("--panel", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck(panel):
    """Reconstruct the captured declaration without original files or ratings."""
    click.echo(canonical(_call(panels.recheck_panel, panel)).decode())
