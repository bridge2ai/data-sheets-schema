"""Run-tracking commands for the D4D CLI."""

import click
from pathlib import Path


@click.group()
def runs():
    """Track and compare parallel D4D generation runs."""
    pass


@runs.command('list')
@click.option('--arm', default=None, help='Filter by arm.')
@click.option('--full-only', is_flag=True, help='Hide the _core companions.')
def list_runs(arm, full_only):
    """List every generation run found on disk."""
    from data_sheets_schema.runs import discover, needs_replicate_label

    found = discover()
    if arm:
        found = [r for r in found if r.arm == arm]
    if full_only:
        found = [r for r in found if not r.is_core]
    if not found:
        click.echo("No runs found."); return

    click.echo(f"{'arm':<23}{'method':<36}{'label':<34}{'index':>6}  projects")
    for r in found:
        if r.deterministic:
            rep = 'det'
        elif r.legacy_revision is not None:
            rep = f'rev{r.legacy_revision}'
        else:
            rep = f'rep{r.replicate}' if r.replicate else '—'
        click.echo(f"{r.arm:<23}{r.method:<36}{r.label:<34}{rep:>6}  "
                   f"{','.join(r.projects)}")

    legacy = [r for r in found if r.legacy_revision is not None]
    if legacy:
        click.echo(f"\n  rev{{N}} = legacy `-r{{N}}` label meaning a REVISION "
                   "(changed pipeline), not a replicate.")
        click.echo("  Those runs are not comparable to each other as samples.")


@runs.command()
@click.option('--method', required=True, help='e.g. claudecode_agent')
@click.option('--project', required=True)
@click.option('--label', 'labels', multiple=True,
              help='Run labels to compare; default all for that method.')
def compare(method, project, labels):
    """Compare slot coverage across replicates of one method."""
    from data_sheets_schema.runs import compare as do_compare, discover

    if not labels:
        labels = [r.label for r in discover() if r.method == method]
    result = do_compare(method, project, list(labels))
    if 'error' in result:
        click.echo(f"❌ {result['error']}", err=True)
        raise SystemExit(1)

    if not result['same_procedure']:
        click.echo("⚠️  THESE ARE NOT REPLICATES — the runs used different "
                   "procedures.\n   Their differences measure the pipeline "
                   "change, not sampling variance.\n")
        for lab, fp in result['procedures'].items():
            desc = fp.get('Generation Method') or fp.get('Agent runtime') or '?'
            click.echo(f"     {lab:<36} {desc}")
        click.echo("")

    if result.get('excluded_incomplete'):
        click.echo(f"⚠️  excluded as still running / incomplete: "
                   f"{', '.join(result['excluded_incomplete'])}\n")

    click.echo(f"{project} — {method}")
    for lab, n in result['counts'].items():
        click.echo(f"  {lab:<36} {n:>3} slots")
    click.echo(f"\n  stable across all runs: {len(result['stable'])}")
    click.echo(f"  varying:                {len(result['varying'])}")
    click.echo(f"  agreement:              {result['agreement']:.1%}")
    if result['varying']:
        click.echo(f"\n  slots not present in every run:\n    {', '.join(result['varying'])}")
