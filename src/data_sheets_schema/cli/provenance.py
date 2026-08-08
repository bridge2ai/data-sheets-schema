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
@click.option('--prompt', 'prompts', multiple=True,
              type=click.Path(exists=True, dir_okay=False),
              help='Prompt file this run was launched with; may repeat. '
                   'Hashed into the record.')
def record(project, method, label, input_bundle, prompts):
    """Write a LIVE provenance record for a run just produced.

    Every field is observed at run time — hardware, software versions, input
    hashes. Use this from inside a generation process.

    Pass --prompt for every prompt file the run consumed. Without it the
    record's `prompts` block is null, which is what the agentic path produced
    for its whole history while `d4d api run` hashed its prompts via
    `prompt_paths`: the same procedure was reproducible from an API record and
    not from a Claude Code one. A prompt is a generation input like the bundle,
    and the prompt-condition study is precisely a comparison between prompts,
    so a record that cannot identify its own prompt cannot be placed in it.
    """
    from data_sheets_schema.provenance import build_record, record_path_for

    rec = build_record(project, method, label, mode="live",
                       input_bundle=Path(input_bundle) if input_bundle else None,
                       input_verified=True,
                       prompt_paths=[Path(p) for p in prompts] or None)
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


@provenance.command('reasoning')
@click.option('--method', default=None, help='limit to one method')
@click.option('--project', default=None)
@click.option('--label', default=None, help='limit to one run label')
@click.option('--path', type=click.Path(), default=None,
              help='read one reasoning log directly instead of discovering runs')
def reasoning_cmd(method, project, label, path):
    """Summarise captured model reasoning for generation runs.

    Reports presence and availability separately on purpose. Through the CBORG
    proxy every thinking block arrives signed but empty, so a summary that
    conflated the two would read as "no reasoning happened" when what actually
    happened is that the endpoint withheld it. The token estimate is the only
    quantitative trace that survives in that case.
    """
    from pathlib import Path as _Path

    from data_sheets_schema import reasoning as _reasoning
    from data_sheets_schema.api_runner import CONCAT_DIR
    from data_sheets_schema.runs import discover

    logs: list[_Path] = []
    if path:
        logs = [_Path(path)]
    else:
        for run in discover():
            if method and run.method != method:
                continue
            if label and run.label != label:
                continue
            for proj in run.projects:
                if project and proj != project:
                    continue
                logs.append(CONCAT_DIR / f"{run.method}_core" / run.label /
                            f"{proj}_reasoning.jsonl")

    logs = [p for p in logs if p.exists()]
    if not logs:
        click.echo("No reasoning logs found. They are written by `d4d api run`; "
                   "runs generated before reasoning capture have none, and that "
                   "is unrecoverable rather than unverified.")
        return

    total: list[dict] = []
    for p in sorted(logs):
        entries = _reasoning.read(p)
        total.extend(entries)
        s = _reasoning.summarise(entries)
        click.echo(f"\n{p}")
        click.echo(f"  entries {s['entries']}, with a reasoning block "
                   f"{s['with_reasoning_block']}, with reasoning text "
                   f"{s['with_reasoning_text']}")
        if s.get('reasoning_tokens_estimate_total'):
            click.echo(f"  reasoning tokens (estimated) "
                       f"{s['reasoning_tokens_estimate_total']:,} total, "
                       f"{s['reasoning_tokens_estimate_max']:,} max")
        if s['truncated']:
            click.echo(f"  ⚠️  {s['truncated']} response(s) stopped at "
                       f"max_tokens")

    if len(logs) > 1:
        s = _reasoning.summarise(total)
        click.echo(f"\n{len(logs)} log(s), {s['entries']} entries, "
                   f"{s['with_reasoning_text']} with reasoning text")
    if total and not any(e.get('reasoning_available') for e in total):
        click.echo("\nNo reasoning text was available in any entry. The blocks "
                   "are signed but empty — the endpoint strips the plaintext. "
                   "Runs made directly against the Anthropic API capture it.")
