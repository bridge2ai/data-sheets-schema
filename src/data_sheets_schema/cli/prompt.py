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
