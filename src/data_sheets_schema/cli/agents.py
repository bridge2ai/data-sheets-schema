"""`d4d agents` — prove which definition a subagent was given (#1077)."""
import click

from data_sheets_schema.agent_pin import (AGENT_DIR, StaleAgentDefinition,
                                          agent_digest, challenge,
                                          challenge_is_from_a_change,
                                          spawn_preamble, verify_echo)


def _names():
    return sorted(p.stem for p in AGENT_DIR.glob("*.md"))


@click.group()
def agents():
    """Agent definitions: their pins, and whether a subagent read them."""


@agents.command("preamble")
@click.option("--agent", required=True, help="agent name, without .md")
def preamble(agent):
    """Print the text to prepend to a spawn prompt.

    An agent-definition edit does not always reach a subagent spawned
    afterwards, and when it does not the run silently applies the old rules.
    The preamble asks the agent to quote back a sentence the current
    definition has and the previous one did not, so the reply is evidence of
    what it read.
    """
    if agent not in _names():
        raise click.BadParameter(f"unknown agent; have: {', '.join(_names())}")
    click.echo(spawn_preamble(agent))
    if not challenge_is_from_a_change(agent):
        click.echo("\n⚠️  This definition has no recent change to draw a "
                   "challenge from, so the sentence above also appears in the "
                   "previous version: echoing it proves the agent read *a* "
                   "definition, not that it read this one.", err=True)


@agents.command("check-echo")
@click.option("--agent", required=True)
@click.option("--reply", required=True,
              help="the subagent's reply, or - to read stdin")
def check_echo(agent, reply):
    """Exit non-zero unless the reply quotes the current definition."""
    text = click.get_text_stream("stdin").read() if reply == "-" else reply
    try:
        verify_echo(agent, text)
    except StaleAgentDefinition as exc:
        raise SystemExit(str(exc))
    click.echo(f"✓ {agent}: the reply quotes the definition on disk "
               f"({agent_digest(agent)[:12]}…)")


@agents.command("digest")
@click.option("--agent", default=None, help="one agent; omit for all")
def digest(agent):
    """The sha256 an evaluation should record as `instrument_sha256`."""
    for name in ([agent] if agent else _names()):
        mark = "" if challenge_is_from_a_change(name) else "  (no recent change)"
        click.echo(f"{agent_digest(name)}  {name}{mark}")
