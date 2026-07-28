"""Provenance commands for the D4D CLI."""

import click
from pathlib import Path


@click.group()
def provenance():
    """Generation provenance records — live capture and retroactive backfill."""
    pass


@provenance.command()
@click.option('--project', required=True)
@click.option('--method', required=True, help='e.g. claudecode_agent')
@click.option('--label', required=True, help='run label, e.g. 2026-07-27_claude-opus-5_rep1')
@click.option('--input-bundle', type=click.Path(), default=None)
def record(project, method, label, input_bundle):
    """Write a LIVE provenance record for a run just produced.

    Every field is observed at run time — hardware, software versions, input
    hashes. Use this from inside a generation process.
    """
    from data_sheets_schema.provenance import build_record, record_path_for

    rec = build_record(project, method, label, mode="live",
                       input_bundle=Path(input_bundle) if input_bundle else None,
                       input_verified=True)
    out = rec.write(record_path_for(project, method, label))
    click.echo(f"✓ {out}")


@provenance.command()
@click.option('--verified-label', 'verified', multiple=True,
              help='Run labels whose input bytes are known unchanged; may repeat.')
@click.option('--dry-run', is_flag=True)
def backfill(verified, dry_run):
    """Reconstruct provenance records for runs already on disk.

    Fields that cannot be honestly recovered are listed under `unrecoverable`
    rather than filled from present-day observation. Pass --verified-label for
    runs whose inputs are known unchanged, so their input hashes can be
    recorded.
    """
    from data_sheets_schema.provenance import build_record, record_path_for
    from data_sheets_schema.runs import discover

    written = skipped = 0
    for run in discover():
        if run.is_core or run.deterministic:
            continue
        for project in run.projects:
            is_verified = run.label in verified
            rec = build_record(project, run.method, run.label,
                               mode="reconstructed", input_verified=is_verified)
            target = record_path_for(project, run.method, run.label)
            n_unrec = len(rec.data.get("unrecoverable") or [])
            if dry_run:
                click.echo(f"  would write {target}  ({n_unrec} unrecoverable)")
                skipped += 1
            else:
                rec.write(target)
                click.echo(f"  ✓ {target}  ({n_unrec} unrecoverable)")
                written += 1
    click.echo(f"\n{'would write' if dry_run else 'wrote'} "
               f"{skipped or written} record(s)")
