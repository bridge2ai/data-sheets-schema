"""Explicit registered support or fitness execution; saved commands stay offline."""
import os
from pathlib import Path

import click

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema.cli.support_results import _call
from data_sheets_schema.support_plan import canonical


@click.group("support-execution")
def support_execution():
    """Execute the explicitly declared support or fitness instrument, without retries."""


@support_execution.command("prepare")
@click.option("--descriptor", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--declaration", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
def prepare(descriptor, declaration, output):
    """Capture the request, explicit decisions and one bound run directory."""
    value = _call(execution.prepare, descriptor, declaration, output)
    click.echo(canonical({"registration": str(output), "run_output": value["declaration"]["run_output"],
                          "original_readiness": value["original_readiness"],
                          "scientific_eligibility": False}).decode())


@support_execution.command("run")
@click.option("--registration", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--credential-env", default=None, help="Explicit variable name; no credential discovery or recording.")
def run(registration, credential_env):
    """Make the registered HTTP calls once; existing run directories refuse."""
    if credential_env is not None and (not credential_env or credential_env not in os.environ):
        raise click.ClickException("Explicit credential variable is unavailable.")
    value = _call(execution.run, registration,
                  credential=os.environ[credential_env] if credential_env is not None else None)
    click.echo(canonical(value).decode())
    if not value["all_selected_accepted"]:
        raise click.ClickException("Execution stopped or remained incomplete; captured evidence is preserved.")


@support_execution.command("recheck")
@click.option("--run", "run_directory", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck(run_directory):
    """Rebuild the report from captured bytes, without another HTTP request."""
    click.echo(canonical(_call(execution.recheck, run_directory)).decode())
