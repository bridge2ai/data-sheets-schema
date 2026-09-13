"""Healthsheet command group for D4D CLI."""

import click
from pathlib import Path


@click.group()
def healthsheet():
    """Healthsheet commands: the healthsheet-only generation input, from an
    upstream record that carries one."""
    pass


@healthsheet.command()
@click.option('--record', type=click.Path(exists=True), default=None,
              help='the upstream record JSON carrying a Healthsheet; default: the '
                   "active profile's (the study's capture under bridge2ai; none under neutral)")
@click.option('--project', default=None,
              help="the dataset the bundle identifies itself as; default: the active profile's (none under neutral)")
@click.option('--name', default=None,
              help="the bundle's file name; default: the active profile's, else <record stem>_healthsheet_only.txt")
@click.option('--output-dir', type=click.Path(), default='data/preprocessed/concatenated',
              show_default=True)
def bundle(record, output_dir, project, name):
    """Build the healthsheet-only generation input.

    Writes `{PROJECT}_healthsheet_only.txt` — the Healthsheet and nothing
    else. This is an extra arm, not the dataset's baseline: the baseline
    corpus keeps the healthsheet alongside every other cited source.
    """
    from data_sheets_schema.healthsheet import build_bundle, default_record

    src = Path(record) if record else default_record()
    if src is None:
        click.echo("❌ no --record given and the active profile names no healthsheet record", err=True)
        raise SystemExit(1)
    try:
        target, stats = build_bundle(src, Path(output_dir), name=name, project=project)
    except (FileNotFoundError, KeyError, ValueError) as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1)

    click.echo(f"→ {target} ({target.stat().st_size:,} bytes)")
    click.echo(f"  {stats.sections} sections, {stats.questions} questions "
               f"({stats.answered} answered, "
               f"{stats.questions - stats.answered} unanswered)")
    if stats.unanswered:
        click.echo(f"  unanswered: {', '.join(stats.unanswered)}")
