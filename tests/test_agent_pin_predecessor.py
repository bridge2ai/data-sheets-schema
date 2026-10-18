"""Explicit predecessor challenges for separately named agent definitions.

These are offline identity checks, not evidence of live agent behavior.
"""
import hashlib
from pathlib import Path

import pytest

from data_sheets_schema import agent_pin


SHARED = "This stable instruction is shared by both definitions and must never be selected merely because it is long."
FRESH = "Before assigning a score, inspect every stated relationship and preserve any explicit limitation on its supporting evidence."
PREVIOUS = "---\nname: compatibility-agent\n---\n## Procedure\n\n" + SHARED + "\n"
CURRENT = PREVIOUS + "\n" + FRESH + "\n"


def definition(tmp_path, monkeypatch, name, text):
    path = tmp_path / f"{name}.md"
    path.write_text(text, encoding="utf-8")

    def selected(requested):
        assert requested == name
        return path

    monkeypatch.setattr(agent_pin, "agent_path", selected)
    return path


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_new_v4_name_uses_real_released_v3_text_without_same_path_history(tmp_path, monkeypatch, rubric):
    released = Path(__file__).resolve().parents[1] / ".claude" / "agents" / f"d4d-{rubric}-semantic.md"
    predecessor = released.read_text(encoding="utf-8")
    assert "## General context instrument v3" in predecessor
    name = f"d4d-{rubric}-semantic-v4"
    # Public fixture for a new definition: the actual v3 predecessor plus one
    # distinguishable instruction. No live v4 asset or historical registry edit.
    definition(tmp_path, monkeypatch, name, predecessor + "\n## Versioned rule\n\n" + FRESH + "\n")

    def no_invented_history(_name):
        pytest.fail("an explicit predecessor must not consult same-path history")

    monkeypatch.setattr(agent_pin, "_previous_text", no_invented_history)
    ask = agent_pin.challenge(name, predecessor_text=predecessor)
    assert ask == {"expected": FRESH, "prefix": "Before assigning a",
                   "locator": "the section headed “Versioned rule”"}
    assert agent_pin._normalise(ask["expected"]) not in agent_pin._normalise(predecessor)
    preamble = agent_pin.spawn_preamble(name, predecessor_text=predecessor)
    assert agent_pin.agent_digest(name) in preamble
    assert ask["prefix"] in preamble and ask["expected"] not in preamble
    for stale_reply in (predecessor, preamble, ask["prefix"]):
        with pytest.raises(agent_pin.StaleAgentDefinition):
            agent_pin.verify_echo(name, stale_reply, predecessor_text=predecessor)
    agent_pin.verify_echo(name, "Quoted from my instructions: " + FRESH,
                          predecessor_text=predecessor)


def test_explicit_identical_predecessor_cannot_fall_back_to_different_history(tmp_path, monkeypatch):
    definition(tmp_path, monkeypatch, "compatibility-agent", CURRENT)
    monkeypatch.setattr(agent_pin, "_previous_text", lambda name: PREVIOUS)
    assert agent_pin.challenge("compatibility-agent") is not None
    assert agent_pin.challenge("compatibility-agent", predecessor_text=CURRENT) is None
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.spawn_preamble("compatibility-agent", predecessor_text=CURRENT)
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.verify_echo("compatibility-agent", FRESH, predecessor_text=CURRENT)


@pytest.mark.parametrize("predecessor", ["", " \t\n", b"previous definition", 123, False,
                                        Path("previous.md"), [PREVIOUS]])
@pytest.mark.parametrize("operation", ["challenge", "spawn_preamble", "verify_echo"])
def test_invalid_explicit_predecessor_refused_before_definition_or_history(monkeypatch, predecessor, operation):
    def forbidden(*args):
        pytest.fail("invalid supplied text must not trigger definition/history resolution")

    monkeypatch.setattr(agent_pin, "_previous_text", forbidden)
    monkeypatch.setattr(agent_pin, "agent_path", forbidden)
    args = ("unused", "reply") if operation == "verify_echo" else ("unused",)
    with pytest.raises(ValueError, match="predecessor_text must be nonblank text"):
        getattr(agent_pin, operation)(*args, predecessor_text=predecessor)


def test_default_history_and_preamble_bytes_remain_exactly_compatible(tmp_path, monkeypatch):
    definition(tmp_path, monkeypatch, "compatibility-agent", CURRENT)
    calls = []

    def history(name):
        calls.append(name)
        return PREVIOUS

    monkeypatch.setattr(agent_pin, "_previous_text", history)
    assert agent_pin.challenge("compatibility-agent") == {
        "expected": FRESH, "prefix": "Before assigning a",
        "locator": "the section headed “Procedure”"}
    preamble = agent_pin.spawn_preamble("compatibility-agent")
    # Captured with unmodified agent_pin.py on main20f694145 before this change.
    assert hashlib.sha256(preamble.encode()).hexdigest() == "d2ab82203201f81fa33f763a79aae4b6fcdcb8303b6497c77abbb8bfe8c1c47a"
    assert agent_pin.spawn_preamble("compatibility-agent", predecessor_text=None) == preamble
    agent_pin.verify_echo("compatibility-agent", FRESH)
    with pytest.raises(agent_pin.StaleAgentDefinition):
        agent_pin.verify_echo("compatibility-agent", preamble)
    assert calls == ["compatibility-agent"] * 5


def test_missing_default_history_still_refuses_without_an_explicit_predecessor(tmp_path, monkeypatch):
    definition(tmp_path, monkeypatch, "compatibility-agent", CURRENT)
    monkeypatch.setattr(agent_pin, "_previous_text", lambda name: None)
    assert agent_pin.challenge("compatibility-agent") is None
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.spawn_preamble("compatibility-agent")
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.verify_echo("compatibility-agent", FRESH)
    assert agent_pin.challenge("compatibility-agent", predecessor_text=PREVIOUS)["expected"] == FRESH
