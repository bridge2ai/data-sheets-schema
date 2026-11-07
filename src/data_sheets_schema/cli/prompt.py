"""Top-level home for prompt rendering.

`d4d api render-prompt` exists so the **agentic** path can obtain its
instruction rather than compose one by hand — but it lives under `d4d api`,
the group for generating records through the Anthropic API. So the command an
agentic run needs was filed under the path it is not taking, and `d4d api
--help` describes a group its audience is deliberately not using (#428).

The rendering machinery genuinely is the API runner's — `resolve_prompt`,
`RunSpec` and `CONDITION_PROMPTS` all live in `api_runner` — so this aliases
rather than moves. One implementation, two entry points, and the discoverable
one is named in `.claude/commands/d4d-full-core.md`, which is what an agentic
run actually reads.

Moving `resolve_prompt` and `RunSpec` into a shared module is the larger fix
the issue describes as option 2; it touches the module every API run goes
through, and is worth doing only if this shared surface grows.
"""

import click

from data_sheets_schema.cli.api import render_prompt_cmd


@click.group()
def prompt():
    """Render the instruction a run should receive, for any runtime."""


# The same command object, not a reimplementation: a copy would be free to
# drift, and two renderers that disagree is precisely the failure #425 was
# built to remove.
prompt.add_command(render_prompt_cmd, name="render")


@prompt.command("render-native-shared")
@click.option("--selection", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Exact native shared-generation selection JSON.")
@click.option("--runtime-declaration", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Sole runtime declaration, checked without invoking the runtime.")
@click.option("--job-id", required=True, help="Explicit job identity for the v2 preparation.")
@click.option("--provider", required=True, help="Must match the sole runtime declaration.")
@click.option("--reasoning-effort", required=True, help="Must match the sole runtime declaration.")
@click.option("--max-draft-checks", required=True, type=click.IntRange(min=1))
@click.option("--run-date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--out", type=click.Path(dir_okay=False), help="Write a new instruction file; refuse an existing file.")
def render_native_shared(selection, runtime_declaration, job_id, provider, reasoning_effort,
                         max_draft_checks, run_date, out):
    """Render genuine v2 preparation offline; this does not authorize execution."""
    from pathlib import Path
    import hashlib
    from data_sheets_schema import native_execution_registration_v2 as preparation
    from data_sheets_schema import native_shared_contract as contract
    try:
        envelope = preparation.prepare(selection, runtime_declaration, job_id=job_id,
            run_date=run_date.strftime('%Y-%m-%d'), max_draft_checks=max_draft_checks)
        body = envelope['registration']
        spec = body['render_spec']
        if (spec['provider'], spec['reasoning_effort']) != (provider, reasoning_effort):
            raise ValueError('provider and reasoning effort differ from the sole runtime declaration')
        text = body['instruction']
        if out:
            destination = Path(out).absolute()
            if destination != destination.resolve() or destination.is_symlink():
                raise ValueError('instruction output must use its physical path')
            selected = contract.parse_selection(spec['native_shared_generation_registration']['raw_json'].encode('utf-8'))
            stage_root = Path(selected['stage_root'])
            if destination == stage_root or stage_root in destination.parents:
                raise ValueError('instruction output must be outside the mutable native stage root')
            # This is an offline render artifact, never a reservation or admission.
            with destination.open('x', encoding='utf-8') as stream:
                stream.write(text)
    except (OSError, ValueError, UnicodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    raw = text.encode('utf-8')
    click.echo(f'# sha256 {hashlib.sha256(raw).hexdigest()}  ({len(raw)} bytes)', err=True)
    click.echo('# Offline v2 preparation; execution requires separate registration and all admission gates.', err=True)
    if out:
        click.echo(f'✓ {out}', err=True)
    else:
        click.echo(text, nl=False)
