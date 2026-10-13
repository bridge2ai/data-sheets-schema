"""Explicit strict top-level fitness results; no provider execution."""
from pathlib import Path

import click

from data_sheets_schema import top_level_fitness_results as results
from data_sheets_schema.cli.support_results import _call
from data_sheets_schema.support_plan import canonical


@click.group("fitness-results")
def fitness_results():
    """Reconstruct SAVED fitness evidence; mechanical acceptance is not calibration."""


@fitness_results.command("prepare")
@click.option("--plan", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.option("--protocol", required=True, type=click.Choice([results.FORMAT]))
@click.option("--select", "selections", required=True, multiple=True, nargs=2, metavar="TARGET_ID ATTEMPT_ID")
def prepare(plan, output, protocol, selections):
    value = _call(results.prepare, plan, output, protocol=protocol,
                  selections=[{"target_id": t, "attempt_id": a} for t, a in selections])
    click.echo(canonical({"descriptor": str(output / "descriptor.json"),
                          "selected_targets": len(value["selections"]), "readiness": value["readiness"]}).decode())


@fitness_results.command("accept")
@click.option("--descriptor", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--response", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--attempt", "attempt_id", required=True)
@click.option("--output", required=True, type=click.Path(path_type=Path))
def accept(descriptor, response, attempt_id, output):
    value = _call(results.accept, descriptor, response, output, attempt_id=attempt_id)
    click.echo(canonical({"result": str(output / "result.json"), "assessment": value["assessment"],
                         "scientific_scoring_eligible": False}).decode())
    if value["assessment"]["status"] != "accepted":
        raise click.ClickException("Saved fitness response rejected; original raw evidence preserved.")


@fitness_results.command("recheck")
@click.option("--result", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck(result):
    click.echo(canonical(_call(results.recheck, result)).decode())


@fitness_results.command("index")
@click.option("--descriptor", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--result", "paths", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--support-result", "support_paths", multiple=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--execution", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Capture and independently recheck the fixed execution ledger; never dispatch or retry.")
@click.option("--support-execution", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Opt into index v2 with every registered support selection and its captured dispatch outcome.")
@click.option("--rubric-associations", is_flag=True,
              help="Opt into index v3: compare captured rubric identity declarations, never accept ratings.")
@click.option("--rubric-plan", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Original captured plan supplying rubric blobs; must match the descriptor's exact plan pin.")
@click.option("--output", required=True, type=click.Path(path_type=Path))
def index(descriptor, paths, support_paths, execution, support_execution, rubric_associations, rubric_plan, output):
    click.echo(canonical(_call(results.build_index, descriptor, list(paths), output,
                              execution=execution, support_results=list(support_paths),
                              support_execution=support_execution, rubric_associations=rubric_associations,
                              rubric_plan=rubric_plan)).decode())


@fitness_results.command("recheck-index")
@click.option("--index", "path", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck_index(path):
    click.echo(canonical(_call(results.recheck_index, path)).decode())
