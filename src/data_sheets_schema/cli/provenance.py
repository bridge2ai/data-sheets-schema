"""Provenance commands for the D4D CLI."""

import click

from data_sheets_schema.cli.api import ARMS as _ARMS
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


def _parse_phases(specs) -> list[dict]:
    """`--phase` values into phase dicts, in the order given (#562).

    Two forms, because the caller is sometimes a person and sometimes an agent
    writing a shell command: a bare name, or a JSON object for the cases where
    completion, iteration count or artifacts are worth stating.

    A malformed value raises rather than being dropped. A phase log missing one
    phase is worse than no phase log: it reads as a run that skipped a step.
    """
    import json

    out = []
    for raw in specs or ():
        text = str(raw).strip()
        if not text:
            continue
        if text.startswith("{"):
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                raise click.BadParameter(
                    f"--phase {text!r} is not valid JSON: {exc}") from exc
            if not isinstance(obj, dict) or not obj.get("name"):
                raise click.BadParameter(
                    f"--phase {text!r} must be an object with a 'name'")
            out.append(obj)
        else:
            out.append({"name": text, "completed": True})
    return out


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
@click.option('--condition', default=None,
              help='Condition the instruction was rendered under. With --arm '
                   'and --runtime this reconstructs the render spec, so the '
                   'render gate can re-render and compare instead of reporting '
                   '`unverifiable` (#497).')
@click.option('--arm', type=click.Choice(sorted(_ARMS)), default='baseline',
              show_default=True,
              help='Arm the instruction was rendered for. Expanded to the same '
                   'display name `render-prompt` substitutes, so the two '
                   'commands cannot disagree and the render gate cannot report '
                   'a false mismatch (#500).')
@click.option('--runtime', default=None,
              help='Runtime the instruction declared, e.g. "Claude Code".')
@click.option('--provider', default=None, help='Provider the spec declared.')
@click.option('--bundle-for-spec', 'bundle_for_spec', default=None,
              type=click.Path(),
              help='Bundle the instruction was rendered against, when it '
                   'differs from --input-bundle.')
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
@click.option('--phase', 'phase_specs', multiple=True,
              help='a phase this run performed, in order. Either a bare name '
                   '("reconcile") or a JSON object '
                   '(\'{"name":"reconcile","completed":true,"iterations":3}\'). '
                   'Repeat once per phase. Records what the API path records '
                   'as api_usage and the agentic path recorded nowhere (#562).')
def record(project, method, label, input_bundle, prompts, prompt_text,
           condition, arm, runtime, provider, bundle_for_spec,
           reasoning_effort, phase_specs):
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
    from data_sheets_schema import schema_digest
    from data_sheets_schema.provenance import build_record, record_path_for

    # The schema is on disk and the run has just been validated against it, so
    # the digest is observed rather than asserted. `d4d api run` has always
    # recorded it and this path never could, which left the agentic arm off the
    # axis the whole prompt comparison is stratified by — and unable to go
    # STALE when the schema moves (#426, #433, #497).
    digest = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))

    # Reconstruct the render spec, so the gate can re-render and compare rather
    # than reporting `unverifiable`. Only when the caller says which condition
    # was rendered: guessing it would assert a condition the run may not have
    # used, which is the failure the gate exists to catch.
    spec = None
    if condition:
        from data_sheets_schema.api_runner import RunSpec
        bundle = bundle_for_spec or input_bundle
        # `render-prompt` substitutes `ARMS[arm][0]`, the display name, not the
        # token. Storing the token here produced a spec that could never
        # re-render to what was sent, and the gate blamed an unchanged prompt
        # file for it (#500). Expanded through the same table, so the two
        # commands cannot drift apart.
        spec = RunSpec(
            project=project, arm=_ARMS[arm][0], method=method,
            bundle=Path(bundle) if bundle else None, label=label,
            condition=condition, runtime=runtime, provider=provider,
        ).render_spec()

    rec = build_record(project, method, label, mode="live",
                       input_bundle=Path(input_bundle) if input_bundle else None,
                       input_verified=True,
                       prompt_paths=[Path(p) for p in prompts] or None,
                       prompt_request=(Path(prompt_text).read_text(encoding="utf-8")
                                       if prompt_text else None),
                       prompt_request_spec=spec,
                       schema_digest_md5=digest,
                       reasoning_effort=reasoning_effort,
                       phases=_parse_phases(phase_specs))
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
            # `discover` yields the full and _core methods as separate runs
            # over one reasoning log, so counting both doubles every figure.
            if run.is_core or run.deterministic:
                continue
            if method and run.method != method:
                continue
            if label and run.label != label:
                continue
            for proj in run.projects:
                if project and proj != project:
                    continue
                logs.append(CONCAT_DIR / f"{run.method}_core" / run.label /
                            f"{proj}_reasoning.jsonl")

    # Classify the runs that produced no log, rather than printing one message
    # for three different situations (#400).
    import collections as _collections

    import yaml as _yaml

    from data_sheets_schema import reasoning as _r
    from data_sheets_schema.provenance import record_path_for
    why: _collections.Counter = _collections.Counter()
    for candidate in logs:
        proj = candidate.name.replace("_reasoning.jsonl", "")
        run_label = candidate.parent.name
        base = candidate.parent.parent.name
        runtime = None
        rec = record_path_for(proj, base, run_label)
        if rec.exists():
            try:
                data = _yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
                runtime = (data.get("model") or {}).get("agent_runtime")
            except (_yaml.YAMLError, OSError, UnicodeDecodeError):
                runtime = None
        why[_r.log_status(runtime, run_label, candidate.exists())] += 1

    logs = [p for p in logs if p.exists()]
    if not logs:
        click.echo("No reasoning logs found for the selection.")
        if why[_r.NO_LOG_RUNTIME]:
            click.echo(f"   {why[_r.NO_LOG_RUNTIME]} run(s): the Claude Code "
                       "runtime cannot produce one — a subagent has no access "
                       "to its own token accounting. Not a gap to fill: a log "
                       "carrying only the effort level would look comparable "
                       "with the API path's and would not be (#400).")
        if why[_r.NO_LOG_PREDATES]:
            click.echo(f"   {why[_r.NO_LOG_PREDATES]} run(s): predate reasoning "
                       f"capture ({_r.CAPTURE_FROM}). Unrecoverable rather "
                       "than unverified.")
        if why[_r.NO_LOG_MISSING]:
            click.echo(f"   ⚠️  {why[_r.NO_LOG_MISSING]} run(s): an API run "
                       "after capture existed, with no log. That is a defect, "
                       "not a limitation.")
        return
    if why[_r.NO_LOG_RUNTIME] or why[_r.NO_LOG_PREDATES] or why[_r.NO_LOG_MISSING]:
        click.echo(f"{len(logs)} log(s); "
                   f"{why[_r.NO_LOG_RUNTIME]} run(s) whose runtime cannot "
                   f"capture, {why[_r.NO_LOG_PREDATES]} predating capture, "
                   f"{why[_r.NO_LOG_MISSING]} missing.")
        click.echo("   A run with no log has not spent zero reasoning; it has "
                   "no measurement. Do not average the two (#400).\n")

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


@provenance.command("backfill-effort-basis")
@click.option('--execute', is_flag=True,
              help='write the records; without it this reports and changes nothing')
@click.option('--label', default=None, help='restrict to one run label')
def backfill_effort_basis(execute, label):
    """Say where each recorded reasoning effort came from (#470).

    Every honestly-derived effort carries a basis — read from the route,
    observed against CLAUDE_EFFORT, or asserted by the generating agent. A value
    with no basis cannot be placed on that ladder, and anything grouping runs by
    effort reads it as a third condition alongside `high` and absent.

    Two actions, reported separately because they are opposite:

    \b
      record_basis      the value is real and stays; the basis is added
      drop_placeholder  the value names no effort ('default') and is removed

    The second is a deletion. It is never bundled into the first's count, and it
    writes an `unverified` entry naming the gap it leaves.
    """
    from pathlib import Path

    from data_sheets_schema.provenance import (
        CONCAT_DIR, apply_effort_basis, effort_basis_gap,
    )

    paths = sorted(CONCAT_DIR.glob("*_core/*/*_provenance.yaml"))
    if label:
        paths = [p for p in paths if p.parts[-2] == label]

    gaps = [g for g in (effort_basis_gap(Path(p)) for p in paths) if g]
    if not gaps:
        click.echo(f"{len(paths)} record(s) examined; every recorded effort "
                   "already says where it came from.")
        return

    by_action: dict[str, list] = {}
    for g in gaps:
        by_action.setdefault(g["action"], []).append(g)

    verb = "applying" if execute else "would apply"
    click.echo(f"{len(paths)} record(s) examined, {len(gaps)} {verb}:")
    for action, items in sorted(by_action.items()):
        routes = sorted({str(i["route"]) for i in items})
        click.echo(f"   {action:18} {len(items):3}   "
                   f"effort={sorted({str(i['effort']) for i in items})}   "
                   f"route={routes}")

    if not execute:
        click.echo("\nNothing written. Re-run with --execute to apply.")
        return

    counts: dict[str, int] = {}
    for g in gaps:
        applied = apply_effort_basis(g["path"])
        if applied:
            counts[applied["action"]] = counts.get(applied["action"], 0) + 1
    for action, n in sorted(counts.items()):
        click.echo(f"\n{n} record(s): {action}")
    if counts.get("drop_placeholder"):
        click.echo("   A value was removed, not corrected. Each such record now "
                   "names the gap under `unverified`.")


@provenance.command("backfill-prompts")
@click.option('--execute', is_flag=True,
              help='write the records; without it this reports and changes nothing')
@click.option('--label', default=None, help='restrict to one run label')
def backfill_prompts(execute, label):
    """Recover prompts for historical runs, as of each run's own commit (#399).

    A resolver, not a --prompt flag. The honest answer differs per run, so an
    operator asserting a hash by hand is exactly what must not be possible.

    \b
      recovered                    the header names a file; bytes taken at the
                                   run's commit
      no_prompt_header             supplied inline, never saved — stays null
      no_commit_at_or_before_run   the file did not exist yet
      already_recorded             left alone

    The hash is of the bytes at the run's commit, never today's:
    `d4d_generic_arm_prompt.md` was edited the day after the runs that name it,
    so today's hash would assert they used a prompt that did not yet exist.
    """
    from data_sheets_schema.provenance import (
        HISTORICAL_RECOVERED, apply_historical_prompt, resolve_historical_prompt,
    )
    from data_sheets_schema.runs import discover, is_complete

    targets = []
    for run in discover():
        if run.is_core or run.deterministic:
            continue
        if label and run.label != label:
            continue
        for proj in run.projects:
            if not is_complete(run.method, run.label, proj):
                continue
            targets.append((proj, run.method, run.label))

    outcomes = {}
    for proj, method, lab in targets:
        r = resolve_historical_prompt(proj, method, lab)
        outcomes.setdefault(r["status"], []).append((proj, method, lab, r))

    verb = "recovering" if execute else "would recover"
    for status, items in sorted(outcomes.items()):
        click.echo(f"   {status:28} {len(items):4}")
    recoverable = outcomes.get(HISTORICAL_RECOVERED, [])
    if not recoverable:
        click.echo("\nNothing to recover.")
        return
    commits = sorted({i[3]['commit'][:12] for i in recoverable})
    click.echo(f"\n{len(recoverable)} record(s) {verb}, from commit(s) "
               f"{', '.join(commits)}")
    if not execute:
        click.echo("Nothing written. Re-run with --execute to apply.")
        return
    n = sum(1 for proj, method, lab, _ in recoverable
            if apply_historical_prompt(proj, method, lab) is not None)
    click.echo(f"{n} record(s) updated, each naming the commit its hash is of.")


@provenance.command("backfill-checks")
@click.option('--execute', is_flag=True,
              help='write the records; without it this reports and changes nothing')
@click.option('--method', default=None, help='restrict to one method directory')
@click.option('--label', default=None, help='restrict to one run label')
@click.option('--project', default=None, help='restrict to one project')
@click.option('--overwrite', is_flag=True,
              help='replace blocks that are already present')
def backfill_checks(execute, method, label, project, overwrite):
    """Recompute the pair, report and grounding checks for older records (#552).

    #544, #546 and #547 each added a block that `d4d api run` writes from then
    on. Nothing gave those blocks to the records already on disk, so `d4d runs
    check` reported the whole corpus as unknown — including the 15 agentic
    records whose playbook does run the pair checker, and whose clean result is
    the arm comparison that motivated #544.

    Every block written here carries `recorded_by: backfill_checks`. A verdict
    the run attested and one recomputed today are different claims, and where
    the bytes have moved they are different answers.

    Grounding is skipped for a record whose bundle has drifted: checking its
    identifiers against today's bundle would answer a question about a file the
    run never read. Reported as such rather than silently omitted.
    """
    from pathlib import Path

    from data_sheets_schema.backfill_checks import apply, compute, summarise
    from data_sheets_schema.provenance import CONCAT_DIR
    from data_sheets_schema.report_claims import declared_slots

    paths = sorted(CONCAT_DIR.glob("*_core/*/*_provenance.yaml"))
    if method:
        base = method[:-5] if method.endswith("_core") else method
        paths = [p for p in paths if p.parts[-3] == f"{base}_core"]
    if label:
        paths = [p for p in paths if p.parts[-2] == label]
    if project:
        # Exact, not a prefix. `VOICE_PEDIATRIC_provenance.yaml` starts with
        # `VOICE_`, so `--project VOICE --overwrite` rewrote records of a
        # different project (#580). A scoped write that is not scoped is only
        # noticed after it matters.
        paths = [p for p in paths
                 if p.name == f"{project}_provenance.yaml"]
    if not paths:
        click.echo("no records matched")
        return

    # Built once. Each call loads two SchemaViews, which over 122 records is
    # the difference between seconds and minutes.
    declared = declared_slots()
    written = skipped = 0
    for p in paths:
        try:
            blocks = compute(p, declared)
            # Inside the same guard as compute: a write that raises halfway
            # through 192 records leaves a corpus in two states, and the reason
            # it raised is exactly the kind a reader needs to see per-record.
            changed = apply(p, blocks, overwrite=overwrite) if execute else True
        except Exception as exc:                               # noqa: BLE001
            click.echo(f"   ✗ {p.parts[-2]}/{p.name}: {exc}")
            continue
        if execute and not changed:
            skipped += 1
            continue
        written += 1
        click.echo(f"   {'✔' if execute else '·'} {p.parts[-2][:38]:38} "
                   f"{p.name[:-16]:16} {summarise(blocks)}")
    verb = "written" if execute else "would be written"
    click.echo(f"\n{written} record(s) {verb}"
               + (f", {skipped} already carried the blocks" if skipped else ""))
    if not execute:
        click.echo("Nothing was changed. Re-run with --execute to write.")


@provenance.command("backfill-context")
@click.option('--execute', is_flag=True,
              help='write the records; without it this reports and changes nothing')
@click.option('--label', default=None, help='restrict to one run label')
def backfill_context(execute, label):
    """Record the context each API run actually used (#568).

    Adds no claim the record was not already making: `peak_request_tokens` is
    computed from the `api_usage` the run wrote itself, so this is arithmetic
    over existing evidence rather than a new assertion — the same ground on
    which `backfill-effort` is defensible and a temperature backfill would not
    be.

    The *limit* is not backfilled. It was not knowable at the time and is not
    knowable now; recording a guess would make headroom computable and wrong.

    Agentic records have no `api_usage` and are skipped, not filled with zero.
    """
    import yaml as _yaml

    from data_sheets_schema.api_runner import context_facts
    from data_sheets_schema.backfill_checks import _split_header
    from data_sheets_schema.provenance import CONCAT_DIR

    paths = sorted(CONCAT_DIR.glob("*_core/*/*_provenance.yaml"))
    if label:
        paths = [p for p in paths if p.parts[-2] == label]
    rows, skipped = [], 0
    for p in paths:
        header, body = _split_header(p.read_text(encoding="utf-8"))
        rec = _yaml.safe_load(body)
        if not isinstance(rec, dict):
            continue
        usage = rec.get("api_usage")
        if not isinstance(usage, list) or not usage:
            skipped += 1
            continue
        model = rec.get("model") or {}
        facts = context_facts(str(model.get("model") or ""), usage)
        # Marked, like every other backfill (#552): a value the run wrote and
        # one computed afterwards are different claims even when the arithmetic
        # is the same, and only the record can say which this is.
        facts["recorded_by"] = "backfill_context"
        rows.append((p, facts))
        if execute:
            model["context"] = facts
            rec["model"] = model
            p.write_text(header + _yaml.safe_dump(rec, sort_keys=False,
                                                  allow_unicode=True),
                         encoding="utf-8")
    for p, f in sorted(rows, key=lambda r: -(r[1]["peak_request_tokens"] or 0))[:12]:
        click.echo(f"   {'✔' if execute else '·'} {p.parts[-2][:38]:38} "
                   f"{p.name[:-16]:16} peak {f['peak_request_tokens']:>8,} "
                   f"({f['peak_phase']})")
    click.echo(f"\n{len(rows)} API record(s) {'written' if execute else 'would be written'}"
               f"; {skipped} skipped as having no api_usage (agentic runs)")
    if not execute:
        click.echo("Nothing was changed. Re-run with --execute to write.")
