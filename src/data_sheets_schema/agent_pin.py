"""Prove which text a subagent actually received (#1077).

On 2026-09-08 the Element 8 software threshold was written into
`.claude/agents/d4d-rubric10-semantic.md`, verified on disk, and a subagent
spawned afterwards reported the **pre-edit** criteria back verbatim. Earlier
the same session a different batch did pick up mid-session edits. So the
staleness is intermittent, which is worse than consistent: a rescore can
silently measure the old instrument, and nothing in its output says so.

**Why a hash is not enough.** #1099 has evaluations record
`instrument_sha256`. That makes a score's instrument nameable, and it is
worth having — but it cannot detect this defect, because the agent computes
that hash by reading the file *from disk*, which is current, while the
definition it was given may be stale. The two come from different places, so
they agree even when the run is wrong.

**What does work is a challenge the stale text cannot answer.** Take a
sentence that exists only in the current definition, ask the agent to quote
it back, and check the answer. An agent that received the old text cannot
produce it, and — as the evaluator that caught #1077 did unprompted — will
usually say so.

    preamble = spawn_preamble("d4d-rubric10-semantic")   # prepend to the task
    ...
    verify_echo("d4d-rubric10-semantic", reply)          # raises if stale

**The challenge must come from what changed, not from what is longest.** The
first version of this took the longest line of the definition and failed its
own decisive test: replayed against the real #1077 incident — the pre-edit
text at `8813c8e6` against the post-edit text at `119e3171` — the longest
line was a paragraph about model identity that both versions shared, so the
stale agent would have echoed it happily. The challenge is therefore drawn
from the lines the **most recent change to the file added**, which is exactly
the text a stale definition lacks. That is checked by a test that replays
those two commits.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO / ".claude" / "agents"

#: Short lines make weak challenges: headings and list markers recur across
#: versions, so echoing one proves nothing about which text was received.
MIN_CHALLENGE = 60

#: A line that is boilerplate rather than instrument: present in every
#: version, so useless as a discriminator.
_SKIP = re.compile(r"^\s*(?:[-*+]\s|\d+\.\s|#|\||```|>)")


class StaleAgentDefinition(RuntimeError):
    """A subagent did not echo the challenge from the definition on disk."""


def agent_path(name: str) -> Path:
    path = AGENT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"no agent definition at {path}")
    return path


def agent_digest(name: str) -> str:
    """sha256 of the definition as it stands on disk."""
    return hashlib.sha256(agent_path(name).read_bytes()).hexdigest()


def _body(name: str) -> str:
    """The definition below its YAML frontmatter."""
    text = agent_path(name).read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[2] if len(parts) > 2 else text


def _usable(lines):
    """Prose lines long enough that echoing one cannot be luck.

    Headings and list markers recur across versions, so they discriminate
    nothing; short lines are echoed by chance.
    """
    return [ln.strip() for ln in lines
            if len(ln.strip()) >= MIN_CHALLENGE and not _SKIP.match(ln.strip())]


def _added_lines(name: str) -> list[str]:
    """Lines the most recent change to the definition added.

    Uncommitted edits first — that is the case #1077 is about, an edit made
    and a subagent spawned before it is committed. Otherwise the last commit
    that touched the file. Empty when git knows nothing about it.
    """
    path = agent_path(name)
    rel = path.relative_to(REPO)
    for args in (["git", "diff", "--unified=0", "--", str(rel)],
                 ["git", "diff", "--unified=0", "HEAD~1", "HEAD", "--", str(rel)]):
        out = subprocess.run(args, capture_output=True, text=True,
                             cwd=REPO).stdout
        added = [ln[1:] for ln in out.splitlines()
                 if ln.startswith("+") and not ln.startswith("+++")]
        if _usable(added):
            return added
    return []


def challenge(name: str) -> str:
    """A sentence the current definition has and the previous one did not.

    Drawn from the lines the most recent change added, because that is
    precisely the text a stale definition lacks. Falls back to the longest
    line of the body when the file has no history to diff — a weaker
    challenge, and the docstring of `spawn_preamble` says so.
    """
    added = _usable(_added_lines(name))
    if added:
        return max(added, key=len)
    usable = _usable(_body(name).splitlines())
    if not usable:
        raise ValueError(f"{name}: no line of {MIN_CHALLENGE}+ characters to "
                         "challenge on")
    return max(usable, key=len)


def challenge_is_from_a_change(name: str) -> bool:
    """Whether the challenge discriminates against the previous version."""
    return bool(_usable(_added_lines(name)))


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def spawn_preamble(name: str) -> str:
    """Text to prepend to a spawn prompt so the reply proves what was read."""
    return (
        f"Before the task: your definition on disk is `{name}.md`, sha256 "
        f"`{agent_digest(name)}`.\n\n"
        "An agent-definition edit does not always reach a subagent spawned "
        "afterwards (#1077), and when it does not, nothing in the output says "
        "so — the run silently applies the old rules. So, first, quote back "
        "the following sentence from your own instructions **verbatim**:\n\n"
        f"    {challenge(name)}\n\n"
        "If the sentence is not in the instructions you were given, say so "
        "plainly and stop rather than proceeding: your definition is stale "
        "and any result would measure the previous instrument. Record the "
        "sha256 above as `instrument_sha256` in your output (#1099)."
    )


def verify_echo(name: str, reply: str) -> None:
    """Raise unless the reply contains the current definition's challenge."""
    if _normalise(challenge(name)) not in _normalise(reply):
        raise StaleAgentDefinition(
            f"{name}: the reply does not quote the challenge sentence from the "
            f"definition on disk (sha256 {agent_digest(name)[:12]}…). Either "
            "the subagent received a stale definition (#1077) or it did not "
            "follow the preamble; in both cases the result cannot be read as "
            "measuring the current instrument.")


def echoed(name: str, reply: str) -> bool:
    """`verify_echo` as a predicate, for callers that tally rather than fail."""
    try:
        verify_echo(name, reply)
    except StaleAgentDefinition:
        return False
    return True
