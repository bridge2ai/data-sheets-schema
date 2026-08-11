"""Provenance commands for the D4D CLI."""

import click
from pathlib import Path

#: The effort ladder, duplicated here so the CLI keeps its lazy imports and
#: does not pull in `provenance` just to build a decorator. It is the same
#: vocabulary `_effort_from_route` matches routes against, and
#: `test_effort_ladder_matches_the_recorder` fails if the two drift apart.
EFFORT_CHOICES = ("minimal", "low", "medium", "high")


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
@click.option('--prompt-text', 'prompt_text',
              type=click.Path(exists=True, dir_okay=False),
              help='The instruction as actually sent, e.g. from '
                   '`d4d api render-prompt --out`. Hashed as prompts.request. '
                   'The file is what an instruction was built from; this is '
                   'what it became.')
@click.option('--reasoning-effort', 'reasoning_effort', default=None,
              type=click.Choice(EFFORT_CHOICES),
              help='Reasoning effort this run was launched at, where the '
                   'runtime does not expose it. Recorded as asserted, not '
                   'observed. Omit it rather than guessing: an absent effort '
                   'is reported as a gap, and "default" is not a value — the '
                   'choice list refuses it rather than trusting the reader '
                   '(#450), because `PLACEHOLDER_VALUES` in runs.py would '
                   'discard it downstream and the record and the analysis '
                   'would then disagree.')
def record(project, method, label, input_bundle, prompts, prompt_text,
           reasoning_effort):
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
                       prompt_paths=[Path(p) for p in prompts] or None,
                       prompt_request=(Path(prompt_text).read_text(encoding="utf-8")
                                       if prompt_text else None),
                       reasoning_effort=reasoning_effort)
    out = rec.write(record_path_for(project, method, label))
    click.echo(f"✓ {out}")

    # Say it here, but do not refuse. Recording an uncanonical prompt is the
    # honest act — it is what puts the evidence in the record for `d4d runs
    # check` to fail on (#432). Refusing would reward not recording at all,
    # which is the state this whole thread has been climbing out of.
    from data_sheets_schema import prompt_registry as _pr
    for p in prompts:
        st, why = _pr.disk_status(p)
        if st != _pr.CANONICAL:
            click.echo(f"  ⚠️  prompt {st}: {why}")
            click.echo("      This is recorded, and `d4d runs check` reports "
                       "it. If the text is intentional, declare it with "
                       "`d4d api prompts pin`.")
    # Say what happened to any prior verdict. Re-recording used to delete it
    # silently and the run then failed `--strict` with "nothing to verify",
    # while this command printed a tick and exited 0 (#396).
    if rec.validation_carried is True:
        click.echo("  validation: carried forward — the artifacts it names "
                   "still hash to what it recorded")
    elif rec.validation_carried is False:
        click.echo("  ⚠️  validation: dropped — the artifacts changed since it "
                   "was recorded, so the verdict is about bytes that no longer "
                   "exist.\n      Re-run `d4d runs validate --label "
                   f"{label} --project {project}` before `d4d runs check`.")


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


@provenance.command("backfill-effort")
@click.option('--execute', is_flag=True,
              help='write the records; without it this reports and changes nothing')
@click.option('--method', default=None, help='restrict to one method directory')
@click.option('--label', default=None, help='restrict to one run label')
def backfill_effort(execute, method, label):
    """Record the reasoning effort a run's own model route already names (#448).

    `_effort_from_route` runs only when a record is built, so records written
    before it existed name `google/claude-opus-5-high` and carry no
    `reasoning_effort`. The information was in the route all along; nothing read
    it.

    This adds no claim the record was not already making — the route is in the
    record, and the effort is read off it — so the value is recorded as
    **observed** and does not enter `unverified`. That is what makes a bulk pass
    defensible here and not, say, for temperature.

    Reports by default and writes only under --execute, because rewriting
    records should be a deliberate reviewable commit rather than a side effect.
    """
    from pathlib import Path

    from data_sheets_schema.provenance import (
        CONCAT_DIR, apply_observed_effort, observed_effort_gap,
    )

    paths = sorted(CONCAT_DIR.glob("*_core/*/*_provenance.yaml"))
    if method:
        base = method[:-5] if method.endswith("_core") else method
        paths = [p for p in paths if p.parts[-3] == f"{base}_core"]
    if label:
        paths = [p for p in paths if p.parts[-2] == label]

    gaps = [g for g in (observed_effort_gap(Path(p)) for p in paths) if g]
    if not gaps:
        click.echo(f"{len(paths)} record(s) examined; none has an effort its "
                   "route names but it does not carry.")
        return

    by_route: dict[str, int] = {}
    for g in gaps:
        by_route[f"{g['route']} -> {g['effort']}"] = (
            by_route.get(f"{g['route']} -> {g['effort']}", 0) + 1)

    verb = "updating" if execute else "would update"
    click.echo(f"{len(paths)} record(s) examined, {len(gaps)} {verb}:")
    for route, n in sorted(by_route.items()):
        click.echo(f"   {route:44} {n}")

    if not execute:
        click.echo("\nNothing written. Re-run with --execute to apply.")
        return

    written = 0
    for g in gaps:
        if apply_observed_effort(g["path"]) is not None:
            written += 1
    click.echo(f"\n{written} record(s) updated. The value is observed — read "
               "from the route the record already carried — so it is not "
               "listed under `unverified`.")
