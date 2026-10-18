"""Offline control registration and reconstruction of support calibration evidence."""
from pathlib import Path

import click

from data_sheets_schema import support_calibration as calibration
from data_sheets_schema.cli.support_results import _call
from data_sheets_schema.support_plan import canonical


@click.group("support-calibration")
def support_calibration():
    """Bind controls and inspect captured evidence; never dispatch requests."""


@support_calibration.command("prepare")
@click.option("--registration", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--controls", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path),
              help="New calibration directory; existing output is preserved.")
def prepare(registration, controls, output):
    """Capture explicit control labels against one exact execution registration."""
    click.echo(canonical(_call(calibration.prepare, registration, controls, output)).decode())


@support_calibration.command("report")
@click.option("--calibration", "calibration_directory", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--run", "run_directory", default=None,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Captured execution directory; omission leaves observations missing.")
@click.option("--output", default=None, type=click.Path(path_type=Path),
              help="Optional new directory containing a portable report and its evidence.")
def report(calibration_directory, run_directory, output):
    """Reconstruct verdicts and denominators while retaining unresolved controls."""
    click.echo(canonical(_call(calibration.report, calibration_directory,
                               run_path=run_directory, output=output)).decode())


@support_calibration.command("recheck")
@click.option("--calibration", "calibration_directory", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Captured controls or portable report directory.")
def recheck(calibration_directory):
    """Verify captured bytes and reconstruct results without a provider request."""
    click.echo(canonical(_call(calibration.recheck, calibration_directory)).decode())
