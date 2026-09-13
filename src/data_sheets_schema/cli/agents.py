"""`d4d agents` — prove which definition a subagent was given (#1077)."""
import click

from data_sheets_schema.agent_pin import (AGENT_DIR,
                                          NoDiscriminatingChallenge,
                                          StaleAgentDefinition, agent_digest,
                                          discriminates, spawn_preamble,
                                          verify_echo)


def _names():
    from pathlib import Path
    from data_sheets_schema.agentic_runtime import resource_names
    # Project-local agents are allowed, but do not hide shipped D4D agents.
    names = {Path(name).stem for name in resource_names(".claude/agents")}
    names.update(path.stem for path in Path(".claude/agents").glob("*.md"))
    return sorted(names)


@click.group()
def agents():
    """Agent definitions: their pins, and whether a subagent read them."""


@agents.command("playbook")
def playbook():
    """Print the agentic playbook with executable installed resource paths."""
    from data_sheets_schema.agentic_runtime import playbook_text
    click.echo(playbook_text())


@agents.command("preamble")
@click.option("--agent", required=True, help="agent name, without .md")
def preamble(agent):
    """Print the text to prepend to a spawn prompt.

    An agent-definition edit does not always reach a subagent spawned
    afterwards, and when it does not the run silently applies the old rules.
    The preamble names a *section* of the definition and asks the agent to
    quote the sentence beginning with the words it names, in full; the rest
    of the sentence is withheld, so copying
    the prompt does not pass (#1102). Exits non-zero when the definition
    carries nothing the previous version lacked, rather than issuing a
    question that cannot fail.
    """
    if agent not in _names():
        raise click.BadParameter(f"unknown agent; have: {', '.join(_names())}")
    try:
        click.echo(spawn_preamble(agent))
    except NoDiscriminatingChallenge as exc:
        raise SystemExit(str(exc))


@agents.command("check-echo")
@click.option("--agent", required=True)
@click.option("--reply", required=True,
              help="the subagent's reply, or - to read stdin")
def check_echo(agent, reply):
    """Exit non-zero unless the reply quotes the current definition."""
    text = click.get_text_stream("stdin").read() if reply == "-" else reply
    try:
        verify_echo(agent, text)
    except (StaleAgentDefinition, NoDiscriminatingChallenge) as exc:
        raise SystemExit(str(exc))
    click.echo(f"✓ {agent}: the reply quotes the definition on disk "
               f"({agent_digest(agent)[:12]}…)")


@agents.command("digest")
@click.option("--agent", default=None, help="one agent; omit for all")
def digest(agent):
    """The sha256 an evaluation should record as `instrument_sha256`."""
    for name in ([agent] if agent else _names()):
        mark = "" if discriminates(name) else "  (nothing unique to challenge on)"
        click.echo(f"{agent_digest(name)}  {name}{mark}")
