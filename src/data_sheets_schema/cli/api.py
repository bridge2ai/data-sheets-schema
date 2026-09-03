"""API generation commands — D4D runs over the Anthropic API (four model phases; the core is derived, #694)."""

import json
import sys
from pathlib import Path

import click

from data_sheets_schema.api_runner import CONDITION_PROMPTS

from data_sheets_schema.constants import PROJECTS

# `baseline` writes under `claudecode_api` from generic_v8 on (#690, v8 plan
# D6): the API and agentic runtimes shared `claudecode_agent` through v7 and
# were told apart only by the label and `model.agent_runtime`. The other arms
# were only ever run on the API path and keep their directories.
ARMS = {
    "baseline": ("BASELINE (input documents only)", "claudecode_api",
                 "{p}_preprocessed.txt",
                 "# Source manifest: data/preprocessed/source_manifest.yaml"),
    "de_novo": ("DE NOVO WITH CRATE (documents + RO-Crate evidence)",
                "claudecode_agent_crate", "{p}_preprocessed_with_crate.txt",
                "# Source manifest: data/preprocessed/source_manifest.yaml"),
    "crate_only": ("CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)",
                   "claudecode_agent_crate_only", "{p}_crate_only.txt",
                   "# Source manifest: not used (crate-only arm; single declared source bundle)"),
    "healthsheet": ("HEALTHSHEET-ONLY (single structured upstream source)",
                    "claudecode_agent_healthsheet", "{p}_healthsheet_only.txt",
                    "# Source manifest: not used; this arm declares its single source bundle explicitly"),
}


# Read from the registry rather than repeated inline. The list was written out
# three times, so adding `generic_v2` to CONDITION_PROMPTS left it unreachable
# from every CLI entry point — the condition was staged, tested, and could not be
# launched.
_CONDITIONS = sorted(CONDITION_PROMPTS)


def _spec(project, arm, label, condition, bundle=None, out_dir=None,
          runtime=None, provider=None):
    """Resolve a run spec.

    `project` is a free string rather than a click.Choice because the GitHub
    assistant generates datasheets for datasets outside the four study
    projects. A known project resolves its bundle by convention; anything else
    must declare one, which is checked in `_require_bundle`.
    """
    from data_sheets_schema.api_runner import RunSpec
    display, method, pattern, manifest = ARMS[arm]
    resolved = (Path(bundle) if bundle else
                Path("data/preprocessed/concatenated") / pattern.format(p=project))
    kw = {}
    if runtime:
        kw["runtime"] = runtime
    if provider:
        kw["provider"] = provider
    return RunSpec(project=project, arm=display, method=method,
                   bundle=resolved, label=label, condition=condition,
                   manifest_line=manifest,
                   out_dir=Path(out_dir) if out_dir else None, **kw)


def _require_canonical_prompts(spec):
    """Refuse to spend money under a prompt file nobody declared (#432).

    Checked before the cost confirmation, because the cheapest place to catch
    an undeclared prompt is before it has produced a record that then has to be
    argued about. There is no override flag: declaring the text is one command
    and leaves the dated line that makes the condition auditable, which is the
    entire mechanism. A new prompt version is *meant* to stop here once.
    """
    from data_sheets_schema import prompt_registry as pr

    bad = [(p, pr.disk_status(p)) for p in spec.prompt_files]
    bad = [(p, why) for p, (st, why) in bad if st != pr.CANONICAL]
    if not bad:
        return
    lines = "\n".join(f"   {pr.normalise(p)}: {why}" for p, why in bad)
    raise click.ClickException(
        f"prompt file(s) not at their canonical hash for condition "
        f"{spec.condition!r}:\n{lines}\n"
        "Declare the text with `d4d api prompts pin --file <path> --reason "
        "'<why>'`, then re-run. A run under an undeclared prompt cannot be "
        "placed in the study.")


def _require_bundle(spec, project, bundle):
    if bundle is None and project not in PROJECTS:
        raise click.ClickException(
            f"{project!r} is not one of the known projects ({', '.join(PROJECTS)}), "
            "so its bundle cannot be resolved by convention. Pass --bundle.")
    if not spec.bundle.exists():
        raise click.ClickException(f"bundle not found: {spec.bundle}")


def _canary_never_ran(spec, baseline, what_happened: str) -> str:
    """The stop message for a canary that produced no verdict at all (#619).

    Distinct from a canary that ran and regressed: there, the gate can name the
    metric that moved. Here there is no measurement, and "no measurement" is
    the one thing this corpus insists must not read as "fine".
    """
    return (f"canary did not pass: the first run ({spec.project} "
            f"{spec.label}) never produced a verdict against the {baseline} "
            f"baseline because {what_happened}. Fanning out would spend the "
            "rest of the sweep on a failure that has not been diagnosed, and "
            "these failures are usually systematic — the remaining runs would "
            "hit it too, each after being billed. Fix it and re-run, or pass "
            "--no-canary-gate to proceed anyway.")



def _plan_or_refuse(spec):
    """A plan that cannot be assembled is a refusal with a reason, not a
    traceback (#742): a receipt condition on a bundle with no chunk manifest."""
    from data_sheets_schema.api_runner import plan
    try:
        return plan(spec)
    except RuntimeError as exc:
        raise click.ClickException(str(exc))

@click.group()
def api():
    """Generate D4D records via the Anthropic API (four model phases plus a derived core)."""


@api.command("render-prompt")
@click.option("--project", required=True,
              help="AI_READI|CHORUS|CM4AI|VOICE, or any dataset name with --bundle")
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--label", required=True, help="run label")
@click.option("--condition", type=click.Choice(_CONDITIONS), default="generic",
              show_default=True)
@click.option("--bundle", type=click.Path(), default=None,
              help="explicit input bundle; required for datasets outside PROJECTS")
@click.option("--runtime", default="Claude Code", show_default=True,
              help="runtime the instruction should declare")
@click.option("--provider", default="Anthropic", show_default=True)
@click.option("--out", type=click.Path(), default=None,
              help="write the instruction here as well as printing its digest")
def render_prompt_cmd(project, arm, label, condition, bundle, runtime,
                      provider, out):
    """Render the exact instruction a run should receive, for any runtime.

    The API path never types an instruction: `resolve_prompt()` builds it from
    the spec, so the condition, the substitutions and the per-project content
    are all functions of declared inputs. The agentic path had no way to obtain
    that text, so its launch prompts were hand-composed — and the VOICE run of
    2026-08-07 was sent a project-specific scope paragraph that appears in no
    prompt file, while its provenance recorded the base file and the header
    said "identical for all projects" (#419, #422).

    Rendering closes that by construction rather than by discipline. Per-project
    content can then only enter through `--condition tuned`, which is a declared
    door that the record names.

    The digest is of the resolved text, not the file. Substitution is what makes
    the two different objects, which is why `prompt_request_hash` exists.
    """
    import hashlib
    from data_sheets_schema import prompt_registry as pr
    from data_sheets_schema.api_runner import resolve_prompt

    spec = _spec(project, arm, label, condition, bundle,
                 runtime=runtime, provider=provider)
    _require_bundle(spec, project, bundle)

    # Warned, not refused. Rendering is free and reading the text of a draft
    # condition is a legitimate reason to be here; `d4d api run` refuses and
    # `d4d runs check` fails, so the fatal gates sit where a claim is made
    # rather than where text is inspected. But this is the agentic path's
    # launch point, and an edit made before rendering is invisible downstream
    # by construction (#432) — so it has to be said here.
    for f in spec.prompt_files:
        st, why = pr.disk_status(f)
        if st != pr.CANONICAL:
            click.echo(f"# ⚠️  {st}: {why}", err=True)

    text = resolve_prompt(spec)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(f"✓ {out}", err=True)
    click.echo(f"# rendered {condition} for {project} / {arm} / runtime={runtime}",
               err=True)
    click.echo(f"# sha256 {digest}  ({len(text.encode('utf-8'))} bytes)", err=True)
    click.echo(f"# record it with: d4d provenance record ... --prompt-text <file>",
               err=True)
    if not out:
        click.echo(text)


@api.command("plan")
@click.option("--project", required=True,
              help="AI_READI|CHORUS|CM4AI|VOICE, or any dataset name with --bundle")
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--label", required=True, help="run label, e.g. 2026-07-29_claude-opus-5-api-generic_rep1")
@click.option("--condition", type=click.Choice(_CONDITIONS),
              default="generic", show_default=True)
@click.option("--bundle", type=click.Path(), default=None,
              help="explicit input bundle; required for datasets outside PROJECTS")
@click.option("--out-dir", type=click.Path(), default=None,
              help="flat output directory (the assistant layout)")
@click.option("--json", "as_json", is_flag=True, help="emit the full plan as JSON")
def plan_cmd(project, arm, label, condition, bundle, out_dir, as_json):
    """Render every phase without calling the API — no key, no charge."""
    from data_sheets_schema.api_runner import plan
    spec = _spec(project, arm, label, condition, bundle, out_dir)
    _require_bundle(spec, project, bundle)
    p = _plan_or_refuse(spec)
    if as_json:
        click.echo(json.dumps(p, indent=2))
        return
    click.echo(f"📋 {p['project']} / {arm} / {p['condition']}")
    click.echo(f"   model    {p['model']['name']}  temp={p['model']['temperature']}  "
               f"max_tokens={p['model']['max_tokens']}")
    click.echo(f"   runtime  {p['runtime']}")
    click.echo(f"   bundle   {p['bundle']}  ({p['bundle_bytes']:,} b)")
    click.echo(f"   prompts  {', '.join(Path(x).name for x in p['prompt_files'])}")
    click.echo(f"   digest   md5 {p['schema_digest_md5'][:12]}")
    for ph in p["phases"]:
        click.echo(f"     {ph['phase']:10} ~{ph['approx_input_tokens']:>8,} tok"
                   f"   cached blocks={ph['cached_blocks']}")
    click.echo(f"   total    ~{p['approx_total_input_tokens']:,} input tokens "
               f"(uncached; phases 2-4 reuse the cached prefix)")
    for k, v in p["outputs"].items():
        click.echo(f"   -> {k:6} {v}")


@api.command("run")
@click.option("--project", required=True,
              help="AI_READI|CHORUS|CM4AI|VOICE, or any dataset name with --bundle")
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--label", required=True)
@click.option("--condition", type=click.Choice(_CONDITIONS),
              default="generic", show_default=True)
@click.option("--bundle", type=click.Path(), default=None,
              help="explicit input bundle; required for datasets outside PROJECTS")
@click.option("--out-dir", type=click.Path(), default=None,
              help="flat output directory (the assistant layout)")
@click.option("--yes", is_flag=True, help="skip the cost confirmation")
def run_cmd(project, arm, label, condition, bundle, out_dir, yes):
    """Execute every phase (four model calls; the core is derived from the full) and write outputs plus a live provenance record."""
    from data_sheets_schema.api_runner import execute, plan
    spec = _spec(project, arm, label, condition, bundle, out_dir)
    _require_bundle(spec, project, bundle)
    _require_canonical_prompts(spec)
    if spec.full_path.exists():
        raise click.ClickException(
            f"{spec.full_path} already exists; a run label is never reused")

    p = _plan_or_refuse(spec)
    click.echo(f"~{p['approx_total_input_tokens']:,} input tokens across 6 phases "
               f"on {p['model']['name']}")
    if not yes and not click.confirm("Proceed with billed API calls?"):
        click.echo("aborted")
        return
    res = execute(spec)
    for u in res["usage"]:
        click.echo(f"   {u['phase']:10} in={u['input_tokens']} out={u['output_tokens']} "
                   f"cache_read={u['cache_read']} cache_write={u['cache_write']}")

    problems = res.get("validation_problems") or []
    if problems:
        # The first live run printed a tick over two records that failed
        # validation. A run that produced invalid output has not succeeded,
        # and must not exit 0.
        click.echo(f"❌ {res['project']} {res['label']} — "
                   f"{len(problems)} validation failure(s)", err=True)
        for p in problems:
            click.echo(f"   {p.get('artifact')}", err=True)
            click.echo(f"     {p.get('error')}", err=True)
        click.echo("   Resume state kept; fix and re-run to redo only what "
                   "is needed.", err=True)
        sys.exit(2)

    click.echo(f"✓ {res['project']} {res['label']} — both records validate")
    for k, v in res["outputs"].items():
        click.echo(f"   {k:10} {v}")


@api.command("batch")
@click.option("--projects", default="AI_READI,CHORUS,CM4AI,VOICE", show_default=True,
              help="comma-separated")
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--condition", type=click.Choice(_CONDITIONS),
              default="generic", show_default=True)
@click.option("--replicates", type=int, default=3, show_default=True)
@click.option("--label-prefix", required=True,
              help="e.g. 2026-07-29_claude-opus-5-api-generic; _rep{N} is appended")
@click.option("--dry-run", is_flag=True, help="cost the sweep without calling the API")
@click.option("--continue-on-error", is_flag=True,
              help="keep going after a failed run instead of stopping")
@click.option("--canary-baseline", default=None,
              help="label prefix of the arm the first run is held against; it "
                   "must be no worse on any check or the sweep stops (#579)")
@click.option("--branch-guard/--no-branch-guard", default=True, show_default=True,
              help="refuse a run whose label is tracked on a git ref but absent from disk (#795); "
                   "--no-branch-guard for a run that was removed on purpose")
@click.option("--no-canary-gate", is_flag=True,
              help="fan out even if the first run regresses against the "
                   "baseline; the comparison is still printed")
@click.option("--yes", is_flag=True)
def batch_cmd(projects, arm, condition, replicates, label_prefix, dry_run,
              continue_on_error, canary_baseline, no_canary_gate, yes, branch_guard):
    """Run a sweep of projects x replicates, reporting cumulative cost.

    Each run resumes independently, so a sweep interrupted partway costs only
    the unfinished phases to complete rather than restarting.
    """
    from data_sheets_schema.api_runner import execute, plan

    names = [p.strip() for p in projects.split(",") if p.strip()]
    specs = []
    for p in names:
        for n in range(1, replicates + 1):
            s = _spec(p, arm, f"{label_prefix}_rep{n}", condition)
            if not s.bundle.exists():
                raise click.ClickException(
                    f"bundle not found for {p}: {s.bundle}")
            _require_canonical_prompts(s)
            specs.append(s)

    plans = [_plan_or_refuse(s) for s in specs]
    total = sum(x["approx_total_input_tokens"] for x in plans)
    click.echo(f"📦 {len(specs)} runs — {len(names)} projects x {replicates} "
               f"replicates, arm={arm}, condition={condition}")
    for s, x in zip(specs, plans):
        click.echo(f"   {s.project:9} {s.label:44} ~{x['approx_total_input_tokens']:>8,} tok")
    click.echo(f"   {'TOTAL':9} {'':44} ~{total:>8,} input tokens (uncached)")

    if dry_run:
        return
    if not yes and not click.confirm(f"Run {len(specs)} billed generations?"):
        click.echo("aborted")
        return

    # Claim the label prefix before spending anything (#513). Two batches
    # writing the same label directories is not a tolerable race: each writes
    # phase snapshots and a progress file under the same names, so the
    # survivor's record can be a mixture of both runs while its provenance
    # describes neither. That happened on 2026-08-11.
    # A run that is tracked on another branch but not on disk must not be
    # generated again under its label (#795): the checkout that removed it
    # from the working tree is the only reason it looks absent.
    from data_sheets_schema import run_guard
    tracked = run_guard.tracked_core_dirs() if branch_guard else {}
    found = run_guard.runs_on_other_refs([(s.label, s.method) for s in specs], tracked) if branch_guard else []
    if found:
        raise click.ClickException(run_guard.message(found))

    from data_sheets_schema import run_lock
    try:
        lock_path = run_lock.acquire(label_prefix, names)
    except run_lock.AlreadyRunning as exc:
        raise click.ClickException(str(exc)) from exc

    ok, failed, spent_in, spent_out = [], [], 0, 0
    canary_stop: str | None = None
    #: Whether the fan-out is gated on the first run at all. Read in three
    #: places, so it is computed once rather than restated (#619).
    gating = bool(canary_baseline) and not no_canary_gate
    for i, s in enumerate(specs, 1):
        click.echo(f"\n[{i}/{len(specs)}] {s.project} {s.label}")
        # Again, per run (#799): the checkout that empties the working tree
        # can happen while this batch is live, and the one-shot check above
        # has already passed by then. Outside the per-run try, so the refusal
        # stops the batch rather than counting as one failed run.
        if branch_guard:
            late = run_guard.runs_on_other_refs([(s.label, s.method)], run_guard.tracked_core_dirs())
            if late:
                # Stop the loop and raise after the lock is released, as the
                # canary stop does: the release below is not in a finally.
                canary_stop = run_guard.message(late)
                break
        try:
            res = execute(s)
            spent_in += sum(u["input_tokens"] or 0 for u in res["usage"])
            spent_out += sum(u["output_tokens"] or 0 for u in res["usage"])
            cached = sum(u["cache_read"] or 0 for u in res["usage"])
            note = f"  (resumed, skipped {len(res['skipped'])})" if res["skipped"] else ""
            vp = res.get("validation_problems") or []
            if vp:
                # A sweep must not count an invalid record as a success, or the
                # summary line reports work that cannot be used.
                click.echo(f"   ❌ invalid output ({len(vp)} failure(s)) "
                           f"in={spent_in:,} out={spent_out:,}", err=True)
                for p in vp:
                    click.echo(f"      {p.get('artifact')}: {p.get('error')}",
                               err=True)
                failed.append((s.project, s.label,
                               f"{len(vp)} validation failure(s)"))
                if gating and i == 1:
                    canary_stop = _canary_never_ran(
                        s, canary_baseline,
                        f"it produced {len(vp)} validation failure(s)")
                if not continue_on_error and not canary_stop:
                    click.echo("stopping; re-run to resume", err=True)
                    break
                if canary_stop:
                    break
                continue
            click.echo(f"   ✓ in={spent_in:,} out={spent_out:,} cache_read={cached:,}{note}")

            # The three post-generation checks, printed for every run so a
            # sweep cannot look clean while they fail (#579) — and, on the
            # first run, gating the fan-out.
            from data_sheets_schema import canary as _canary
            counts = _canary.counts_from(res.get("checks") or {})
            # Reported-only metrics too (#669 review): the commit that added
            # the GC-label metric said "report ... in the canary output" while
            # nothing output it — minted fragments had the same gap since
            # #602. Displayed after the gated ones, never gated.
            counts.update(_canary.counts_from(res.get("checks") or {},
                                              _canary.REPORTED_ONLY))
            click.echo("     " + "  ".join(
                f"{name}={'—' if v is None else v}"
                for name, v in counts.items()))

            if i == 1 and gating:
                bar = _canary.baseline_for(s.project, canary_baseline)
                v = _canary.verdict(res.get("checks") or {}, bar,
                                    baseline_requested=True)
                if v.get("unbaselined"):
                    click.echo(
                        f"     no baseline for {s.project} under "
                        f"{canary_baseline!r} — check the label prefix",
                        err=True)
                for row in v["rows"]:
                    mark = "❌" if row.get("regressed") else "  "
                    click.echo(f"     {mark} {row['metric']:24} "
                               f"{row['run']} vs baseline worst "
                               f"{row['baseline_worst']}")
                if v["status"] != _canary.OK:
                    for line in v["regressions"] or v["blind"]:
                        click.echo(f"     {line}", err=True)
                    # Recorded, not raised here: this block is inside the
                    # per-run `try`, whose bare `except Exception` would catch
                    # a ClickException and — under --continue-on-error — fan
                    # out anyway, which is the one thing this gate exists to
                    # prevent. Raised after the loop, once the lock is released.
                    canary_stop = (
                        f"canary {v['status']}: the first run is worse than "
                        f"the {canary_baseline} baseline for {s.project}, or a "
                        "check could not run. Fanning out would spend the rest "
                        "of the sweep on a known regression. Re-run with "
                        "--no-canary-gate to proceed anyway.")
                else:
                    click.echo("     canary ok — fanning out")
            ok.append(s.label)
        except Exception as exc:                       # noqa: BLE001
            click.echo(f"   ❌ {type(exc).__name__}: {exc}", err=True)
            failed.append((s.project, s.label, str(exc)))
            # A canary that *raised* has not passed, and before #619 nothing
            # said so: `canary_stop` was only ever set by a verdict, so a first
            # run that threw left the gate unevaluated and `--continue-on-error`
            # fanned out to the rest of the sweep. The failures that reach here
            # are systematic by construction — a broken validator, a writer the
            # schema does not know, an unreachable route — so they recur on
            # every run, after each is fully billed, and `ok` ends up empty.
            #
            # This is the gate's whole purpose stated the other way round: it
            # must fan out only on a canary that demonstrably passed, never
            # merely on one that failed to say it did not.
            if gating and i == 1:
                canary_stop = _canary_never_ran(
                    s, canary_baseline, f"it raised {type(exc).__name__}")
            if not continue_on_error:
                click.echo("stopping; re-run to resume unfinished phases", err=True)
                break
        if canary_stop:
            break

    # Released even when the sweep failed or was interrupted mid-loop: a lock
    # outliving its process would make the next attempt refuse to start, which
    # turns a crash into a permanent block. `live()` also checks the pid, so a
    # lock left by a hard kill is recognised as stale rather than believed.
    run_lock.release(lock_path)

    if canary_stop:
        raise click.ClickException(canary_stop)

    click.echo(f"\n{len(ok)} succeeded, {len(failed)} failed")
    click.echo(f"tokens: {spent_in:,} in, {spent_out:,} out")
    for p, lbl, err in failed:
        click.echo(f"   {p} {lbl}: {err[:90]}")
    if failed:
        sys.exit(1)


@api.command("status")
def api_status_cmd():
    """Which sweeps are running, and under what pid (#513).

    Exists because a batch cannot be found by name: a console-script entry
    point runs as `python -c import sys; …`, so `pgrep -f "d4d api"` returns
    nothing while the sweep is still spending. The lock is the answer that
    string matching cannot give.
    """
    from data_sheets_schema import run_lock

    running = run_lock.live()
    stale = run_lock.stale()
    if not running and not stale:
        click.echo("No sweep is running.")
        return
    for lock in running:
        click.echo(f"▶  pid {lock.pid}  {lock.label_prefix}  "
                   f"since {lock.started}  ({', '.join(lock.projects)})")
    for lock in stale:
        click.echo(f"·  stale lock for {lock.label_prefix} (pid {lock.pid} is "
                   f"gone) — a sweep died without releasing it: {lock.path}")
    if running:
        click.echo("\nStop one with `d4d api stop --label-prefix <prefix>`.")


@api.command("stop")
@click.option("--label-prefix", required=True)
@click.option("--force", is_flag=True, help="SIGKILL instead of SIGTERM")
def api_stop_cmd(label_prefix, force):
    """Stop a running sweep by the label it holds (#513).

    Stopping mid-run is safe: each run resumes from its progress file, so the
    cost of stopping is the unfinished phases of the current run and nothing
    more. What is *not* safe is believing a sweep has stopped when it has not,
    which is what this command exists to prevent.
    """
    import signal as _signal

    from data_sheets_schema import run_lock

    matches = [l for l in run_lock.live() if l.label_prefix == label_prefix]
    if not matches:
        click.echo(f"No running sweep holds {label_prefix!r}.")
        stale = [l for l in run_lock.stale() if l.label_prefix == label_prefix]
        if stale:
            click.echo("A stale lock exists; its process is already gone.")
        return
    for lock in matches:
        sig = _signal.SIGKILL if force else _signal.SIGTERM
        sent = run_lock.stop(lock, sig)
        click.echo(f"{'signalled' if sent else 'could not signal'} pid "
                   f"{lock.pid} ({'KILL' if force else 'TERM'})")
    click.echo("Re-run `d4d api status` to confirm it is gone — a signal sent "
               "is not a process stopped.")


@api.group("prompts")
def prompts_group():
    """The canonical prompt registry — what each condition's text is (#432)."""


@prompts_group.command("check")
@click.option("--strict", is_flag=True,
              help="Exit non-zero if any prompt file differs from its pin.")
def prompts_check_cmd(strict):
    """Check the prompt files on disk against their canonical hashes.

    The repo-state half of #432. `d4d runs check` asks the same question of
    records; this asks it of the working tree, so an undeclared edit is caught
    before it produces a run rather than after.
    """
    from data_sheets_schema import prompt_registry as pr

    rows = pr.check_disk()
    # Every state other than `canonical` fails here, `unpinned` included. The
    # record gate treats an unpinned path as absence of evidence, because a
    # record may legitimately name a prompt the registry does not cover; the
    # working tree has no such excuse. A condition prompt nobody pinned is
    # text that was never declared, which is the hole (#432), not a gap in it.
    # `annotated` is reported and not counted against the gate: the
    # instruction is at its pin and only rationale moved (#560).
    bad = [r for r in rows if r["status"] not in (pr.CANONICAL, pr.ANNOTATED)]
    annotated = [r for r in rows if r["status"] == pr.ANNOTATED]
    for r in rows:
        mark = {"canonical": "✓", "superseded": "⚠️ ", "annotated": "ⓘ ",
                "uncanonical": "❌", "unpinned": "❌",
                "missing": "❌"}[r["status"]]
        click.echo(f" {mark} {r['status']:12} {r['path']}")
        if r["reason"]:
            click.echo(f"       {r['reason']}")
    click.echo(f"\n{len(rows)} prompt file(s), {len(bad)} not at their pin"
               + (f", {len(annotated)} annotated (body unchanged)"
                  if annotated else ""))
    if bad:
        click.echo("Declare them with `d4d api prompts pin --file <path> "
                   "--reason '<why this is the condition's text>'`. Editing a "
                   "prompt without rotating its pin, or adding one without a "
                   "pin at all, is what this command is for.")
    if strict and bad:
        sys.exit(1)


@prompts_group.command("pin")
@click.option("--file", "path", required=True,
              type=click.Path(exists=True, dir_okay=False))
@click.option("--reason", required=True,
              help="Why this text is now canonical for its condition.")
def prompts_pin_cmd(path, reason):
    """Declare a prompt file's current bytes canonical, retiring the old pin.

    The previous hash is kept, not dropped: records written under it stay
    `superseded` rather than turning `uncanonical` the moment a prompt moves.
    """
    from data_sheets_schema import prompt_registry as pr

    res = pr.pin(path, reason)
    if res["status"] == "unchanged":
        click.echo(f"already pinned at {res['sha256'][:12]}… — nothing to do")
        return
    click.echo(f"✓ {res['path']} pinned at {res['sha256'][:12]}…")
    if res.get("previous"):
        click.echo(f"  previous {res['previous'][:12]}… kept as superseded, so "
                   "runs made under it still verify")
