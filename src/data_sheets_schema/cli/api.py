"""API generation commands — six-phase D4D runs over the Anthropic API."""

import json
import sys
from pathlib import Path

import click

from data_sheets_schema.api_runner import CONDITION_PROMPTS

from data_sheets_schema.constants import PROJECTS

ARMS = {
    "baseline": ("BASELINE (input documents only)", "claudecode_agent",
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


def _require_bundle(spec, project, bundle):
    if bundle is None and project not in PROJECTS:
        raise click.ClickException(
            f"{project!r} is not one of the known projects ({', '.join(PROJECTS)}), "
            "so its bundle cannot be resolved by convention. Pass --bundle.")
    if not spec.bundle.exists():
        raise click.ClickException(f"bundle not found: {spec.bundle}")


@click.group()
def api():
    """Generate D4D records via the Anthropic API (six-phase)."""


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
    from data_sheets_schema.api_runner import resolve_prompt

    spec = _spec(project, arm, label, condition, bundle,
                 runtime=runtime, provider=provider)
    _require_bundle(spec, project, bundle)
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
    p = plan(spec)
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
    """Execute all six phases and write outputs plus a live provenance record."""
    from data_sheets_schema.api_runner import execute, plan
    spec = _spec(project, arm, label, condition, bundle, out_dir)
    _require_bundle(spec, project, bundle)
    if spec.full_path.exists():
        raise click.ClickException(
            f"{spec.full_path} already exists; a run label is never reused")

    p = plan(spec)
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
@click.option("--yes", is_flag=True)
def batch_cmd(projects, arm, condition, replicates, label_prefix, dry_run,
              continue_on_error, yes):
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
            specs.append(s)

    plans = [plan(s) for s in specs]
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

    ok, failed, spent_in, spent_out = [], [], 0, 0
    for i, s in enumerate(specs, 1):
        click.echo(f"\n[{i}/{len(specs)}] {s.project} {s.label}")
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
                if not continue_on_error:
                    click.echo("stopping; re-run to resume", err=True)
                    break
                continue
            click.echo(f"   ✓ in={spent_in:,} out={spent_out:,} cache_read={cached:,}{note}")
            ok.append(s.label)
        except Exception as exc:                       # noqa: BLE001
            click.echo(f"   ❌ {type(exc).__name__}: {exc}", err=True)
            failed.append((s.project, s.label, str(exc)))
            if not continue_on_error:
                click.echo("stopping; re-run to resume unfinished phases", err=True)
                break

    click.echo(f"\n{len(ok)} succeeded, {len(failed)} failed")
    click.echo(f"tokens: {spent_in:,} in, {spent_out:,} out")
    for p, lbl, err in failed:
        click.echo(f"   {p} {lbl}: {err[:90]}")
    if failed:
        sys.exit(1)
