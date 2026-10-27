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
              help="Sole explicit runtime declaration; read and checked without invoking the runtime.")
@click.option("--provider", required=True, help="Must equal the sole runtime declaration.")
@click.option("--reasoning-effort", required=True, help="Must equal the sole runtime declaration.")
@click.option("--max-draft-checks", required=True, type=click.IntRange(min=1),
              help="Explicit allowance to use again when composing and registering the execution.")
@click.option("--run-date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Explicit date written into the instruction, YYYY-MM-DD.")
@click.option("--out", type=click.Path(dir_okay=False),
              help="Write a new instruction file; an existing file is refused.")
def render_native_shared(selection, runtime_declaration, provider, reasoning_effort,
                         max_draft_checks, run_date, out):
    """Render the selected native instruction offline. This does not authorize a launch."""
    from pathlib import Path
    import hashlib

    from data_sheets_schema.api_runner import RunSpec
    from data_sheets_schema import native_shared_contract as contract
    from data_sheets_schema.native_shared_selection import capture
    from data_sheets_schema.native_shared_controller import bind_runtime

    try:
        captured = capture(selection)
        document = captured.document()
        inputs = document['inputs']
        if inputs['source_manifest'] is None:
            raise ValueError('native shared rendering requires an explicit source manifest')
        manifest = inputs['source_manifest']['path']
        spec = RunSpec(**document['run'], condition=contract.CONDITION,
            render_version=contract.RENDERER, runtime=contract.RUNTIME,
            bundle=Path(inputs['bundle']['path']), manifest=Path(manifest),
            chunk_manifest=Path(inputs['chunk_manifest']['path']),
            manifest_line=f'# Source manifest: {manifest}',
            profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
            provider=provider, reasoning_effort=reasoning_effort,
            run_date=run_date.strftime('%Y-%m-%d'), prompt_text_env=True,
            native_shared_generation_version=1,
            native_shared_generation_registration=captured.registration.raw.decode('utf-8'))
        bind_runtime(spec, runtime_declaration, max_draft_checks)
        text = spec.instruction
        if out:
            destination = Path(out).resolve()
            stage_root = Path(document['stage_root'])
            if destination == stage_root or stage_root in destination.parents:
                raise ValueError('the instruction must be outside the mutable native stage root')
            with destination.open('x', encoding='utf-8') as stream:
                stream.write(text)
    except (OSError, ValueError, UnicodeError) as exc:
        raise click.ClickException(str(exc)) from exc
    raw = text.encode('utf-8')
    click.echo(f'# sha256 {hashlib.sha256(raw).hexdigest()}  ({len(raw)} bytes)', err=True)
    click.echo('# Offline rendering only; execution still requires its separate registration and acceptance gates.', err=True)
    if out:
        click.echo(f'✓ {out}', err=True)
    else:
        click.echo(text, nl=False)
