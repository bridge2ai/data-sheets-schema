"""Healthsheet command group for D4D CLI."""

import click
from pathlib import Path


@click.group()
def healthsheet():
    """Healthsheet commands (AI-READI only — the sole GC that publishes one)."""
    pass


@healthsheet.command()
@click.option('--record', type=click.Path(exists=True), default=None,
              help='FAIRhub API record JSON; defaults to the manifest capture.')
@click.option('--output-dir', type=click.Path(), default='data/preprocessed/concatenated',
              show_default=True)
def bundle(record, output_dir):
    """Build the healthsheet-only generation input.

    Writes AI_READI_healthsheet_only.txt — the Healthsheet and nothing else.
    This is an extra arm, not the AI-READI baseline: the baseline corpus keeps
    the healthsheet alongside every other cited source.
    """
    from data_sheets_schema.healthsheet import FAIRHUB_RECORD, build_bundle

    src = Path(record) if record else FAIRHUB_RECORD
    try:
        target, stats = build_bundle(src, Path(output_dir))
    except (FileNotFoundError, KeyError) as e:
        click.echo(f"❌ {e}", err=True)
        raise SystemExit(1)

    click.echo(f"→ {target} ({target.stat().st_size:,} bytes)")
    click.echo(f"  {stats.sections} sections, {stats.questions} questions "
               f"({stats.answered} answered, "
               f"{stats.questions - stats.answered} unanswered)")
    if stats.unanswered:
        click.echo(f"  unanswered: {', '.join(stats.unanswered)}")
