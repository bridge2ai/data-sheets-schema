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

**The answer must not be in the question.** The first version of this printed
the challenge sentence in the preamble and asked for it back, so an agent that
copied the preamble passed — including the stale one the mechanism exists to
catch (#1102). A check whose expected answer is visible to the answerer is a
compliance check on the prompt, not evidence about the definition.

So the preamble carries a **locator** — a heading in the definition — and the
verifier alone holds the **expected** text under it. An agent handed the old
definition finds different prose there and cannot produce it.

    ask = spawn_preamble("d4d-rubric10-semantic")   # prepend to the task
    ...
    verify_echo("d4d-rubric10-semantic", reply)     # raises if stale

**The expected text must come from what changed, and be checked absent from
the previous version.** Taking the longest line failed the decisive replay of
the real incident (`8813c8e6` against `119e3171`): it was a shared paragraph
about model identity. Taking a line the last change touched is not enough
either — a reformat "changes" a line that both versions carry. So a challenge
is built only where the chosen text is **verifiably absent from the
pre-image**, and `discriminates()` reports whether that holds rather than
whether a diff was non-empty (#1102).

**The question and the answer are the same unit.** The second version asked
for the section's longest *sentence* and verified the longest fresh *line*
(#1145): on the review-record definition the sentence carrying that line
ranked 2nd of 38 by length, so an agent that did exactly as asked was told
to stop. The challenge is now a sentence, and the preamble names it by its
opening words — enough to find it in its section, never enough to answer.
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

#: Where one sentence ends and the next begins, in prose joined across the
#: wrapped lines of a paragraph: a terminator, optionally a closing bracket
#: or quote, whitespace, then an opening capital, quote, backtick or bracket
#: (#1149 review, S2: `.)` and `.”` used to merge two sentences into one).
_SENTENCE_END = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][)\]\u201d\"'`]))\s+(?=[A-Z\u201c\"'`(])")

#: Abbreviations a sentence does not end at (S3): protected before the split.
_ABBREVIATIONS = ("e.g.", "i.e.", "cf.", "vs.", "etc.", "Fig.", "No.", "Dr.", "Mr.", "Ms.", "approx.")

#: A sentence starts with a capital, a quote, a backtick, a bracket or a
#: digit. A fragment that starts lower-case — text after a bullet list broke
#: a paragraph, or after an unlisted abbreviation — is not something an
#: agent can be asked for (S3).
_SENTENCE_START = re.compile(r"^[A-Z0-9\u201c\"'`(\[]")

#: The fewest opening words of the expected sentence the preamble reveals.
#: Enough to point at one sentence in its section; never the sentence.
MIN_PREFIX_WORDS = 3


class StaleAgentDefinition(RuntimeError):
    """A subagent did not quote text unique to the definition on disk."""


class NoDiscriminatingChallenge(RuntimeError):
    """Nothing in this definition is absent from the previous version.

    Raised rather than silently weakening the challenge: a check that cannot
    fail is worse than no check, because it is reported as a pass (#1102).
    """


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
    nothing; short lines are echoed by chance; a fenced block is a template
    every version carries. Kept as the line-level form the replay test of
    the first rule uses; the challenge itself is built from sentences.
    """
    out, fenced = [], False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and len(stripped) >= MIN_CHALLENGE and not _SKIP.match(stripped):
            out.append(stripped)
    return out


def _git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          cwd=REPO).stdout


def _previous_text(name: str) -> str | None:
    """The definition as it stood before the most recent change to it.

    Two cases, in order. An uncommitted edit — the case #1077 is about, an
    edit made and a subagent spawned before it is committed — compares against
    HEAD; `git diff HEAD` rather than `git diff`, so a staged edit is still
    seen (#1102). Otherwise the parent of the last commit that *touched this
    file*, found with `git log -n1 -- <path>`; asking whether the last commit
    of the repository touched it is a one-commit window that goes blind the
    moment anything else is committed, which left the mechanism inert for all
    twelve definitions.
    """
    rel = str(agent_path(name).relative_to(REPO))
    if _git("diff", "HEAD", "--name-only", "--", rel).strip():
        blob = _git("show", f"HEAD:{rel}")
        return blob or None
    commit = _git("log", "-n1", "--format=%H", "--", rel).strip()
    if not commit:
        return None
    parent = _git("rev-parse", f"{commit}^").strip()
    if not parent:
        return None
    return _git("show", f"{parent}:{rel}") or None



def sentences_by_section(body: str) -> list[tuple[str | None, str]]:
    """(heading, sentence) for every prose sentence of the definition, in
    order: wrapped lines of a paragraph joined, then split at sentence ends.
    Bulleted, numbered, quoted, tabular and fenced lines are left out, as
    `_usable` leaves them out of the line form — they recur across versions.
    """
    out: list[tuple[str | None, str]] = []
    heading: str | None = None
    para: list[str] = []
    fenced = False

    def flush() -> None:
        if para:
            text = re.sub(r"\s+", " ", " ".join(para)).replace("*", "").strip()
            for abbr in _ABBREVIATIONS:
                text = text.replace(abbr + " ", abbr + "\x00")
            for sent in _SENTENCE_END.split(text):
                sent = sent.replace("\x00", " ").strip()
                if sent:
                    out.append((heading, sent))
            para.clear()

    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            fenced = not fenced                  # a code block is a template, not prose
            flush()
            continue
        if fenced:
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("# ").strip()
            continue
        if _SKIP.match(stripped):
            flush()
            continue
        para.append(stripped)
    flush()
    return out


def _prefix_for(expected: str, siblings: list[str]) -> str | None:
    """The fewest opening words (at least `MIN_PREFIX_WORDS`) that begin
    `expected` and no other sentence of its section — what the preamble
    reveals so an agent can find the sentence without being handed it.
    None when no prefix strictly shorter than the sentence is unique: a
    sibling that shares every word but the last would otherwise make the
    prefix the answer, and the check could no longer fail (#1149 review,
    M1 — the #1102 property, re-created silently)."""
    words = expected.split()
    others = [_normalise(sib) for sib in siblings if sib != expected]
    for n in range(MIN_PREFIX_WORDS, len(words)):
        prefix = " ".join(words[:n])
        if not any(o.startswith(_normalise(prefix)) for o in others):
            return prefix
    return None


def challenge_between(body: str, previous: str) -> dict[str, str] | None:
    """The challenge a given pair of versions supports, as a pure function.

    Separated from the git plumbing so the decisive property — that the
    expected text is absent from the version a stale agent would hold — can be
    replayed against any two texts, including the real #1077 commits.

    The unit is a **sentence**, and the preamble names it by its opening
    words (#1145): the first version asked the agent for the section's
    longest sentence while holding the longest fresh *line*, and on a long
    section an agent that answered exactly as asked was told it was stale
    (the sentence carrying the fresh line ranked 2nd of 38). What the
    preamble asks for and what the verifier holds are now the same thing,
    and the opening words point at it without reproducing it.
    """
    old = _normalise(previous)
    sents = sentences_by_section(body)
    fresh = [(h, sent) for h, sent in sents
             if len(sent) >= MIN_CHALLENGE and _SENTENCE_START.match(sent)
             and _normalise(sent) not in old]
    # Longest first; the first fresh sentence that can be named by a prefix
    # shorter than itself is the challenge. A sentence that cannot be is
    # skipped rather than revealed (M1).
    for heading, expected in sorted(fresh, key=lambda hs: -len(hs[1])):
        siblings = [sent for h, sent in sents if h == heading]
        prefix = _prefix_for(expected, siblings)
        if prefix is None:
            continue
        return {"expected": expected, "prefix": prefix,
                "locator": (f"the section headed \u201c{heading}\u201d" if heading
                            else "your scoring instructions")}
    return None


def challenge(name: str) -> dict[str, str] | None:
    """A locator to put in the prompt and the answer to keep out of it.

    Returns `{"locator": …, "expected": …}`, or None when no text in the
    current definition can be shown absent from the previous one — in which
    case there is no honest challenge to make, and callers must say so rather
    than fall back to something weaker (#1102).
    """
    previous = _previous_text(name)
    if previous is None:
        return None
    return challenge_between(_body(name), previous)


def discriminates(name: str) -> bool:
    """Whether a challenge exists whose answer the previous version lacks."""
    return challenge(name) is not None


_FOLD = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
                       "\u2014": "-", "\u2013": "-", "*": "", "`": ""})


def _normalise(text: str) -> str:
    """Whitespace, case, emphasis markers, backticks and the typographic
    forms of quotes and dashes do not decide a match: an agent quoting half
    a kilobyte verbatim may straighten a quote or retype an em dash, and a
    stale definition is a different claim from a dropped backtick (#1149
    review, S4)."""
    text = text.translate(_FOLD).replace("--", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def spawn_preamble(name: str) -> str:
    """Text to prepend to a spawn prompt so the reply is evidence.

    Raises `NoDiscriminatingChallenge` when the definition carries nothing the
    previous version lacked: there is then no question only the current text
    can answer, and issuing one anyway would produce a `✓` that means nothing.
    """
    ask = challenge(name)
    if ask is None:
        raise NoDiscriminatingChallenge(
            f"{name}: nothing in this definition is absent from the previous "
            "version, so no reply can distinguish them. Do not claim the "
            "subagent's definition was verified (#1102).")
    return (
        f"Before the task: your definition on disk is `{name}.md`, sha256 "
        f"`{agent_digest(name)}`.\n\n"
        "An agent-definition edit does not always reach a subagent spawned "
        "afterwards (#1077), and when it does not, nothing in the output says "
        "so — the run silently applies the old rules. So, first, find "
        f"{ask['locator']} in your own instructions, and quote back "
        f"**verbatim and in full** the sentence there that begins "
        f"\u201c{ask['prefix']}\u201d. The rest of the sentence is deliberately "
        "not reproduced here: if it were, copying this prompt would pass the "
        "check and prove nothing.\n\n"
        "If you cannot find that section, or it reads differently from what "
        "you would expect of the current rules, say so plainly and **stop "
        "rather than proceeding** — your definition is stale and any result "
        "would measure the previous instrument. Record the sha256 above as "
        "`instrument_sha256` in your output (#1099)."
    )


def verify_echo(name: str, reply: str) -> None:
    """Raise unless the reply quotes text the previous definition lacked."""
    ask = challenge(name)
    if ask is None:
        raise NoDiscriminatingChallenge(
            f"{name}: nothing distinguishes this definition from the previous "
            "one, so this reply cannot be verified either way (#1102).")
    if _normalise(ask["expected"]) not in _normalise(reply):
        raise StaleAgentDefinition(
            f"{name}: the reply does not quote the sentence beginning "
            f"\u201c{ask['prefix']}\u201d under {ask['locator']} "
            f"from the definition on disk (sha256 {agent_digest(name)[:12]}…). "
            "Either the subagent received a stale definition (#1077) or it did "
            "not follow the preamble; in both cases the result cannot be read "
            "as measuring the current instrument.")


def echoed(name: str, reply: str) -> bool:
    """`verify_echo` as a predicate, for callers that tally rather than fail.

    False for a definition with no discriminating challenge too: "cannot be
    verified" is not "verified".
    """
    try:
        verify_echo(name, reply)
    except (StaleAgentDefinition, NoDiscriminatingChallenge):
        return False
    return True
