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


#: The names a phase log may carry: the API runtime's phases (the six
#: generation phases, the repair phases, the post-repair report rewrite) and
#: the agentic playbook's own names — which are NOT a subset by name. The
#: first version of this check assumed they were and refused every name the
#: playbook itself instructs (`d4d-full-core.md` says --phase generate_full /
#: generate_core / source_audit / reconcile), which would have broken the
#: next agentic run's completion criterion — the #672 review read the
#: template this comment's author had not.
AGENTIC_PHASES = frozenset({"generate_full", "generate_core", "derive_core",
                            "source_audit", "reconcile", "repair"})
# `derive_core`: the core produced by `d4d derive core` from the audited full
# (#694) — a deterministic step, recorded as a phase so the log says the core
# was derived and not generated. `generate_core` stays for pre-#694 runs.
# `repair` is the agentic analogue of the API pipeline's repair_full +
# repair_core rounds: one phase covering both records, whose fix-validate
# loop may iterate (`iterations` counts those loops). `report` and
# `report_after_repair` need no entry here — _known_phases() already carries
# them (`report` from api_runner.PHASES, `report_after_repair` from the
# repair-name set below), so both runtimes may record them.


# What the orchestrator can honestly observe about a phase-subagent it ran:
# the runner reports total tokens, tool-use count and wall duration when the
# agent completes. Aggregate only — no input/output split, not billing-grade —
# so the shape is deliberately different from api_usage and never merges with
# it. The subagent itself must not estimate these (#400); only the launcher
# that observed them may record them.
_OBSERVED_FIELDS = frozenset({"total_tokens", "tool_uses", "duration_ms",
                              "bundle_lines_read", "bundle_lines_total",
                              "receipt_chunks_total", "receipt_chunks_unopened"})
# receipt_chunks_total / receipt_chunks_unopened (#709): of the chunks the
# coverage receipt marks reviewed, how many the transcript shows no file-tool
# window over. The receipt is the agent's claim and the windows are the
# observation; a reviewed-but-unopened chunk is the laziness the receipt
# exists to make deliberate rather than easy.
# bundle_lines_read / bundle_lines_total: how much of the declared bundle the
# run actually opened through its file-reading tool, as the union of its read
# windows over the bundle's line count (#700). The API path has the whole
# bundle in context on every call; the agentic path reads it piecewise, and
# an unread window is indistinguishable in the record from "the bundle does
# not support it" unless this is recorded. scripts/agentic_observed.py
# computes both from the runner's transcript.

# api_usage fields no agentic phase may carry: a phase log that looks
# comparable to the API path's accounting and is not would be worse than the
# gap it fills (#400).
_API_ONLY_PHASE_FIELDS = frozenset({"seconds", "input_tokens",
                                    "output_tokens", "stop_reason"})

# Every key a --phase object may carry. A whitelist, not a blacklist: any
# other key is refused, because a key the parser drops makes the record
# differ silently from what the caller typed ("a malformed value raises
# rather than being dropped", above), and a key it passes through enters the
# record unvalidated (#681 review).
_PHASE_KEYS = frozenset({"name", "completed", "iterations", "artifacts",
                         "notes", "ordinal", "observed"})


def _known_phases() -> frozenset[str]:
    from data_sheets_schema.api_runner import PHASES
    return frozenset(PHASES) | {"repair_full", "repair_core",
                                "report_after_repair", "full_readdress",
                                "report_regate"} | AGENTIC_PHASES


def _inline_checks(path: Path) -> None:
    """Write the four deterministic check blocks into a just-written record.

    The API runner computes pair consistency, report claims, grounding and
    form in-process; this recorder did not, so every agentic record depended
    on a separate `backfill-checks --execute` the playbook never named (#687)
    and a launcher that forgot it shipped records without the metrics the
    canary gate reads. Computed here from the same functions, marked as
    recorded by this command rather than by a retroactive backfill. A failure
    to compute is reported on stdout with exit 0 and does not un-write the
    record: a record without its check blocks is recoverable by backfill; a
    run without a record is not. Downstream, the canary gate reads
    report_claims and refuses a record that lacks it, so the gap cannot pass
    silently into a fan-out. The one exception is an artifact that does not
    parse, which is re-raised.
    """
    import yaml as _yaml

    from data_sheets_schema import backfill_checks as bc
    try:
        blocks = bc.compute(path)
    except _yaml.YAMLError:
        # An artifact that does not parse is a run failure, not a checks
        # failure; hiding it behind a ⚠️ would let a launcher ship it.
        raise
    except Exception as exc:  # noqa: BLE001 — reported on stdout, exit 0
        click.echo(f"  ⚠️  deterministic checks not computed ({exc}); the "
                   "record stands — run `d4d provenance backfill-checks "
                   "--execute` once the cause is fixed")
        return
    for block in blocks.values():
        if isinstance(block, dict):
            block["recorded_by"] = "d4d provenance record"
    bc.apply(path, blocks, overwrite=True)
    click.echo("  " + bc.summarise(blocks))


def _require_repo_root_cwd(command: str) -> None:
    """Refuse to record from anywhere but the repository root (#672 review).

    #659's resolution fix turned an outside-the-root recorder from a loud
    FileNotFoundError into a quietly degraded record: playbook hashes
    exists:false, a null manifest md5 with no unrecoverable entry, repo facts
    from whatever git repo the cwd happens to be in, and the record itself
    written under <cwd>/data/ where no check ever reads it — with a ✓ printed.
    A recorder that cannot see its inputs must say so, not improvise. The
    cwd-relative constants this codebase runs on make "the repo root" the
    only cwd a record can honestly be written from.
    """
    if not (Path("data/d4d_concatenated").is_dir()
            and Path("src/data_sheets_schema").is_dir()):
        raise click.ClickException(
            f"{command} must run from the data-sheets-schema repository root: "
            "the playbook hashes, manifest, schemas and output paths all "
            "resolve relative to it, and a record written from elsewhere "
            "would attest the wrong inputs or none. cd to the repo root and "
            "re-run.")


def _parse_phases(specs) -> list[dict]:
    """`--phase` values into phase dicts, in the order given (#562).

    Two forms, because the caller is sometimes a person and sometimes an agent
    writing a shell command: a bare name, or a JSON object for the cases where
    completion, iteration count or artifacts are worth stating.

    A malformed value raises rather than being dropped. A phase log missing one
    phase is worse than no phase log: it reads as a run that skipped a step.

    The name must be a phase the pipeline has (#642). This log is the agentic
    arm's *only* phase attestation — that runtime cannot observe its own calls
    (#400) — so before this check a typo (`recncile_full`) entered the record
    as an accomplished phase and nothing downstream could tell it from a real
    one. The API arm's phases are attested by the calls themselves, which is
    why the same laxity there would merely be untidy; here it was the whole
    record. Refused rather than marked: the caller is present and can fix a
    typo now, whereas a marked-dubious phase in the record helps nobody later.
    """
    import json

    known = _known_phases()
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
            if obj["name"] not in known:
                raise click.BadParameter(
                    f"--phase name {obj['name']!r} is not a phase this "
                    f"pipeline has. Known: {', '.join(sorted(known))}")
            forbidden = _API_ONLY_PHASE_FIELDS & obj.keys()
            if forbidden:
                raise click.BadParameter(
                    f"--phase {obj['name']!r} carries "
                    f"{sorted(forbidden)}: these are api_usage fields this "
                    "runtime cannot measure (#400). Aggregate totals the "
                    "orchestrator observed go under 'observed', e.g. "
                    '{"name": "generate_full", '
                    '"observed": {"total_tokens": 48211}}, '
                    "which is deliberately not shaped like api_usage.")
            misplaced = _OBSERVED_FIELDS & obj.keys()
            if misplaced:
                raise click.BadParameter(
                    f"--phase {obj['name']!r} carries {sorted(misplaced)} at "
                    "the phase's top level; observed totals go under "
                    "'observed': {…}. Refused rather than moved, so the "
                    "record never differs from what was typed.")
            unknown = obj.keys() - _PHASE_KEYS
            if unknown:
                raise click.BadParameter(
                    f"--phase {obj['name']!r} carries unknown keys "
                    f"{sorted(unknown)}; allowed: {sorted(_PHASE_KEYS)}. "
                    "A dropped key would make the record differ silently "
                    "from what was typed, and an invented one would enter "
                    "the record unvalidated.")
            observed = obj.get("observed")
            if observed is not None:
                if (not isinstance(observed, dict) or not observed
                        or not set(observed) <= _OBSERVED_FIELDS):
                    raise click.BadParameter(
                        f"--phase {obj['name']!r} 'observed' must be a "
                        f"non-empty object with keys from "
                        f"{sorted(_OBSERVED_FIELDS)}")
                bad = {k: v for k, v in observed.items()
                       if not isinstance(v, int) or isinstance(v, bool)
                       or v < 0}
                if bad:
                    raise click.BadParameter(
                        f"--phase {obj['name']!r} 'observed' values must be "
                        f"non-negative integers as measured, got {bad}. "
                        "Coercion is refused: a truncated float or a "
                        "true-as-1 is a measurement the orchestrator did "
                        "not make, and no measurement is negative.")
            out.append(obj)
        else:
            if text not in known:
                raise click.BadParameter(
                    f"--phase {text!r} is not a phase this pipeline has. "
                    f"Known: {', '.join(sorted(known))}")
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
@click.option('--phase-skipped', 'phases_skipped', multiple=True,
              help='a phase a resumed run did not repeat because its artifact '
                   'already existed and validated — the same field the API '
                   'path\'s resumed runs carry. Repeat once per skipped '
                   'phase; names are validated like --phase.')
@click.option('--receipt-expected', 'receipt_expected', is_flag=True, default=False,
              help='this run\'s procedure wrote a coverage receipt (#708); the '
                   'canary gate then treats a missing or failing one as a stop '
                   'rather than as not-applicable')
def record(project, method, label, input_bundle, prompts, prompt_text,
           condition, arm, runtime, provider, bundle_for_spec,
           reasoning_effort, phase_specs, phases_skipped, receipt_expected):
    """Write a LIVE provenance record for a run just produced.

    Refuses to run from anywhere but the repository root — see
    _require_repo_root_cwd.

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
    _require_repo_root_cwd("d4d provenance record")
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
                       phases=_parse_phases(phase_specs),
                       receipt_expected=receipt_expected)
    if phases_skipped:
        known = _known_phases()
        bad = [n for n in phases_skipped if n not in known]
        if bad:
            raise click.BadParameter(
                f"--phase-skipped {bad}: not phases this pipeline has. "
                f"Known: {', '.join(sorted(known))}")
        rec.data["phases_skipped"] = list(phases_skipped)
    out = rec.write(record_path_for(project, method, label))
    click.echo(f"✓ {out}")
    _inline_checks(out)

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


@provenance.command("backfill-spec")
@click.option("--project", required=True)
@click.option("--method", default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option("--label", required=True)
@click.option("--condition", required=True, help="the condition the instruction was rendered under")
@click.option("--runtime", default="Claude Code", show_default=True)
@click.option("--arm", type=click.Choice(sorted(_ARMS)), default="baseline", show_default=True)
@click.option("--execute", is_flag=True, help="write the spec; without it, report only")
def backfill_spec(project, method, label, condition, runtime, arm, execute):
    """Attach the render spec to a record that recorded its request hash
    without one (#772).

    A launcher that passes --prompt-text but not --condition leaves the record
    `unverifiable`: the hash of what was sent is there, the spec that would
    re-render it is not. This reconstructs the spec from the arguments given
    and the record's own inputs, and writes it **only when re-rendering it
    reproduces the recorded hash** — the same test `d4d runs check` applies —
    trying the record's own date and its neighbours for the `# Generated:`
    line. A spec that does not re-render to the hash is not written: that
    would assert a condition the run may not have used.
    """
    from data_sheets_schema.cli.method import resolve_method
    method = method or resolve_method(label, project)
    import hashlib
    from datetime import date, timedelta

    import yaml as _yaml

    from data_sheets_schema import provenance as pv
    from data_sheets_schema.api_runner import RunSpec, resolve_prompt

    path = pv.record_path_for(project, method, label, pv.CONCAT_DIR)   # resolved at call time
    if not path.exists():
        raise click.ClickException(f"no provenance record at {path}")
    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    req = ((data.get("prompts") or {}).get("request")) or {}
    if not req.get("sha256"):
        raise click.ClickException("the record carries no request hash; nothing to attach a spec to")
    if isinstance(req.get("spec"), dict) and req["spec"].get("condition"):
        click.echo(f"   · {label}/{project}: spec already present ({req['spec']['condition']})")
        return
    bundle = ((data.get("inputs") or {}).get("bundle_path"))
    if not bundle:
        raise click.ClickException("the record names no input bundle; the spec needs one")
    stamp = (data.get("record_generated_at") or "")[:10]
    base = date.fromisoformat(stamp) if stamp else date.today()
    # The provider the record itself states — `d4d prompt render` writes the
    # runtime's provider (Anthropic for Claude Code), not the proxy identity
    # the API path's default spec carries, and the header line differs.
    provider = (data.get("model") or {}).get("provider") or None
    for delta in (0, -1, 1, -2):
        spec = RunSpec(project=project, arm=_ARMS[arm][0], method=method, bundle=Path(bundle),
                       label=label, condition=condition, runtime=runtime, provider=provider,
                       run_date=(base + timedelta(days=delta)).isoformat())
        got = hashlib.sha256(resolve_prompt(spec).encode("utf-8")).hexdigest()
        if got == req["sha256"]:
            rendered = spec.render_spec()
            click.echo(f"   ✓ {label}/{project}: {condition} on {rendered['run_date']} re-renders to the recorded hash")
            if execute:
                data["prompts"]["request"]["spec"] = rendered
                data["prompts"]["request"]["spec_basis"] = ("backfilled by d4d provenance backfill-spec: "
                                                            "verified by re-rendering to the recorded hash (#772)")
                pv.ProvenanceRecord(data=data).write(path)
                click.echo(f"     written to {path}")
            return
    raise click.ClickException(
        f"{label}/{project}: no spec under {condition}/{runtime}/{arm}/provider {provider!r} "
        f"(from the record's model.provider) re-renders to the recorded hash "
        f"{req['sha256'][:12]}… on {base}±2 days; not written. A run under another arm "
        f"needs its --method too (the {{METHOD}} substitution differs).")


@provenance.command('annotate-observed')
@click.option('--project', required=True)
@click.option('--method', required=True)
@click.option('--label', required=True)
@click.option('--run', 'run_observed', required=True,
              help='JSON object of aggregate totals the orchestrator observed '
                   'for the whole run, e.g. \'{"total_tokens": 481000, '
                   '"tool_uses": 220, "duration_ms": 5400000}\'. Keys are '
                   'validated like a phase\'s observed block.')
@click.option('--until', 'until', default=None,
              help='ISO timestamp at which the observation was cut, when the '
                   'agent kept acting after its run completed. Recorded as '
                   'run_observed_until so the totals can be reproduced from '
                   'the transcript with the same cut.')
def annotate_observed(project, method, label, run_observed, until):
    """Add run-level observed totals to an existing record (#681 follow-on).

    The two-speakers model, applied where four-phase project-agent mode leaves
    it: the run records its own phases (which it knows) and cannot know its
    accounting (#400); the orchestrator that launched it as one subagent
    observes aggregate totals for the whole run — a single boundary, so
    per-phase observed blocks would claim a measurement nobody made. This
    command lets the launcher add exactly what it saw, after the run has
    written its own record, without retyping any of the run's flags: it edits
    the phase_log in place. The record's `validation` block rides along
    verbatim — the loaded data already carries it, so the re-record
    carry-forward check never runs on this path; that is safe because
    annotation changes no artifact and staleness is re-derived from the
    artifact hashes at read time, but it is carriage, not re-verification.
    """
    import json

    _require_repo_root_cwd("d4d provenance annotate-observed")
    from data_sheets_schema.provenance import (ProvenanceRecord,
                                               record_path_for)
    try:
        observed = json.loads(run_observed)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(f"--run is not valid JSON: {exc}") from exc
    if (not isinstance(observed, dict) or not observed
            or not set(observed) <= _OBSERVED_FIELDS):
        raise click.BadParameter(
            f"--run must be a non-empty object with keys from "
            f"{sorted(_OBSERVED_FIELDS)}")
    bad = {k: v for k, v in observed.items()
           if not isinstance(v, int) or isinstance(v, bool) or v < 0}
    if bad:
        raise click.BadParameter(
            f"--run values must be non-negative integers as measured, "
            f"got {bad}")

    path = record_path_for(project, method, label)
    if not path.exists():
        raise click.ClickException(
            f"no record at {path} — annotate after the run has recorded, "
            "not instead of it: this command adds the orchestrator's "
            "observation to the run's own account, it does not create one.")
    import yaml as _yaml
    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("api_usage"):
        raise click.ClickException(
            "this is an API-path record: api_usage already accounts for "
            "every call, per phase and with an input/output split. A "
            "run_observed block on top of it would double-count the same "
            "spend under a coarser basis (#400).")
    log = data.get("phase_log")
    if not isinstance(log, dict):
        raise click.ClickException(
            "the record has no phase_log — a run that attested no phases "
            "has no account for this observation to annotate. Have the "
            "run re-record with --phase first (an agentic run; an API "
            "record would have been refused above).")
    prior = log.get("run_observed")
    if prior is not None and prior != observed:
        raise click.ClickException(
            f"the record already carries run_observed {prior}. An "
            "observation is made once; silently replacing it would drop "
            "measurements without trace. If the prior value is wrong, "
            "remove it in a reviewed edit that says why.")
    log["run_observed"] = observed
    if until:
        log["run_observed_until"] = until
    elif "run_observed_until" in log:
        del log["run_observed_until"]
    log["run_observed_basis"] = (
        "aggregate totals for the whole run, observed by the orchestrator "
        "from the subagent runner's transcript. One number per run, not per "
        "phase: four-phase project-agent mode runs every phase in one "
        "context, so the run is the only observable boundary. Not the "
        "runtime's own accounting, no input/output split, not billing-grade; "
        "deliberately not shaped like api_usage (#681/#682). total_tokens "
        "counts each API message once (a response spans several transcript "
        "lines); duration_ms sums each invocation's own span, so a resumed "
        "run excludes the gap. bundle_lines_read is the union of the run's "
        "successful file-reading windows over the declared bundle (#700): "
        "lines the run never opened, or opened only in a read that errored, "
        "may have been reached by search, but nothing attests that."
        + (" Cut at run_observed_until: the agent kept acting after its run "
           "completed, and the record describes the run." if until else ""))
    rec = ProvenanceRecord(data=data)
    out = rec.write(path)
    click.echo(f"✓ {out}")
    for v in rec.conformance:
        click.echo(f"  ⚠️  {v}")
    if rec.conformance_failure:
        click.echo(f"  ⚠️  conformance not established: "
                   f"{rec.conformance_failure} — an unchecked record is "
                   "not a passing one (#613)")


@provenance.command()
@click.option('--verified-label', 'verified', multiple=True,
              help='Run labels whose input bytes are known unchanged; may repeat.')
@click.option('--dry-run', is_flag=True)
def backfill(verified, dry_run):
    """Reconstruct provenance records for runs already on disk.

    Refuses to run from anywhere but the repository root — see
    _require_repo_root_cwd.

    Fields that cannot be honestly recovered are listed under `unrecoverable`
    rather than filled from present-day observation. Pass --verified-label for
    runs whose inputs are known unchanged, so their input hashes can be
    recorded.
    """
    _require_repo_root_cwd("d4d provenance backfill")
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
@click.option('--blocks', default=None,
              help='comma-separated subset to write (pair_consistency, report_claims, form, '
                   'grounding, receipts); the others are neither computed for the report '
                   'nor touched — an instrument revision to one block must not overwrite '
                   'a grounding block the run attested on bytes that have since drifted')
def backfill_checks(execute, method, label, project, overwrite, blocks):
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

    from data_sheets_schema.backfill_checks import BLOCKS
    wanted = None
    if blocks:
        wanted = {b.strip() for b in blocks.split(",") if b.strip()}
        unknown = wanted - set(BLOCKS)
        if unknown:
            raise click.ClickException(f"unknown block(s) {sorted(unknown)}; choose from {list(BLOCKS)}")

    # Built once. Each call loads two SchemaViews, which over 122 records is
    # the difference between seconds and minutes.
    declared = declared_slots()
    written = skipped = 0
    import yaml as _yaml
    from datetime import datetime, timezone

    from data_sheets_schema.backfill_checks import _split_header
    from data_sheets_schema.grounding import BRITISH_INSTRUMENT
    for p in paths:
        withheld: list[str] = []
        try:
            blocks = compute(p, declared, only=wanted)
            if "form" in blocks and overwrite:
                # The audit trail of a form recompute (#907 review): the
                # prior instrument note and British count are carried
                # into the new block, so an instrument revision reads as
                # a sequence rather than replacing its own history.
                prior = ((_yaml.safe_load(_split_header(p.read_text(encoding="utf-8"))[1]) or {})
                         .get("form") or {})
                if prior:
                    note = (f"form recomputed {datetime.now(timezone.utc).date().isoformat()} by "
                            f"backfill-checks --overwrite, british instrument {BRITISH_INSTRUMENT}; "
                            f"previous british={prior.get('british_spellings')}")
                    if prior.get("instrument_note"):
                        note = f"{prior['instrument_note']} | {note}"
                    blocks["form"]["instrument_note"] = note
            # Inside the same guard as compute: a write that raises halfway
            # through 192 records leaves a corpus in two states, and the reason
            # it raised is exactly the kind a reader needs to see per-record.
            changed = apply(p, blocks, overwrite=overwrite, withheld=withheld) if execute else True
        except Exception as exc:                               # noqa: BLE001
            click.echo(f"   ✗ {p.parts[-2]}/{p.name}: {exc}")
            continue
        if execute and not changed:
            skipped += 1
            continue
        written += 1
        click.echo(f"   {'✔' if execute else '·'} {p.parts[-2][:38]:38} "
                   f"{p.name[:-16]:16} {summarise(blocks)}"
                   + (f" · kept attested {','.join(withheld)} (recomputation could not measure)" if withheld else ""))
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


@provenance.command("validate-records")
@click.option('--strict', is_flag=True, help='exit 1 if any record fails')
@click.option('--label', default=None, help='restrict to one run label')
def validate_records(strict, label):
    """Validate generation records against their own LinkML schema.

    This repository schematises metadata about datasets, and its own generation
    metadata was a hand-built dictionary that nothing could check — 25
    top-level keys and no definition. The one artifact that did have a schema,
    `d4d_run_telemetry.yaml`, is the derived report rather than the
    authoritative record.

    The schema is deliberately not imported by `data_sheets_schema.yaml`: it
    describes the pipeline, not a dataset, so importing it would move the
    `Dataset` digest a generation arm is frozen against.
    """
    import subprocess
    import sys

    from data_sheets_schema.provenance import CONCAT_DIR, record_schema_path

    # Resolved, not hardcoded (#620). Run from outside the repo root the
    # literal path does not exist and `linkml-validate` exits non-zero on every
    # record, reporting a clean corpus as entirely failing. Loud rather than
    # silent, so not the #618 failure mode — but #618 fixed the gate and left
    # the command it was written about still holding the literal.
    schema = record_schema_path()
    paths = sorted(CONCAT_DIR.glob("*_core/*/*_provenance.yaml"))
    if label:
        paths = [p for p in paths if p.parts[-2] == label]
    if not paths:
        click.echo("no records matched")
        return

    failed = []
    for p in paths:
        r = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", str(schema),
             "-C", "GenerationRecord", str(p)],
            capture_output=True, text=True)
        if r.returncode != 0:
            failed.append(p)
            click.echo(f"   ❌ {p.parts[-2][:38]:38} {p.name}")
            for line in (r.stdout + r.stderr).splitlines():
                if "[ERROR]" in line:
                    click.echo(f"      {line.split(']')[-1].strip()[:110]}")

    click.echo(f"\n{len(paths)} record(s) checked, {len(failed)} failing")
    if not failed:
        click.echo("Every generation record conforms to its schema.")
    if strict and failed:
        sys.exit(1)
