"""Explicit offline nested-support response commands; no provider dispatch."""
from pathlib import Path

import click

from data_sheets_schema import nested_support_results as results
from data_sheets_schema.support_plan import canonical


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.group("support-results")
def support_results():
    """Check SAVED nested-support responses offline; never execute requests."""


@support_results.command("prepare")
@click.option("--plan", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path), help="New descriptor directory.")
@click.option("--protocol", required=True, type=click.Choice([results.FORMAT]))
@click.option("--select", "selections", required=True, multiple=True, nargs=2,
              metavar="TARGET_ID ATTEMPT_ID", help="One explicit attempt per target; repeat for a subset.")
def prepare(plan, output, protocol, selections):
    """Bind a selected subset of an existing draft plan to an offline contract."""
    value = _call(results.prepare, plan, output, protocol=protocol,
                  selections=[{"target_id": t, "attempt_id": a} for t, a in selections])
    click.echo(canonical({"descriptor": str(output / "descriptor.json"),
                         "selected_targets": len(value["selections"]), "readiness": value["readiness"]}).decode())


@support_results.command("accept")
@click.option("--descriptor", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--response", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--attempt", "attempt_id", required=True)
@click.option("--output", required=True, type=click.Path(path_type=Path), help="New saved-attempt directory.")
def accept(descriptor, response, attempt_id, output):
    """Preserve saved raw evidence and mechanically accept or reject its reply."""
    value = _call(results.accept, descriptor, response, output, attempt_id=attempt_id)
    assessment = value["assessment"]
    click.echo(canonical({"result": str(output / "result.json"),
                         **{k: assessment[k] for k in ("status", "problems", "verdict", "reason")}}).decode())
    if assessment["status"] != "accepted":
        raise click.ClickException("Saved response rejected; original and captured raw evidence preserved.")


@support_results.command("recheck")
@click.option("--result", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck(result):
    """Reconstruct saved acceptance/rejection from bytes, without trusting flags."""
    value = _call(results.recheck, result)
    click.echo(canonical({"checked": True, "target_id": value["target_id"],
                         "attempt_id": value["attempt_id"], "assessment": value["assessment"]}).decode())


@support_results.command("report")
@click.option("--descriptor", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--result", "paths", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def report(descriptor, paths):
    """Report missing/rejected/accepted selected responses and retained blockers."""
    click.echo(canonical(_call(results.report, descriptor, list(paths))).decode())
