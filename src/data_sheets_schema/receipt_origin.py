"""Receipt origin (#2933): which coverage-receipt snippets were written while
reading, and which after the draft existed. Read from the run's transcript;
report-only.

On the native and direct arms the receipt is written chunk by chunk as the
bundle is read, and only then extracted into the record (d4d-full-core
Phase 1, steps 3–4). Three routes let a run change it after the full record
exists: the Phase 1 correction clause, renderer 13's NATIVE_PHASE1_RECEIPTS
("including adding or removing extracted assertions") and the Phase 3
back-port. `receipts check` reads the final receipt only, and the agentic
path keeps no phase-1 snapshot (`receipts.phase1_snapshot`), so the API
arm's #807 split has no equivalent there. This module rebuilds the
receipt's history from the run's own tool calls and classifies each final
(chunk, snippet, slot) element by its (chunk, snippet):

- `contemporaneous` — in the receipt as it stood at the first successful
  Write of the full record;
- `phase1_correction` — added after that, and present when the first
  successful `derive core` of that record ran;
- `phase3_backport` — added after that derivation.

With no successful derive the Phase 1 window runs to the end of the
transcripts: every element added after the draft is a `phase1_correction`,
there is no derive-time snapshot, and the block reports `draft_to_final`
where the two derive-core deltas would be.

The comparison is between those three snapshots as multisets: a duplicated
final triple counts twice, and one added and removed between snapshots is
not counted. `readdressed` counts contemporaneous elements whose slot
changed; `removed_contemporaneous` counts pre-draft elements the final
receipt no longer carries. Which slot each listed entry names is a function
of the three multisets, never of the receipt's order: a final slot the
pre-draft snapshot carried is contemporaneous, the slots the derive-time
snapshot added are preferred as the Phase 1 ones, and the re-addressed and
Phase 3 labels then go in slot order.

Only a successful Write, paired with its tool_result by id, changes state.
A Write the runtime refused (the unread-file wrapper, #2285) or that
returned an error is listed and changes nothing, and so is a shell call
the native control denied: it never ran (#3185). A `derive core` succeeded
only where its call's result carries the derive's own status (#3113). With
every join in the command `&&` or `;`, the call's success or failure is the
derive's when the derive is the last part, and its success alone is when
every join after the derive is `&&` (a failure may be a later part's).
Otherwise (piped, backgrounded, grouped, after `||`, followed by `;`, in a
multi-line command, or a failed `&&` chain) the derive is ambiguous, unless
the native control denied the call, which then never ran. A call the runtime
backgrounded is ambiguous too: its result is the launch, not the end. A
shell command is read as bash reads it: `#` starts a comment only at the
start of a word, outside quotes (#3184).

The status is `unknown`, with every reason, and no classification is
reported when the history cannot be rebuilt: a transcript is missing,
unreadable or malformed; a tool id is duplicated or a result has no call
(#2077); a Write of the receipt, or of the full record before its first
successful Write, has no result or no success evidence; the receipt is
changed by anything other than a Write (an edit tool, or a shell command
that names it, is not known to be read-only and was not denied by the
native control) where the change can reach
the pre-draft or derive-time snapshot, or the full record is changed that
way before its first Write; the first observed Write of either file updated
an existing file, or carries no create/update metadata to say it did not; a
`derive core` of the full record cannot be placed; or the rebuilt final
receipt's sha256 differs from the file on disk. A non-Write change issued
after the last receipt Write, the draft and the derive boundary had all
returned can reach only the final receipt, which the sha256 comparison
covers: it is listed with `covered_by_final_sha256` and is not a reason.
Nothing is ever reported as contemporaneous on incomplete evidence.

The output carries counts, chunk ids, slot paths and sha256 digests, never
snippet text or tool payloads: transcripts hold model output.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

INSTRUMENT = "receipt_origin v1 (#2933)"
ORIGINS = ("contemporaneous", "phase1_correction", "phase3_backport")

#: The native runtime's refusal to overwrite a file the session has not read
#: (#2285), as the pinned `native_control.UNREAD_WRITE_MESSAGE` names it.
UNREAD_WRITE_ERROR = ("<tool_use_error>File has not been read yet. "
                      "Read it first before writing to it.</tool_use_error>")

#: Tools that only read. Any other tool given a path that names a tracked
#: file (Edit, MultiEdit, NotebookEdit, ...) changes it other than by a Write.
READ_TOOLS = frozenset({"Read", "Grep", "Glob", "LS", "NotebookRead"})
#: Shell programs that read their operands and write only to stdout (`sed`
#: without an in-place flag). Anything else that names a tracked file is a
#: possible mutation.
READ_ONLY_PROGRAMS = frozenset({"cat", "head", "tail", "grep", "egrep", "fgrep", "rg", "wc", "ls",
                                "stat", "file", "md5", "md5sum", "shasum", "sha256sum", "cmp",
                                "diff", "nl", "sed", "echo", "printf", "pwd", "true", "test", "["})
#: `d4d` subcommands that write neither the receipt nor the full record
#: (unless an `--out` names one). `provenance record` writes only
#: `{project}_provenance.yaml` and the check blocks inside it (cli/provenance.py
#: `record`, `backfill_checks.apply`); the playbook's recorder line names the
#: receipt in its `--phase` and `--render-spec-json` values (#3112).
READ_ONLY_D4D = frozenset({("receipts", "check"), ("receipts", "invert"), ("receipts", "origin"),
                           ("derive", "core"), ("provenance", "record")})

#: The pinned native control's PreToolUse denial reason
#: (`native_control.hook_output`): a call answered with it never ran.
NATIVE_DENIAL_PREFIX = "Outside the registered tool policy: "
#: Joins between the parts of a shell command after which the command's own
#: status can still be the derive's (#3113).
_SEQUENTIAL = frozenset({"&&", ";"})

NON_CHECKS = (
    "that a contemporaneous snippet supports the value it sits under (#2067: post-draft "
    "snippets stay unaccepted for semantic support until independent review)",
    "a shell write that names the receipt only through a glob or variable, before the last "
    "Write (one after it is caught by the final sha256)",
)

_ABSENT = object()
_LABEL = {"receipt": "receipt", "full": "full record"}
_OPERATORS = frozenset({"&&", "||", ";", "|", "&", "|&", "(", ")", ";;", ";&"})
_PUNCT = frozenset("();<>|&")
_CLEAN_PATH = re.compile(r"[A-Za-z0-9_./+@-]+")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
_PYTHON = re.compile(r"python(\d+(\.\d+)*)?")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- targets
class _Target:
    """A tracked file, matched by its absolute spelling or its real path."""

    def __init__(self, kind: str, path: Path):
        self.kind, self.path = kind, Path(path)
        self.name = self.path.name
        self.forms = {os.path.normpath(os.path.abspath(path)), os.path.realpath(path)}

    def matches(self, spelled: str, cwd: str | None) -> bool | None:
        """Whether a path as the transcript spells it is this file; None when
        a relative spelling has no working directory to resolve against."""
        if not os.path.isabs(spelled):
            if cwd is None:
                return None
            spelled = os.path.join(cwd, spelled)
        spelled = os.path.normpath(spelled)
        return spelled in self.forms or os.path.realpath(spelled) in self.forms


# ---------------------------------------------------------------- transcripts
def _load(paths: list[Path], reasons: list[str]) -> tuple[list[dict], list[tuple[int, int, dict]]]:
    """Every transcript's events with their physical line numbers. A missing,
    unreadable, empty, blank-lined, truncated or non-JSON transcript is a
    reason, never repaired."""
    info: list[dict] = []
    events: list[tuple[int, int, dict]] = []
    for t, path in enumerate(paths):
        entry: dict[str, Any] = {"path": str(path), "sha256": None, "lines": None}
        info.append(entry)
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            reasons.append(f"transcript {t} cannot be read ({type(exc).__name__})")
            continue
        entry["sha256"] = _sha256(data)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            reasons.append(f"transcript {t} is not UTF-8")
            continue
        lines = text.split("\n")
        terminated = lines[-1] == ""
        if terminated:
            lines.pop()
        entry["lines"] = len(lines)
        if not lines:
            reasons.append(f"transcript {t} carries no events")
            continue
        bad: list[str] = []
        for n, line in enumerate(lines, 1):
            if not line.strip():
                bad.append(f"line {n} is blank")
                continue
            if n == len(lines) and not terminated:
                bad.append(f"line {n} is unterminated")
                continue
            try:
                event = json.loads(line)
            except ValueError:
                bad.append(f"line {n} is not JSON")
                continue
            if not isinstance(event, dict):
                bad.append(f"line {n} is not a JSON object")
                continue
            events.append((t, n, event))
        if bad:
            reasons.append(f"transcript {t} has {len(bad)} malformed line(s), first: {bad[0]}")
    return info, events


def _pair(events: list[tuple[int, int, dict]], reasons: list[str]) -> tuple[list[dict], dict[str, dict]]:
    """Tool calls in order and their results by id. A duplicated call id makes
    every call under it ambiguous (#2077), a result with no earlier call is
    foreign evidence, and a second result for one call is ambiguous."""
    calls: list[dict] = []
    by_id: dict[str, dict] = {}
    results: dict[str, dict] = {}
    duplicated: set[str] = set()
    malformed: list[str] = []
    cwd_of: dict[int, str] = {}
    for t, n, event in events:
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and isinstance(event.get("cwd"), str):
            cwd_of[t] = event["cwd"]
        if kind not in ("assistant", "user"):
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            malformed.append(f"transcript {t} line {n}: {kind} event without a message mapping")
            continue
        content = message.get("content")
        if content is None or isinstance(content, str):
            continue
        if not isinstance(content, list):
            malformed.append(f"transcript {t} line {n}: message content is not a list")
            continue
        cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else cwd_of.get(t)
        blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
        # Result metadata is per event: it describes a result only when the
        # event carries exactly one.
        metadata = (event.get("tool_use_result", event.get("toolUseResult", _ABSENT))
                    if len(blocks) == 1 else _ABSENT)
        for block in content:
            if not isinstance(block, dict):
                malformed.append(f"transcript {t} line {n}: a content block is not a mapping")
                continue
            if block.get("type") == "tool_use":
                identity = block.get("id")
                if kind != "assistant" or not isinstance(identity, str) or not identity:
                    malformed.append(f"transcript {t} line {n}: tool call without an id or outside an assistant event")
                    continue
                if identity in by_id:
                    duplicated.add(identity)
                    continue
                call = {"id": identity, "name": block.get("name"), "input": block.get("input"),
                        "transcript": t, "line": n, "pos": len(calls), "cwd": cwd}
                calls.append(call)
                by_id[identity] = call
            elif block.get("type") == "tool_result":
                identity = block.get("tool_use_id")
                if kind != "user" or not isinstance(identity, str):
                    malformed.append(f"transcript {t} line {n}: tool result without an id or outside a user event")
                    continue
                if identity not in by_id:
                    malformed.append(f"transcript {t} line {n}: tool result with no earlier call")
                    continue
                if identity in results:
                    duplicated.add(identity)
                    continue
                results[identity] = {"is_error": block.get("is_error", _ABSENT),
                                     "content": block.get("content"), "metadata": metadata,
                                     "transcript": t, "line": n}
    if duplicated:
        reasons.append(f"{len(duplicated)} tool id(s) are duplicated: {', '.join(sorted(duplicated)[:5])}")
    if malformed:
        reasons.append(f"{len(malformed)} malformed tool event(s), first: {malformed[0]}")
    return calls, results


def _outcome(result: dict | None) -> str:
    """`succeeded`, `rejected`, `pending` or `ambiguous`, for a file tool.
    Success is an explicit `is_error: false`, or no error flag with the
    runtime's own result metadata beside it (#2077). An error whose
    metadata says the file was written contradicts itself."""
    if result is None:
        return "pending"
    flag, metadata = result["is_error"], result["metadata"]
    if flag is True:
        wrote = isinstance(metadata, dict) and metadata.get("type") in ("create", "update")
        return "ambiguous" if wrote else "rejected"
    if flag is False or (flag is _ABSENT and isinstance(metadata, dict)):
        return "succeeded"
    return "ambiguous"


def _shell_outcome(result: dict | None) -> str:
    """The same for a shell call's command as a whole, read as the phase
    history reads it: an explicit `is_error: false`, not interrupted, exit 0.
    A backgrounded call is `ambiguous`: its result is the launch, not the
    command's end (#3113)."""
    if result is None:
        return "pending"
    flag, metadata = result["is_error"], result["metadata"]
    if not isinstance(flag, bool):
        return "ambiguous"
    if flag:
        return "failed"
    if isinstance(metadata, dict) and (metadata.get("backgroundTaskId") or metadata.get("background_task_id")):
        return "ambiguous"
    if isinstance(metadata, dict) and (
            metadata.get("interrupted")
            or metadata.get("exitCode") not in (None, 0) or metadata.get("exit_code") not in (None, 0)):
        return "failed"
    return "succeeded"


def _denied(result: dict | None) -> bool:
    """The native control refused the call before it ran."""
    if result is None or result["is_error"] is not True:
        return False
    text = _result_text(result["content"])
    return isinstance(text, str) and text.startswith(NATIVE_DENIAL_PREFIX)


def _derive_outcome(result: dict | None, basis: str) -> str:
    """A `derive core` part's own outcome from its call's result (#3113).
    `basis` says what the call's status tells about the part: `command` (it
    is the part's status), `and_chain` (a success is the part's; a failure
    may be a later part's) or `none` (piped, backgrounded, grouped, after
    `||`, followed by `;`, or in a multi-line command). A part whose status
    the result does not carry is `ambiguous`, unless the native control
    denied the call, which then never ran."""
    overall = _shell_outcome(result)
    if overall in ("pending", "ambiguous") or basis == "command":
        return overall
    if overall == "failed":
        return "failed" if _denied(result) else "ambiguous"
    return "succeeded" if basis == "and_chain" else "ambiguous"


def _result_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text") for b in content if isinstance(b, dict) and isinstance(b.get("text"), str)]
        return "".join(parts) if len(parts) == len(content) else None
    return None


# ---------------------------------------------------------------- shell
def _strip_comments(command: str) -> str:
    """The command with its comments removed as bash reads them: a `#`
    starts one only at the start of a word (at the start, or after
    whitespace or a metacharacter) and outside quotes, and it runs to the
    end of the line. A `#` inside a word (`s/#//g`, `a#b`, `$#`) or quoted
    is text (#3184). An unterminated quote keeps the rest as written, which
    the tokeniser then refuses."""
    out: list[str] = []
    i, n = 0, len(command)
    quote: str | None = None                        # "'", '"' or "$'" (ANSI-C)
    word_start = True
    while i < n:
        ch = command[i]
        if quote is not None:
            if ch == "\\" and quote != "'" and i + 1 < n:
                out.append(command[i:i + 2])
                i += 2
                continue
            out.append(ch)
            if ch == quote[-1]:
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            out.append(command[i:i + 2])
            i += 2
            word_start = False
            continue
        if ch == "#" and word_start:
            end = command.find("\n", i)
            if end < 0:
                break
            i = end                                 # the newline itself is kept
            continue
        if ch == "$" and command[i + 1:i + 2] == "'":
            quote = "$'"
            out.append("$'")
            i += 2
            word_start = False
            continue
        if ch in "'\"":
            quote = ch
        out.append(ch)
        word_start = ch.isspace() or ch in "();<>|&"
        i += 1
    return "".join(out)


def _tokens(command: str) -> list[str] | None:
    """The command's words and operators, or None when it does not tokenise.
    Comments are removed first, the way bash removes them, and the lexer's
    own comment rule is off: shlex ends a word at any `#`, which would drop
    everything after `s/#//g` (#3184)."""
    lexer = shlex.shlex(_strip_comments(command.replace("\\\n", " ")), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return None


def _layout(tokens: list[str]) -> tuple[list[list[str]], list[list[str]], list[str]]:
    """(segments, joins, leading): the command's parts between operators,
    with joins[i] the operators after part i (before part i + 1, or at the
    end for the last) and `leading` any before the first."""
    segments: list[list[str]] = []
    joins: list[list[str]] = []
    leading: list[str] = []
    current: list[str] = []
    for token in tokens:
        if token in _OPERATORS:
            if current:
                segments.append(current)
                joins.append([])
                current = []
            (joins[-1] if joins else leading).append(token)
        else:
            current.append(token)
    if current:
        segments.append(current)
        joins.append([])
    return segments, joins, leading


def _status_basis(index: int, joins: list[list[str]], leading: list[str], newline: bool) -> str:
    """What the command's status tells about part `index` (#3113): `command`
    when it is that part's status, `and_chain` when a success is (every
    later join is `&&`), else `none`. Only `&&` and `;` joins keep it; a
    trailing `;` changes nothing; an unescaped newline is a join shlex
    cannot see, so it keeps nothing."""
    tail = list(joins[-1]) if joins else []
    while tail and tail[-1] == ";":
        tail.pop()
    ops = leading + [op for j in joins[:-1] for op in j] + tail
    if newline or not set(ops) <= _SEQUENTIAL:
        return "none"
    after = [op for j in joins[index:-1] for op in j] + tail
    if not after:
        return "command"
    return "and_chain" if set(after) == {"&&"} else "none"


def _program(segment: list[str]) -> list[str]:
    """The segment from its program on: leading assignments and `poetry run` dropped."""
    rest = list(segment)
    while rest and _ASSIGNMENT.fullmatch(rest[0]):
        rest.pop(0)
    if rest[:2] == ["poetry", "run"]:
        rest = rest[2:]
    return rest


def _cli_args(rest: list[str]) -> list[str] | None:
    """The arguments to the d4d CLI, when the segment runs it."""
    if not rest:
        return None
    program = os.path.basename(rest[0])
    if program == "d4d":
        return rest[1:]
    if _PYTHON.fullmatch(program) and rest[1:3] == ["-m", "data_sheets_schema.cli"]:
        return rest[3:]
    return None


def _subcommand(args: list[str]) -> tuple[tuple[str, ...], list[str]]:
    rest = list(args)
    if rest[:1] == ["--manifest"]:
        rest = rest[2:]
    elif rest and rest[0].startswith("--manifest="):
        rest = rest[1:]
    return tuple(rest[:2]), rest[2:]


def _option(args: list[str], *names: str) -> list[str]:
    values = []
    for i, token in enumerate(args):
        for name in names:
            if token == name and i + 1 < len(args):
                values.append(args[i + 1])
            elif token.startswith(name + "="):
                values.append(token[len(name) + 1:])
    return values


def _shell(command: str, cwd: str | None, targets: list[_Target]) -> dict[str, Any]:
    """What one shell command does to the tracked files: the targets it names,
    whether it is known to be read-only, and each part that derives the core
    (whether its `--full` is the tracked record, and what the call's status
    says about that part)."""
    tokens = _tokens(command)
    named = [x for x in targets if x.name in command]
    out: dict[str, Any] = {"named": [], "read_only": False, "derives": []}
    if tokens is None:
        out["named"] = [x.kind for x in named]
        return out
    newline = "\n" in command.replace("\\\n", " ")
    segments, joins, leading = _layout(tokens)
    changes_directory = any(_program(s)[:1] in (["cd"], ["pushd"]) for s in segments)
    for target in named:
        for token in tokens:
            if target.name not in token:
                continue
            if not _CLEAN_PATH.fullmatch(token) or changes_directory:
                hit = True
            else:
                hit = target.matches(token, cwd)
            if hit is not False:
                out["named"].append(target.kind)
                break
    # Read-only: no redirection except to /dev/null or a descriptor, no
    # unescaped newline (a second command), and every program known to read.
    read_only = not newline
    for i, token in enumerate(tokens):
        if set(token) <= _PUNCT and ">" in token:
            following = tokens[i + 1] if i + 1 < len(tokens) else ""
            if not (following == "/dev/null" or (token == ">&" and following.isdigit())):
                read_only = False
    local = cwd
    full = next((x for x in targets if x.kind == "full"), None)
    for index, segment in enumerate(segments):
        rest = _program(segment)
        if not rest:
            continue
        program = os.path.basename(rest[0])
        if program == "cd":
            where = rest[1] if len(rest) > 1 else None
            if where is None or not _CLEAN_PATH.fullmatch(where):
                local = None
            elif os.path.isabs(where):
                local = where
            else:
                local = os.path.join(local, where) if local is not None else None
            continue
        args = _cli_args(rest)
        if args is not None:
            sub, sub_args = _subcommand(args)
            outs = _option(sub_args, "--out", "-o")
            if sub not in READ_ONLY_D4D or any(
                    target.matches(o, local) is not False for o in outs for target in targets):
                read_only = False
            if sub == ("derive", "core") and full is not None:
                spelled = _option(sub_args, "--full")
                if not spelled:
                    verdict = False
                elif not _CLEAN_PATH.fullmatch(spelled[-1]):
                    verdict = None                  # a variable or glob: cannot be placed
                else:
                    verdict = full.matches(spelled[-1], local)
                out["derives"].append({"targets_full": verdict, "segment": index,
                                       "basis": _status_basis(index, joins, leading, newline)})
            continue
        if program not in READ_ONLY_PROGRAMS:
            read_only = False
        elif program == "sed" and any(a == "-i" or a == "-I" or a.startswith("--in-place")
                                      or (a.startswith("-") and not a.startswith("--") and "i" in a[1:])
                                      for a in rest[1:]):
            read_only = False
    out["read_only"] = read_only
    return out


# ---------------------------------------------------------------- receipts
def _key(value: Any) -> str:
    return value if isinstance(value, str) else "\x00json:" + json.dumps(value, sort_keys=True, default=str)


def _digest(key: str) -> str:
    return _sha256(key.encode("utf-8"))


def triples(text: str) -> list[tuple[str, str, str]] | None:
    """(chunk, snippet, slot) for every pair `receipts.check` counts as a
    snippet, in receipt order; None when the text is not a receipt."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("chunks"), list):
        return None
    out = []
    for entry in data["chunks"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            continue
        pairs = entry.get("extracted")
        if entry.get("status") != "extracted" or not isinstance(pairs, list) or not all(
                isinstance(p, dict) for p in pairs):
            continue
        out.extend((entry["id"], _key(p.get("snippet")), _key(p.get("slot"))) for p in pairs)
    return out


def _delta(before: Counter, after: Counter) -> dict[str, int]:
    return {"removed": sum((before - after).values()), "added": sum((after - before).values())}


def _split(items: list[str], available: Counter) -> tuple[list[str], list[str]]:
    """(matched, unmatched): items matched one-for-one against a multiset,
    in order."""
    left = Counter(available)
    matched, unmatched = [], []
    for item in items:
        if left[item] > 0:
            left[item] -= 1
            matched.append(item)
        else:
            unmatched.append(item)
    return matched, unmatched


def classify(base: list[tuple[str, str, str]], core: list[tuple[str, str, str]],
             final: list[tuple[str, str, str]]) -> dict[str, Any]:
    """Each final element's origin, by (chunk, snippet) multiset against the
    pre-draft and derive-time snapshots. An element whose triple is in the
    pre-draft snapshot is matched first; a contemporaneous element matched
    only by (chunk, snippet) was re-addressed. Which slots the entries name
    is a function of the three multisets, never of receipt order (#3115)."""
    pairs = lambda rows: Counter((c, s) for c, s, _ in rows)
    b_pairs, c_pairs = pairs(base), pairs(core)
    b_slots: dict[tuple, list[str]] = defaultdict(list)
    c_slots: dict[tuple, Counter] = defaultdict(Counter)
    f_slots: dict[tuple, list[str]] = defaultdict(list)
    for c, s, slot in base:
        b_slots[(c, s)].append(slot)
    for c, s, slot in core:
        c_slots[(c, s)][slot] += 1
    for c, s, slot in final:
        f_slots[(c, s)].append(slot)
    counts = dict.fromkeys(ORIGINS, 0)
    by_chunk: dict[str, dict[str, int]] = {}
    post, removed = [], []
    readdressed = 0
    for pair, finals in f_slots.items():
        chunk, snippet = pair
        contemporaneous = min(len(finals), b_pairs[pair])
        phase1 = min(len(finals) - contemporaneous, max(c_pairs[pair] - b_pairs[pair], 0))
        # Final slots in slot order: those the pre-draft snapshot carried are
        # contemporaneous as they stand (never more than `contemporaneous`).
        exact, rest = _split(sorted(finals), Counter(b_slots[pair]))
        moved = contemporaneous - len(exact)
        readdressed += moved
        # Of the rest, the slots the derive-time snapshot added are the Phase
        # 1 ones first; the re-addressed contemporaneous elements come next,
        # and what is left, preferring slots absent at derive, is Phase 3.
        at_core, later = _split(rest, c_slots[pair] - Counter(b_slots[pair]))
        ordered = at_core + later
        labels = (["phase1_correction"] * phase1 + [None] * moved
                  + ["phase3_backport"] * (len(ordered) - phase1 - moved))
        row = by_chunk.setdefault(chunk, dict.fromkeys(ORIGINS, 0))
        counts["contemporaneous"] += contemporaneous
        row["contemporaneous"] += contemporaneous
        for slot, label in zip(ordered, labels):
            if label is None:
                continue                                # a re-addressed contemporaneous element
            counts[label] += 1
            row[label] += 1
            post.append({"chunk": chunk, "slot": slot, "snippet_sha256": _digest(snippet), "origin": label})
    for pair, slots in b_slots.items():
        finals = f_slots.get(pair, [])
        gone = len(slots) - min(len(slots), len(finals))
        if gone:
            # Unmatched pre-draft slots, in slot order, feed the re-addressed
            # elements first; the last `gone` are the ones the final receipt dropped.
            _, unmatched = _split(sorted(slots), Counter(finals))
            for slot in unmatched[len(unmatched) - gone:]:
                removed.append({"chunk": pair[0], "slot": slot, "snippet_sha256": _digest(pair[1])})
    return {"origin": counts, "post_draft": counts["phase1_correction"] + counts["phase3_backport"],
            "removed_contemporaneous": len(removed), "readdressed": readdressed,
            "by_chunk": {c: by_chunk[c] for c in sorted(by_chunk)},
            "post_draft_entries": sorted(post, key=lambda e: (e["chunk"], e["slot"], e["snippet_sha256"], e["origin"])),
            "removed_entries": sorted(removed, key=lambda e: (e["chunk"], e["slot"], e["snippet_sha256"]))}


# ---------------------------------------------------------------- the report
def _where(call: dict, result: dict | None = None) -> dict[str, Any]:
    out = {"tool_use_id": call["id"], "transcript": call["transcript"], "line": call["line"]}
    if result is not None:
        out["result_line"] = result["line"]
    return out


def _touches(target: _Target, spelled: str, cwd: str | None) -> bool:
    """A path names the target; a relative one with no working directory
    does when its basename is the target's."""
    hit = target.matches(spelled, cwd)
    return hit is True or (hit is None and os.path.basename(spelled) == target.name)


def _history(calls: list[dict], results: dict[str, dict], targets: list[_Target],
             reasons: list[str]) -> dict[str, Any]:
    """Every call that bears on the two files, sorted into successful Writes,
    unsettled Writes, refusals, other mutations and `derive core` runs."""
    h: dict[str, Any] = {"writes": {"receipt": [], "full": []}, "unsettled": {"receipt": [], "full": []},
                         "mutations": [], "rejected": [], "derives": []}
    for call in calls:
        name, inputs, result = call["name"], call["input"], results.get(call["id"])
        if not isinstance(inputs, dict):
            reasons.append(f"tool call {call['id']} (transcript {call['transcript']} line {call['line']}) "
                           "has no input mapping")
            continue
        # `_at` is where the call was issued and `_settled` where its result
        # came back, as (transcript, line): internal, never output.
        where = {**_where(call, result), "pos": call["pos"], "_at": (call["transcript"], call["line"]),
                 "_settled": (result["transcript"], result["line"]) if result is not None else None}
        if name == "Write":
            spelled = inputs.get("file_path")
            for target in targets:
                if not isinstance(spelled, str) or not _touches(target, spelled, call["cwd"]):
                    continue
                state = _outcome(result)
                if state == "succeeded" and isinstance(inputs.get("content"), str):
                    metadata = result["metadata"] if isinstance(result["metadata"], dict) else {}
                    if target.matches(spelled, call["cwd"]) is None:
                        reasons.append(f"Write {call['id']} names the {_LABEL[target.kind]} by a relative "
                                       "path with no working directory")
                    h["writes"][target.kind].append({**where, "content": inputs["content"],
                                                     "created": metadata.get("type")})
                elif state == "rejected":
                    h["rejected"].append({**_where(call, result), "target": target.kind, "tool": name,
                                          "rejection": ("file_not_read" if _result_text(result["content"])
                                                        == UNREAD_WRITE_ERROR else "is_error")})
                else:
                    h["unsettled"][target.kind].append(
                        {**where, "outcome": state if state != "succeeded" else "no content"})
        elif name == "Bash":
            command = inputs.get("command")
            if not isinstance(command, str):
                reasons.append(f"shell call {call['id']} has no command string")
                continue
            shell = _shell(command, call["cwd"], targets)
            # One row per part that derives the core, with that part's own
            # outcome (#3113): `targets_full` is None when its `--full`
            # cannot be placed.
            h["derives"].extend({**where, "segment": part["segment"], "targets_full": part["targets_full"],
                                 "outcome": _derive_outcome(result, part["basis"]),
                                 "command_outcome": _shell_outcome(result), "status_basis": part["basis"]}
                                for part in shell["derives"])
            if shell["read_only"]:
                continue
            if _denied(result):
                # The native control refused the call before it ran (#3185):
                # listed like a refused Edit, never a possible change.
                h["rejected"].extend({**_where(call, result), "target": kind, "tool": name,
                                      "rejection": "native_denial"} for kind in shell["named"])
            else:
                h["mutations"].extend({**where, "target": kind, "tool": name, "outcome": _shell_outcome(result)}
                                      for kind in shell["named"])
        elif name not in READ_TOOLS:
            # An edit tool, or any other tool given a path: a change that is
            # not a whole-file Write, unless it was refused (READ_TOOLS).
            spelled = [inputs.get(k) for k in ("file_path", "notebook_path", "path")
                       if isinstance(inputs.get(k), str)]
            for target in targets:
                if not any(_touches(target, p, call["cwd"]) for p in spelled):
                    continue
                state = _outcome(result)
                if state == "rejected":
                    h["rejected"].append({**_where(call, result), "target": target.kind, "tool": name,
                                          "rejection": "is_error"})
                else:
                    h["mutations"].append({**where, "target": target.kind, "tool": name, "outcome": state})
    return h


def _boundaries(h: dict[str, Any], reasons: list[str]) -> tuple[dict | None, dict | None]:
    """The first successful Write of the full record, and the first successful
    `derive core` of it after that; every reason the history cannot be
    placed around them."""
    first = h["writes"]["full"][0] if h["writes"]["full"] else None
    if first is None:
        reasons.append("no successful Write of the full record in the transcripts")
    draft = first["pos"] if first else None
    pre_draft = lambda row: draft is None or row["pos"] < draft
    for kind in ("receipt", "full"):
        opening = h["writes"][kind][0]["created"] if h["writes"][kind] else "create"
        if opening == "update":
            reasons.append(f"the first observed Write of the {_LABEL[kind]} updated an existing file: "
                           "its earlier history is not in the transcripts")
        elif opening != "create":
            # An explicit `is_error: false` is success evidence without the
            # runtime's metadata, which alone says the file was new (#3116).
            reasons.append(f"the first observed Write of the {_LABEL[kind]} carries no create/update "
                           "metadata: whether its earlier history is in the transcripts cannot be told")
        for row in h["unsettled"][kind]:
            if kind == "receipt" or pre_draft(row):
                reasons.append(f"Write {row['tool_use_id']} of the {_LABEL[kind]} has no success evidence "
                               f"({row['outcome']})")
    derived = None
    for row in h["derives"]:
        if row["targets_full"] is False:
            continue                                    # another record's derivation
        if row["outcome"] == "succeeded" and row["targets_full"] is True:
            if pre_draft(row):
                reasons.append(f"core derived ({row['tool_use_id']}) before the first full-record Write")
                continue
            derived = row
            break
        if row["outcome"] in ("ambiguous", "pending") and row["command_outcome"] == row["outcome"]:
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: its result is {row['outcome']}")
        elif row["outcome"] == "ambiguous":
            why = ("a later `&&` part may be what failed" if row["status_basis"] == "and_chain" else
                   "piped, backgrounded, grouped, after `||`, followed by `;`, or multi-line")
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: the call {row['command_outcome']} "
                           f"but its status is not the derive's own ({row['status_basis']}: {why})")
        elif row["outcome"] == "succeeded":
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: its --full cannot be resolved "
                           "(a variable, or a relative path with no working directory)")
    # A non-Write change of the receipt issued after the draft, the last
    # receipt Write and the derive boundary had all returned reaches no
    # snapshot but the final one, which the sha256 against the file on disk
    # covers (#3112). Any earlier one may have changed a snapshot unseen.
    receipt_writes = h["writes"]["receipt"]
    settled = [row["_settled"] for row in (first, receipt_writes[-1] if receipt_writes else None, derived)
               if row is not None]
    for row in h["mutations"]:
        if row["target"] == "receipt":
            row["covered_by_final_sha256"] = bool(first is not None and receipt_writes
                                                  and all(row["_at"] > s for s in settled))
            if row["covered_by_final_sha256"]:
                continue
        if row["target"] == "receipt" or pre_draft(row):
            reasons.append(f"{row['tool']} call {row['tool_use_id']} (transcript {row['transcript']} line "
                           f"{row['line']}) may change the {_LABEL[row['target']]} other than by a Write")
    return first, derived


def origin(transcripts: list[Path], receipt: Path, full: Path) -> dict[str, Any]:
    """The receipt-origin block for one run: its transcripts in order (a
    killed-and-resumed run's files, first invocation first), its coverage
    receipt and its full record."""
    reasons: list[str] = []
    info, events = _load([Path(p) for p in transcripts], reasons)
    calls, results = _pair(events, reasons)
    h = _history(calls, results, [_Target("receipt", receipt), _Target("full", full)], reasons)
    first, derived = _boundaries(h, reasons)
    writes = h["writes"]["receipt"]
    try:
        on_disk = _sha256(Path(receipt).read_bytes())
    except OSError as exc:
        on_disk = None
        reasons.append(f"the receipt cannot be read ({type(exc).__name__})")
    last = writes[-1] if writes else None
    rebuilt = _sha256(last["content"].encode("utf-8")) if last else None
    if last is None:
        reasons.append("no successful Write of the receipt in the transcripts")
    elif on_disk is not None and rebuilt != on_disk:
        reasons.append("the receipt rebuilt from the transcripts differs from the file on disk (sha256)")

    def before(row: dict) -> dict | None:
        earlier = [w for w in writes if w["pos"] < row["pos"]]
        return earlier[-1] if earlier else None

    snapshots: dict[str, list] = {}
    if not reasons:
        for stage, write in (("pre_draft", before(first)),
                             ("at_derive_core", before(derived) if derived else last),
                             ("final", last)):
            rows = triples(write["content"]) if write is not None else []
            if rows is None:
                reasons.append(f"the receipt as written at transcript {write['transcript']} line "
                               f"{write['line']} ({stage}) is not a receipt")
            snapshots[stage] = rows

    strip = lambda row: {k: v for k, v in row.items() if k not in ("pos", "content") and not k.startswith("_")}
    block: dict[str, Any] = {
        "instrument": INSTRUMENT,
        "status": "unknown" if reasons else "checked",
        "reasons": reasons,
        "transcripts": info,
        "receipt": {"path": str(receipt), "sha256": on_disk, "rebuilt_sha256": rebuilt, "writes": len(writes)},
        "full": {"path": str(full), "writes": len(h["writes"]["full"])},
        "boundaries": {"full_record_write": strip(first) if first else None,
                       "derive_core": strip(derived) if derived else None},
        "derive_core_attempts": [strip(r) for r in h["derives"]],
        "rejected_writes": h["rejected"],
        "non_write_mutations": [strip(r) for r in h["mutations"]],
        "non_checks": list(NON_CHECKS),
    }
    if reasons:
        return block
    base, core, final = snapshots["pre_draft"], snapshots["at_derive_core"], snapshots["final"]
    pairs = lambda rows: Counter((c, s) for c, s, _ in rows)
    block["snippets"] = {"pre_draft": len(base), "at_derive_core": len(core) if derived else None,
                         "final": len(final)}
    # With no successful derive there is no derive-time snapshot: the two
    # derive-core deltas are None and `draft_to_final` carries the step (#3114).
    block["deltas"] = {
        "draft_to_derive_core": _delta(pairs(base), pairs(core)) if derived else None,
        "derive_core_to_final": _delta(pairs(core), pairs(final)) if derived else None,
        "draft_to_final": _delta(pairs(base), pairs(final)),
        "triples_draft_to_final": _delta(Counter(base), Counter(final)),
    }
    block.update(classify(base, core, final))
    return block


def summary(block: dict[str, Any]) -> list[str]:
    """Plain lines for the terminal: counts only."""
    lines = [f"receipt origin: {block['status']} ({block['instrument']})"]
    if block["status"] != "checked":
        return lines + [f"· {r}" for r in block["reasons"]]
    s, d, o = block["snippets"], block["deltas"], block["origin"]
    core = "no successful derive core" if s["at_derive_core"] is None else f"{s['at_derive_core']} at derive core"
    lines.append(f"snippets {s['pre_draft']} pre-draft · {core} · {s['final']} final")
    if d["draft_to_derive_core"] is not None:
        step, then = d["draft_to_derive_core"], d["derive_core_to_final"]
        text = (f"draft → derive core −{step['removed']} / +{step['added']}"
                f" · derive core → final −{then['removed']} / +{then['added']}")
    else:
        step = d["draft_to_final"]
        text = f"draft → final −{step['removed']} / +{step['added']}"
    step = d["triples_draft_to_final"]
    lines.append(text + f" · (chunk, snippet, slot) triples −{step['removed']} / +{step['added']}")
    lines.append(" · ".join(f"{o[k]} {k}" for k in ORIGINS)
                 + f" · {block['removed_contemporaneous']} contemporaneous removed"
                 + f" · {block['readdressed']} readdressed")
    for row in block["rejected_writes"]:
        lines.append(f"· rejected {row['tool']} of the {_LABEL[row['target']]} ({row['rejection']}), "
                     f"transcript {row['transcript']} line {row['line']}")
    return lines
