"""Offline registration, result checks and paired support/fitness analysis."""
from pathlib import Path

import click

from data_sheets_schema import cross_family_judge_panel as panels
from data_sheets_schema.cli.support_results import _call
from data_sheets_schema.support_plan import canonical


@click.group("cross-family-judges")
def cross_family_judges():
    """Capture and analyze saved panel evidence; never dispatch rating requests."""


@cross_family_judges.command("prepare")
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


@cross_family_judges.command("recheck")
@click.option("--panel", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck(panel):
    """Reconstruct the captured declaration without original files or ratings."""
    click.echo(canonical(_call(panels.recheck_panel, panel)).decode())


@cross_family_judges.command("accept-results")
@click.option("--panel", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--submissions", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--root", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Explicit root for the submitted saved rating files.")
@click.option("--output", required=True, type=click.Path(path_type=Path),
              help="New captured-results directory; existing artifacts are preserved.")
def accept_results(panel, submissions, root, output):
    """Check saved ratings against fixed slots; never dispatch or authorize."""
    from data_sheets_schema.cross_family_judge_panel import accept_panel_results
    value = _call(accept_panel_results, panel, submissions, output, root=root)
    click.echo(canonical(value).decode())


@cross_family_judges.command("recheck-results")
@click.option("--results", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck_results(results):
    """Recompute all accepted/rejected/missing ratings from captured bytes."""
    from data_sheets_schema.cross_family_judge_panel import recheck_panel_results
    click.echo(canonical(_call(recheck_panel_results, results)).decode())


@cross_family_judges.command("prepare-analysis")
@click.option("--panel", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--declaration", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
def prepare_analysis(panel, declaration, output):
    """Capture explicit statistical policies; null choices remain pending."""
    from data_sheets_schema.cross_family_judge_analysis import prepare_analysis_spec
    click.echo(canonical(_call(prepare_analysis_spec, panel, declaration, output)).decode())


@cross_family_judges.command("recheck-analysis-spec")
@click.option("--specification", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck_analysis_spec(specification):
    """Reconstruct policy and panel from captured bytes, without results."""
    from data_sheets_schema.cross_family_judge_analysis import recheck_analysis_spec as recheck_spec
    click.echo(canonical(_call(recheck_spec, specification)).decode())


@cross_family_judges.command("analyze")
@click.option("--specification", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--results", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(path_type=Path))
def analyze(specification, results, output):
    """Recheck saved acceptance and compute descriptive paired statistics."""
    from data_sheets_schema.cross_family_judge_analysis import analyze_panel_results
    click.echo(canonical(_call(analyze_panel_results, specification, results, output)).decode())


@cross_family_judges.command("recheck-analysis")
@click.option("--analysis", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def recheck_analysis(analysis):
    """Rebuild acceptance, metric joins and all bootstrap draws portably."""
    from data_sheets_schema.cross_family_judge_analysis import recheck_panel_analysis
    click.echo(canonical(_call(recheck_panel_analysis, analysis)).decode())
