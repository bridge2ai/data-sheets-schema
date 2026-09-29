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
the native control denied: it never ran (#3185). So is one the runtime
refused in `dontAsk` mode, but only where the transcript's terminal
`result` event lists it under `permission_denials` with the call's own
tool name and input (#3201); the refusal text alone is not evidence, and
an uncorroborated one stays a possible change. A `derive core` succeeded
only where its call's result carries the derive's own status (#3113). With
every join in the command `&&` or `;`, the call's success or failure is the
derive's when the derive is the last part, and its success alone is when
every join after the derive is `&&` (a failure may be a later part's).
Otherwise (piped, backgrounded, grouped, after `||`, followed by `;`, in a
multi-line command, or a failed `&&` chain) the derive is ambiguous, unless
the call was denied as above, and then never ran. A `timeout`, `env` or
`nice` wrapper with options this reads, and an interpreter held in a
variable (`$PY -m data_sheets_schema.cli`), are read through; any other
part that carries the words `derive core` and is neither a d4d call of
another subcommand nor a program known to read (a nested `bash -c`,
`xargs`, a wrapper option or CLI option it does not read) is a derive that
cannot be placed (#3137). So is a reader part that carries them where a
pipe later in the command feeds a program not known to read (`echo '...
derive core ...' | bash`, `| xargs d4d`, #3384), and, in a command that
substitutes anywhere (`$(...)`, backticks, `<(...)`), every part that
carries them, readers and the recorder's `--phase` included: the parts
inside a substitution are split out of it, so none can be shown not to be
in one (#3385). A call the runtime
backgrounded is ambiguous too: its result is the launch, not the end. A
shell command is read as bash reads it: `#` starts a comment only at the
start of a word, outside quotes (#3184), and a `cd`, `pushd` or `popd`
moves the directory a later part's `--full` resolves against only where
that part runs only if the change ran and succeeded -- reached by `;` or
`&&` and followed by `&&` alone up to the part; otherwise, and in a
multi-line command, the directory is not known (#3268).

The status is `unknown`, with every reason, and no classification is
reported when the history cannot be rebuilt: a transcript is missing,
unreadable or malformed; a tool id is duplicated or a result has no call
(#2077); a Write of the receipt, or of the full record before its first
successful Write, has no result or no success evidence; the receipt is
changed by anything other than a Write (an edit tool, or a shell command
that names it, is not known to be read-only and was not denied by the
native control; a command substitution -- backticks, `$(...)` unquoted or
double-quoted, `<(...)` or `>(...)` -- is never known to be read-only,
since the inner command is not parsed, #3240) where the change can reach
the pre-draft or derive-time snapshot, or the full record is changed that
way before its first Write; the first observed Write of either file updated
an existing file, or carries no create/update metadata to say it did not; a
`derive core` of the full record cannot be placed; a receipt Write was in
flight (issued before the other had returned) together with another
receipt Write, the first full-record Write or the derive boundary, so which
took effect first cannot be told (#3268); or the rebuilt final receipt's
sha256 differs from the file on disk. A non-Write change issued
after the last receipt Write, the draft and the derive boundary had all
returned can reach only the final receipt, which the sha256 comparison
covers: it is listed with `covered_by_final_sha256` and is not a reason.
Nothing is reported as contemporaneous on incomplete evidence, except
through a shell write the parser cannot attribute to the receipt because
the command does not name it literally -- a glob or variable, a script or
program that writes it without its name on the command line, a command on
a directory that holds it -- or through a ripgrep preprocessor set in a
config file from outside the command (#3256), or a ripgrep hostname helper
set in a config file the same way (#3268), which `NON_CHECKS` names
(#3221). `rg --pre CMD` runs CMD on each file it searches and `rg
--hostname-bin CMD` runs CMD for its hyperlinks, so an `rg` call that
sets either on its command line is not read-only.

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
#: only when `_sed_reads_only` admits its options and script: no in-place
#: flag, no script file, and no `w`/`W`/`e` command or `s///w`/`s///e`
#: flag, #3220; `rg` only when `_rg_reads_only` admits it: no `--pre`
#: preprocessor, which runs a command on each file searched, #3256, and no
#: `--hostname-bin` helper, which runs a command for hyperlinks, #3268).
#: Anything else that names a tracked file is a possible mutation, and so
#: is any command that substitutes one (`_substitutes`, #3240).
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
#: The Claude Code runtime's own refusal of a Bash call in `dontAsk` mode, as
#: `scripts/reference_rescore.py` (`denied_bash_calls`) reads it. The text
#: alone is not evidence: a call answered with it counts as never run only
#: where the transcript's terminal `result` event lists it (#3201).
DONT_ASK_DENIAL_PREFIX = ("Permission to use Bash has been denied because Claude Code is running "
                          "in don't ask mode.")
#: Joins between the parts of a shell command after which the command's own
#: status can still be the derive's (#3113).
_SEQUENTIAL = frozenset({"&&", ";"})

NON_CHECKS = (
    "that a contemporaneous snippet supports the value it sits under (#2067: post-draft "
    "snippets stay unaccepted for semantic support until independent review)",
    "a shell write that does not name the receipt literally, before the last Write (one after "
    "it is caught by the final sha256): a glob or variable, a program or script that writes it "
    "without its name on the command line (`python fix.py`), or a command on a directory that "
    "holds it (`git checkout -- DIR`, `rm -r DIR`) (#3221)",
    "a ripgrep preprocessor set in a config file that `RIPGREP_CONFIG_PATH` names from outside "
    "the command (exported earlier or inherited), or a hostname helper (`--hostname-bin`) set "
    "there: `rg` is read-only only when neither its arguments nor its own assignments set "
    "either (#3256, #3268)",
    "a `derive core` run without the words `derive core` on the command line (a script, an "
    "alias or function, a variable holding the subcommand, `python -c` building the argument "
    "list, or a file that an earlier part wrote the words into and a later part runs): such a "
    "derive is not seen, and the Phase 1 / Phase 3 boundary is missed (#3137, #3384)",
)

_ABSENT = object()
_LABEL = {"receipt": "receipt", "full": "full record"}
_OPERATORS = frozenset({"&&", "||", ";", "|", "&", "|&", "(", ")", ";;", ";&"})
_PUNCT = frozenset("();<>|&")
_CLEAN_PATH = re.compile(r"[A-Za-z0-9_./+@-]+")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
_PYTHON = re.compile(r"python(\d+(\.\d+)*)?")
_VARIABLE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})")
_DURATION = re.compile(r"\d+(\.\d+)?[smhd]?")
_DERIVE_CORE = re.compile(r"(?<![\w.-])derive\s+core(?![\w.-])")


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


def _runtime_denials(events: list[tuple[int, int, dict]], calls: list[dict],
                     results: dict[str, dict]) -> set[str]:
    """The Bash calls the runtime itself refused in `dontAsk` mode (#3201),
    corroborated as `scripts/reference_rescore.py` corroborates them: the
    call's own transcript ends in exactly one terminal `result` event, a
    `success` with `is_error: false`, after the call's result; that event's
    `permission_denials` lists the call once, with `tool_name` Bash and
    `tool_input` equal to the call's input, a mapping whose `command` is a
    string; and the call's result is an error whose content is a string
    opening with the runtime's refusal. The refusal text without the
    terminal listing is not evidence: a command can print it. The one
    tool_use and one tool_result per id that `reference_rescore` requires
    are required here by `_pair`: a duplicated id or a second result is a
    reason, so the whole block is `unknown` (#2077) whatever the denials say."""
    terminals: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for t, n, event in events:
        if event.get("type") == "result":
            terminals[t].append((n, event))
    by_id = {call["id"]: call for call in calls}
    proven: set[str] = set()
    for t, found in terminals.items():
        if len(found) != 1:
            continue
        line, terminal = found[0]
        denials = terminal.get("permission_denials")
        if (terminal.get("subtype") != "success" or terminal.get("is_error") is not False
                or not isinstance(denials, list)):
            continue
        listed = Counter(d.get("tool_use_id") for d in denials if isinstance(d, dict))
        for denial in denials:
            if not isinstance(denial, dict):
                continue
            identity = denial.get("tool_use_id")
            call, result = by_id.get(identity), results.get(identity)
            if (listed[identity] != 1 or call is None or result is None
                    or call["transcript"] != t or result["transcript"] != t
                    or not call["line"] < result["line"] < line
                    or call["name"] != "Bash" or denial.get("tool_name") != "Bash"
                    or not isinstance(call["input"], dict) or not isinstance(call["input"].get("command"), str)
                    or denial.get("tool_input") != call["input"] or result["is_error"] is not True):
                continue
            # The content itself, a string, as `reference_rescore` reads it:
            # a list of text blocks is not joined here (#3387).
            content = result["content"]
            if isinstance(content, str) and content.startswith(DONT_ASK_DENIAL_PREFIX):
                proven.add(identity)
    return proven


def _derive_outcome(result: dict | None, basis: str, denied: bool = False) -> str:
    """A `derive core` part's own outcome from its call's result (#3113).
    `basis` says what the call's status tells about the part: `command` (it
    is the part's status), `and_chain` (a success is the part's; a failure
    may be a later part's), `none` (piped, backgrounded, grouped, after
    `||`, followed by `;`, or in a multi-line command) or `unparsed` (a
    spelling the parser does not read, #3137). A part whose status the
    result does not carry is `ambiguous`, unless the call was `denied` --
    by the native control or, corroborated, by the runtime (#3201) -- and
    so never ran."""
    overall = _shell_outcome(result)
    if overall in ("pending", "ambiguous") or basis == "command":
        return overall
    if overall == "failed":
        return "failed" if denied else "ambiguous"
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


def _substitutes(command: str) -> bool:
    """Whether the (comment-free) command runs a command inside a word:
    a backtick or `$(` outside single and `$'...'` quotes -- inside double
    quotes too -- or a process substitution `<(` / `>(` outside quotes.
    The tokeniser reads `echo "$(sed -i d R)"`, `` echo `rm R` `` and
    `cat <(rm R)` as arguments of a read-only `echo`/`cat` and never sees
    the inner command, so a command that substitutes is never known to be
    read-only (#3240). Conservative by design: the inner command is not
    parsed, and `$((...))` arithmetic counts too."""
    i, n = 0, len(command)
    quote: str | None = None
    while i < n:
        ch = command[i]
        if quote in ("'", "$'"):
            if ch == "\\" and quote == "$'" and i + 1 < n:
                i += 2
                continue
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "`" or (ch == "$" and command[i + 1:i + 2] == "("):
            return True
        if quote == '"':
            if ch == '"':
                quote = None
        elif ch in "<>" and command[i + 1:i + 2] == "(":
            return True
        elif ch == "$" and command[i + 1:i + 2] == "'":
            quote = "$'"
            i += 2
            continue
        elif ch in "'\"":
            quote = ch
        i += 1
    return False


def _newlines_as_joins(command: str) -> str:
    """The (comment-free) command with each unquoted newline read as the
    command separator it is to bash. shlex takes a newline for a space, so
    `cd data\\nd4d derive core ...` was one part whose program is `cd`, and
    the derive on the second line was never seen (#3268). A newline inside
    quotes stays text. A here-document's body lines become parts too, which
    can only add a part: never a known directory or a read-only call, since
    a multi-line command is neither."""
    out: list[str] = []
    i, n = 0, len(command)
    quote: str | None = None
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
            continue
        if ch == "$" and command[i + 1:i + 2] == "'":
            quote = "$'"
            out.append("$'")
            i += 2
            continue
        if ch in "'\"":
            quote = ch
        out.append(" ; " if ch == "\n" else ch)
        i += 1
    return "".join(out)


def _tokens(command: str) -> list[str] | None:
    """The command's words and operators, or None when it does not tokenise.
    Comments are removed first, the way bash removes them, and the lexer's
    own comment rule is off: shlex ends a word at any `#`, which would drop
    everything after `s/#//g` (#3184)."""
    text = _newlines_as_joins(_strip_comments(command.replace("\\\n", " ")))
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
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


def _wrapper_skip(rest: list[str]) -> int | None:
    """How many words a `timeout`, `env` or `nice` wrapper and its options
    take before the program it runs (#3137), or None when `rest` is not one
    or carries an option this does not know (`env -C DIR`, `env -S STRING`,
    ...). Each passes the program's exit status through, so the status basis
    of a part it wraps is unchanged; `timeout`'s own 124 is a failure."""
    head = os.path.basename(rest[0]) if rest else None
    i = 1
    if head == "timeout":
        while i < len(rest) and rest[i].startswith("-"):
            a = rest[i]
            if a in ("--preserve-status", "--foreground", "-v", "--verbose"):
                i += 1
            elif a in ("-s", "-k", "--signal", "--kill-after"):
                i += 2
            elif a.startswith(("--signal=", "--kill-after=")) or (a[:2] in ("-s", "-k") and len(a) > 2):
                i += 1
            else:
                return None
        return i + 1 if i < len(rest) and _DURATION.fullmatch(rest[i]) else None
    if head == "env":
        while i < len(rest) and rest[i].startswith("-"):
            a = rest[i]
            if a in ("-i", "-", "--ignore-environment"):
                i += 1
            elif a in ("-u", "--unset"):
                i += 2
            elif a.startswith("--unset=") or (a.startswith("-u") and len(a) > 2):
                i += 1
            elif a == "--":
                return i + 1
            else:
                return None
        return i                                    # `_program` drops the assignments
    if head == "nice":
        if i < len(rest) and rest[i] in ("-n", "--adjustment"):
            i += 2
        elif i < len(rest) and re.fullmatch(r"(-n|--adjustment=|-)-?\d+", rest[i]):
            i += 1
        elif i < len(rest) and rest[i].startswith("-"):
            return None
        return i
    return None


def _unwrapped(segment: list[str]) -> list[str]:
    """The segment from the program it runs: leading assignments, `poetry
    run`, and any `timeout`, `env` or `nice` wrapper `_wrapper_skip` reads,
    in any order and repeated. A wrapper it cannot read stays the program."""
    rest = _program(segment)
    while (skip := _wrapper_skip(rest)) is not None and skip < len(rest):
        rest = _program(rest[skip:])
    return rest


def _cli_args(rest: list[str]) -> list[str] | None:
    """The arguments to the d4d CLI, when the segment runs it: `d4d`, or
    `python* -m data_sheets_schema.cli` with the interpreter named or held
    in a variable (`$PY -m ...`, #3137)."""
    if not rest:
        return None
    program = os.path.basename(rest[0])
    if program == "d4d":
        return rest[1:]
    if ((_PYTHON.fullmatch(program) or _VARIABLE.fullmatch(rest[0]))
            and rest[1:3] == ["-m", "data_sheets_schema.cli"]):
        return rest[3:]
    return None


def _mentions_derive(segment: list[str]) -> bool:
    """Whether the words `derive core` appear in the segment: as adjacent
    words, or inside one (`bash -c 'd4d derive core ...'`) (#3137)."""
    return bool(_DERIVE_CORE.search(" ".join(segment)))


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


#: sed options that take no value and change nothing but how it reads and
#: prints; `-l N` / `--line-length` take one. `--sandbox` refuses `w`, `e`
#: and `r` outright.
_SED_FLAGS = frozenset("nEsruz")
_SED_LONG = frozenset({"--quiet", "--silent", "--regexp-extended", "--separate", "--unbuffered",
                       "--null-data", "--zero-terminated", "--posix", "--debug", "--sandbox",
                       "--follow-symlinks"})
#: sed commands that take no argument and print, hold, edit the pattern
#: space, or quit. `a`, `i`, `c` print their text; `b`, `t`, `T`, `v` and
#: `:` name a label; `r` and `R` read a file: none writes one.
_SED_PLAIN = frozenset("pPnNdDgGhHxz=lFq Q{}".replace(" ", ""))
_SED_TO_EOL = frozenset("aicrR#")
#: Commands whose label ends at `;` or a newline, so the next command is
#: still read.
_SED_LABELLED = frozenset(":btTv")
_SED_S_FLAGS = frozenset("gpiImM0123456789")


#: ripgrep options whose value is a command ripgrep runs (#3256, #3268).
_RG_RUNS = ("--pre", "--hostname-bin")


def _rg_reads_only(segment: list[str]) -> bool:
    """Whether a ripgrep invocation writes only to stdout (#3256): ripgrep
    runs `--pre COMMAND` on each file it searches, and `--hostname-bin
    COMMAND` to name the host for its hyperlinks (#3268), so neither
    argument (in either spelling, before or after `--`) nor an assignment
    of `RIPGREP_CONFIG_PATH` on the segment, whose file may set either, is
    admitted. `--pre-glob` only narrows a `--pre` and is harmless alone."""
    for token in segment:
        if not _ASSIGNMENT.fullmatch(token):
            break
        if token.startswith("RIPGREP_CONFIG_PATH="):
            return False
    return not any(a == name or a.startswith(name + "=")
                   for a in _program(segment)[1:] for name in _RG_RUNS)


def _sed_reads_only(args: list[str]) -> bool:
    """Whether a sed invocation writes only to stdout (#3220): no in-place
    flag, no script from a file (it cannot be read here), and every script
    is one `_sed_script_reads_only` admits. A spelling it does not know is
    not read-only."""
    scripts: list[str] = []
    operands: list[str] = []
    sandbox = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-" or not a.startswith("-"):
            operands.append(a)                      # GNU reads options after operands too
        elif a == "--":
            operands.extend(args[i + 1:] or [""])
            break
        elif a.startswith("--"):
            name, eq, value = a.partition("=")
            if name == "--expression":
                if not eq:
                    i += 1
                    if i >= len(args):
                        return False
                    value = args[i]
                scripts.append(value)
            elif name == "--line-length":
                if not eq:
                    i += 1
            elif a in _SED_LONG:
                sandbox = sandbox or a == "--sandbox"
            else:
                return False                        # --in-place, --file, or unknown
        else:
            j = 1
            while j < len(a):
                c = a[j]
                if c in "el":
                    value = a[j + 1:]
                    if not value:
                        i += 1
                        if i >= len(args):
                            return False
                        value = args[i]
                    if c == "e":
                        scripts.append(value)
                    break
                if c not in _SED_FLAGS:
                    return False                    # -i, -I, -f, or unknown
                j += 1
        i += 1
    if not scripts:
        if not operands:
            return False
        scripts.append(operands[0])
    return sandbox or all(_sed_script_reads_only(x) for x in scripts)


def _sed_script_reads_only(script: str) -> bool:
    """Whether a sed script can write only to stdout: it parses, every
    command is one `_SED_PLAIN`, `_SED_TO_EOL`, `s` or `y` covers, and no
    `s` carries the `w` or `e` flag. The `w`, `W` and `e` commands, and
    anything unparsed, are writes (#3220)."""
    n, i = len(script), 0

    def delimited(i: int, delim: str) -> int | None:
        """The index after the closing `delim` of a part starting at i."""
        while i < n:
            if script[i] == "\\":
                i += 2
                continue
            if script[i] == "\n" and delim != "\n":
                return None
            if script[i] == delim:
                return i + 1
            i += 1
        return None

    def address(i: int) -> int | None:
        if i < n and script[i].isdigit():
            while i < n and (script[i].isdigit() or script[i] == "~"):
                i += 1
        elif i < n and script[i] == "$":
            i += 1
        elif i < n and script[i] in "/\\":
            if script[i] == "\\":
                if i + 1 >= n:
                    return None
                delim, i = script[i + 1], i + 2
            else:
                delim, i = "/", i + 1
            i = delimited(i, delim)
            if i is None:
                return None
            while i < n and script[i] in "IM":
                i += 1
        return i

    while i < n:
        c = script[i]
        if c in " \t\n;":
            i += 1
            continue
        start = i
        i = address(i)
        if i is None:
            return False
        if i > start and i < n and script[i] == ",":
            i += 1
            if i < n and script[i] in "+~":
                i += 1
            i = address(i)
            if i is None:
                return False
        while i < n and script[i] in " \t!":
            i += 1
        if i >= n:
            return False                            # an address with no command
        c = script[i]
        if c in _SED_PLAIN:
            i += 1
            if c in "qQlL":
                while i < n and script[i].isdigit():
                    i += 1
        elif c in _SED_TO_EOL:
            end = script.find("\n", i)
            i = n if end < 0 else end + 1
        elif c in _SED_LABELLED:
            i += 1
            while i < n and script[i] not in ";\n":
                i += 1
        elif c in "sy":
            if i + 1 >= n or script[i + 1] in "\\\n":
                return False
            delim = script[i + 1]
            i = delimited(i + 2, delim)
            if i is None:
                return False
            i = delimited(i, delim)
            if i is None:
                return False
            if c == "s":
                while i < n and script[i] not in ";\n}":
                    if script[i] not in _SED_S_FLAGS and script[i] not in " \t":
                        return False               # w FILE, e, or unknown
                    i += 1
        else:
            return False                            # w, W, e, or unknown
    return True


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
    changes_directory = any(_program(s)[:1] in (["cd"], ["pushd"], ["popd"]) for s in segments)
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
    # A command substitution hides its command inside a word (#3240).
    substitutes = _substitutes(_strip_comments(command))
    read_only = not newline and not substitutes
    for i, token in enumerate(tokens):
        if set(token) <= _PUNCT and ">" in token:
            following = tokens[i + 1] if i + 1 < len(tokens) else ""
            if not (following == "/dev/null" or (token == ">&" and following.isdigit())):
                read_only = False
    local = cwd
    # `pushd` moves like `cd` and remembers where it left; `popd` returns
    # there (#3222). A stack the command did not build (a `popd` with
    # nothing pushed, a bare `pushd` that swaps) leaves no known directory,
    # and so does an argument that is not a plain directory: an option, or
    # `cd -` (OLDPWD) and `pushd +N`/`-N` (a stack rotation), which bash
    # reads as no directory name (#3257).
    pushed: list[str | None] = []
    full = next((x for x in targets if x.kind == "full"), None)
    # A directory change holds for a later part only where that part runs
    # only if the change ran and succeeded (#3268): the change is reached
    # by `;` or `&&` alone (never after `||`, a pipe, `&` or a group
    # bracket), and every join from it to the part is `&&`. `cd /missing;
    # derive` runs the derive where the call started, and `false && cd X;
    # derive` skips the cd: neither leaves a known directory. In a
    # multi-line command a here-document's lines read as parts too
    # (`_newlines_as_joins`), so a change in one leaves none either.
    unsettled = False                               # a change was made; only `&&` keeps it
    # Per part: whether it runs a program not read here (`runs_unknown`),
    # and the reader parts that carry the words `derive core` without a row.
    runs_unknown = [False] * len(segments)
    mentioning_readers: list[int] = []
    for index, segment in enumerate(segments):
        before = leading if index == 0 else joins[index - 1]
        if unsettled and before != ["&&"]:
            local = None
            pushed = [None] * len(pushed)
        rest = _program(segment)
        if not rest:
            continue
        program = os.path.basename(rest[0])
        if program in ("cd", "pushd", "popd"):
            reached = not newline and before in ([], [";"], ["&&"])
            unsettled = True
        if program in ("cd", "pushd"):
            if program == "pushd":
                pushed.append(local)
                if not reached:
                    pushed = [None] * len(pushed)
            where = rest[1] if len(rest) == 2 else None
            if not reached or where is None or not _CLEAN_PATH.fullmatch(where) or where[:1] in "-+":
                local = None
            elif os.path.isabs(where):
                local = where
            else:
                local = os.path.join(local, where) if local is not None else None
            continue
        if program == "popd":
            local = pushed.pop() if pushed and len(rest) == 1 and reached else None
            if len(rest) > 1 or not reached:
                pushed = [None] * len(pushed)
            continue
        args = _cli_args(_unwrapped(segment))
        # A part that carries the words `derive core` but is not read here as
        # a d4d call of that subcommand, nor as a program known to read, may
        # run the derive through a spelling this parser does not follow (a
        # nested shell, `xargs`, a wrapper or a CLI option it does not know):
        # a derive that cannot be placed, never none (#3137). A substitution
        # anywhere in the command makes every such part opaque, readers and
        # other d4d subcommands included (#3385): the segmenter splits the
        # parts inside `$(...)` out of it, so no part can say it was not in one.
        opaque = False
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
            # A d4d call runs only its own subcommand: `derive core` in an
            # option value (the recorder's `--phase`) runs nothing, unless
            # the subcommand itself was not read (`d4d -v derive core`).
            opaque = len(sub) < 2 or any(word.startswith("-") for word in sub)
        else:
            reads = program in READ_ONLY_PROGRAMS and not (
                (program == "sed" and not _sed_reads_only(rest[1:]))
                or (program == "rg" and not _rg_reads_only(segment)))
            if not reads:
                read_only = False
            opaque = not reads
        runs_unknown[index] = opaque
        if full is not None and _mentions_derive(segment):
            if opaque or substitutes:
                out["derives"].append({"targets_full": None, "segment": index, "basis": "unparsed"})
            else:
                mentioning_readers.append(index)
    # A reader's words run where a pipe carries its output into a program
    # not read here (`echo '... derive core ...' | bash`, `| xargs d4d`,
    # #3384). Any such pipe later in the command counts, since a group
    # (`(echo ...; echo ...) | bash`) feeds every part inside it.
    piped_into_unknown = [j for j in range(1, len(segments))
                          if runs_unknown[j] and {"|", "|&"} & set(joins[j - 1])]
    for index in mentioning_readers:
        if any(j > index for j in piped_into_unknown):
            out["derives"].append({"targets_full": None, "segment": index, "basis": "unparsed"})
    out["derives"].sort(key=lambda row: row["segment"])
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
             reasons: list[str], runtime_denied: set[str] | frozenset = frozenset()) -> dict[str, Any]:
    """Every call that bears on the two files, sorted into successful Writes,
    unsettled Writes, refusals, other mutations and `derive core` runs.
    `runtime_denied` names the shell calls `_runtime_denials` corroborated."""
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
            # A call the native control refused (#3185), or the runtime in
            # `dontAsk` mode with its terminal listing to say so (#3201),
            # never ran.
            denial = ("native_denial" if _denied(result) else
                      "runtime_denial" if call["id"] in runtime_denied else None)
            # One row per part that derives the core, with that part's own
            # outcome (#3113): `targets_full` is None when its `--full`
            # cannot be placed.
            h["derives"].extend({**where, "segment": part["segment"], "targets_full": part["targets_full"],
                                 "outcome": _derive_outcome(result, part["basis"], denial is not None),
                                 "command_outcome": _shell_outcome(result), "status_basis": part["basis"]}
                                for part in shell["derives"])
            if shell["read_only"]:
                continue
            if denial is not None:
                # Refused before it ran: listed like a refused Edit, never a
                # possible change.
                h["rejected"].extend({**_where(call, result), "target": kind, "tool": name,
                                      "rejection": denial} for kind in shell["named"])
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
            if first is None or not row["_at"] > first["_settled"]:
                reasons.append(f"core derived ({row['tool_use_id']}) before the first full-record Write "
                               "had returned")
                continue
            derived = row
            break
        if row["outcome"] in ("ambiguous", "pending") and row["command_outcome"] == row["outcome"]:
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: its result is {row['outcome']}")
        elif row["outcome"] == "ambiguous":
            why = {"and_chain": "a later `&&` part may be what failed",
                   "unparsed": "a spelling of `derive core` the parser does not follow (a nested shell, "
                               "`xargs`, a substitution, or a wrapper or option it does not read)"}.get(
                row["status_basis"], "piped, backgrounded, grouped, after `||`, followed by `;`, or multi-line")
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: the call {row['command_outcome']} "
                           f"but its status is not the derive's own ({row['status_basis']}: {why})")
        elif row["outcome"] == "succeeded":
            reasons.append(f"derive core {row['tool_use_id']} cannot be placed: its --full cannot be resolved "
                           "(a variable, or a relative path with no known working directory: none recorded, or "
                           "after a directory change it may not have made)")
    # A non-Write change of the receipt issued after the draft, the last
    # receipt Write and the derive boundary had all returned reaches no
    # snapshot but the final one, which the sha256 against the file on disk
    # covers (#3112). Any earlier one may have changed a snapshot unseen.
    receipt_writes = h["writes"]["receipt"]
    # The snapshots are chosen by the order calls were issued, which is the
    # order they took effect only where no two relevant calls were in flight
    # together (#3268). A receipt Write issued before the draft that returned
    # after it may have landed on either side, and of two receipt Writes in
    # flight together either may have landed last; the transcript cannot say.
    # The draft is placed by the first-issued full-record Write alone: no
    # full record existed before it was issued, and one existed once it had
    # returned.
    in_flight = lambda a, b: not (a["_settled"] < b["_at"] or b["_settled"] < a["_at"])
    for i, row in enumerate(receipt_writes):
        for other in receipt_writes[i + 1:]:
            if in_flight(row, other):
                reasons.append(f"receipt Writes {row['tool_use_id']} and {other['tool_use_id']} were in flight "
                               "together: which landed last cannot be told")
        for label, boundary in (("the first full-record Write", first), ("the derive core boundary", derived)):
            if boundary is not None and in_flight(row, boundary):
                reasons.append(f"receipt Write {row['tool_use_id']} was in flight with {label} "
                               f"({boundary['tool_use_id']}): which took effect first cannot be told")
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
    h = _history(calls, results, [_Target("receipt", receipt), _Target("full", full)], reasons,
                 _runtime_denials(events, calls, results))
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
