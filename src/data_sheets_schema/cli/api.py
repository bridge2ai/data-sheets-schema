"""API generation commands — four-phase D4D runs over the Anthropic API."""

import json
from pathlib import Path

import click

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


def _spec(project, arm, label, condition):
    from data_sheets_schema.api_runner import RunSpec
    display, method, pattern, manifest = ARMS[arm]
    return RunSpec(project=project, arm=display, method=method,
                   bundle=Path("data/preprocessed/concatenated") /
                          pattern.format(p=project),
                   label=label, condition=condition, manifest_line=manifest)


@click.group()
def api():
    """Generate D4D records via the Anthropic API (four-phase)."""


@api.command("plan")
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--label", required=True, help="run label, e.g. 2026-07-29_claude-opus-5-api-generic_rep1")
@click.option("--condition", type=click.Choice(["generic", "tuned"]),
              default="generic", show_default=True)
@click.option("--json", "as_json", is_flag=True, help="emit the full plan as JSON")
def plan_cmd(project, arm, label, condition, as_json):
    """Render every phase without calling the API — no key, no charge."""
    from data_sheets_schema.api_runner import plan
    spec = _spec(project, arm, label, condition)
    if not spec.bundle.exists():
        raise click.ClickException(f"bundle not found: {spec.bundle}")
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
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--arm", type=click.Choice(sorted(ARMS)), default="baseline",
              show_default=True)
@click.option("--label", required=True)
@click.option("--condition", type=click.Choice(["generic", "tuned"]),
              default="generic", show_default=True)
@click.option("--yes", is_flag=True, help="skip the cost confirmation")
def run_cmd(project, arm, label, condition, yes):
    """Execute all four phases and write outputs plus a live provenance record."""
    from data_sheets_schema.api_runner import execute, plan
    spec = _spec(project, arm, label, condition)
    if not spec.bundle.exists():
        raise click.ClickException(f"bundle not found: {spec.bundle}")
    if spec.full_path.exists():
        raise click.ClickException(
            f"{spec.full_path} already exists; a run label is never reused")

    p = plan(spec)
    click.echo(f"~{p['approx_total_input_tokens']:,} input tokens across 4 phases "
               f"on {p['model']['name']}")
    if not yes and not click.confirm("Proceed with billed API calls?"):
        click.echo("aborted")
        return
    res = execute(spec)
    for u in res["usage"]:
        click.echo(f"   {u['phase']:10} in={u['input_tokens']} out={u['output_tokens']} "
                   f"cache_read={u['cache_read']} cache_write={u['cache_write']}")
    click.echo(f"✓ {res['project']} {res['label']}")
    for k, v in res["outputs"].items():
        click.echo(f"   {k:6} {v}")
