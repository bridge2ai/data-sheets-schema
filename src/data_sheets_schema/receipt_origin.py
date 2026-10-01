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

Only a successful Write, paired with its tool_result by id, changes state,
and on the receipt a successful Edit or MultiEdit, which the agentic
runtime's playbook permits and which is replayed exactly on the receipt as
it last stood (#3047): each `old_string` must occur once, or at least once
under `replace_all`, and a replay that cannot be exact is a reason -- one
with no earlier state to apply to (except an edit whose first `old_string`
is empty, which the runtime accepts only on an absent file or one whose
content is blank under JavaScript's `trim()`, and whose result is then the
whole `new_string`: it is replayed on the empty text, or on the blank
`originalFile` its result names, creating the receipt; an empty
`old_string` on a receipt that is not blank as replayed is a reason,
#3604), a string that does not occur or occurs
more than once without `replace_all`, a deletion the runtime may extend to
the following newline, a replacement carrying a `$` pattern a JavaScript
replace may expand, or a result whose metadata says the runtime applied
something else (a different `oldString`/`newString`/`replaceAll`, an
`originalFile` other than the replayed state, `userModified` or
`staleRecovered`). The final-sha256 check then holds a replayed receipt to
the file on disk as it holds a written one. A Write the runtime refused
(the unread-file wrapper, #2285) or that returned an error is listed and
changes nothing, and so is a shell call the native control denied: it
never ran (#3185). So is one the runtime
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
`nice` wrapper with options this reads is read through. A d4d call whose
program, or a wrapper's, is a variable or a relative path (`$PY -m
data_sheets_schema.cli`, `./d4d`) is read as one, but a `derive core` of
the full record it spells cannot be placed, as the program may be a
wrapper that did not run it, and no subcommand of it is read-only
(#3693). Nor can a `derive core` of the full record with an assignment
before its program -- on the part, given to `env`, as an earlier part of
the command or by `printf -v` (`PYTHONPATH=src python -m
data_sheets_schema.cli derive core`, `PATH=./bin:$PATH; d4d derive
core`) -- as the assignment may make the part run other code; no
assignment is exempt, `PYTHONPATH=src` included (#3781), and an earlier
part of appends or array elements (`PATH+=:./bin;`, `BASH_CMDS[d4d]=./x;`)
counts too. The assignment is read as the position rule reads one (#3689,
#3700): one made any other way -- by `export`, `declare` or `read`, in a
sourced script, a function or an `eval`, or outside the command -- is not
read as one, so a derive after `export PYTHONPATH=./hack;` is placed. Any
other part that carries the words `derive core` and is neither a d4d call
of another subcommand nor a program known to read is a derive that cannot
be placed (#3137): a nested `bash -c`, an `xargs`, or a wrapper option or CLI
option this does not read makes a part such a one (#3455). The words are matched after quote and escape
characters are removed, as the shell running a nested string removes them
(`bash -c 'd4d derive "core"'`), and `derive` followed by a word supplied
at run time (`$SUB`, `$(echo core)`, `xargs`'s `{}`) counts (#3397), as does
one carrying any replacement string an `xargs` in the command sets (`-I%`,
`-J %`, `-i`, `--replace`), and a `derive` that ends an `xargs` command
setting none, where xargs appends the word (#3426) -- ends it once the
shell's redirections are set aside (`2>&1`, `>log`, `< args`, #3453), and one with a
redirection directly after it in an xargs command, whatever follows the
redirection, since a quoted target holding spaces cannot be told from
arguments there (`xargs d4d derive <<< "core ..."`, #3457). A command the
tokenizer cannot split at all (an apostrophe in a here-document's body)
is not read part by part: it is tested whole, quote characters removed,
for the same words, and a match is a derive that cannot be placed (#3458),
a reader's words included. So is a reader part that carries them where a
pipe later in the command feeds a program not known to read (`echo '...
derive core ...' | bash`, `| xargs d4d`, #3384), and, in a command that
substitutes anywhere (`$(...)`, backticks, `<(...)`), every part that
carries them, readers and the recorder's `--phase` included: the parts
inside a substitution are split out of it, so none can be shown not to be
in one (#3385). A `derive core` call with a redirection among its words
rather than after them (`--full 2>/dev/null F`) cannot be placed either
(#3478). Last, a command-wide backstop (#3478-#3480): a call whose raw text
carries more whole-word `derive`s than the rules above gave rows (so a
`--help` row never accounts for a derive hidden beside it), where that text, quote and escape characters
removed, carries the word `derive` as a whole word anywhere -- inside a
substitution, an assignment, a `cd` part or an `xargs` argument included
-- and also a `d4d`, `data_sheets_schema` or `$`-variable invocation, is
one derive that cannot be placed. It does not depend on how the command
is spelled, and its cost is a false `unknown` for a call that only
mentions the word beside such an invocation (`grep 'd4d derive core'
notes.md`, the recorder's `--phase 'derive core'`). A derive whose words
are not on the command line at all (a script, an alias or function, `d4d
$SUB`, `python -c` building the argument list) is placed by position
instead (#3369): a shell call not denied that runs a program not read
here -- a part that is neither a reader, a directory change (the builtin
`cd`, `pushd` or `popd` as the part's first word after its assignments; a
path-qualified lookalike, `./cd`, or `poetry run cd`, is a program not
read, #3753), a d4d call of a literal subcommand, nor `linkml-validate` or `linkml-term-validator` with
options this reads (as the console script or as the `python -c` program
the pipeline spells each with), or such a part not run as its words name
(a variable or relative path as its program, an assignment before it or
as an earlier part, `printf -v` included, #3689, #3700, or for a `python
-c` or `python -m` part a directory change before it in the command, as
the interpreter imports from the directory it starts in first, #3699, and
for a part run through `poetry run` one too, as poetry takes its
virtualenv from the project that directory is in, #3723; a d4d `derive
core` call aimed at another record is held to the same, #3722), a
command or process substitution, whose inner command is not read (#3675),
or a command the tokenizer cannot split -- is a possible derive where one
would move the boundary: it had not
returned before the draft was issued, so a call issued before the draft
counts too (a backgrounded call's result is its launch -- its own
`run_in_background` input or its result's metadata says so, #3744 -- and
a part started with `&` -- at the top level or ending a command inside a
word a nested shell may run, which is read as that shell splits it where
the word has a space in it, `bash -c './derive.sh&echo started'`, #3745,
and the word a shell nested in that one gives its `-c`, or `eval` or `ssh`
runs, read so in turn, however deep, #3748, and otherwise only where a
space, `)`, `}`, `;`, `#` or the end follows the `&`, so `R&D` is text --
or by `coproc`, or by a program that detaches it, `setsid`, `screen`,
`tmux` and the like, may outlive it, so none of them has, #3674, #3690;
nor has a call that starts a process substitution, which bash does not
wait for (`true <(bash step.sh)`): a `<(` or `>(` outside quotes, one
anywhere after a command substitution opens, or one in a nested shell's
word with a space in it, #3752; a
command the tokenizer cannot split is open-ended where its whole text
carries such a `&`, by the rule for a word with no space, `coproc`,
detaching program or `<(` / `>(`, #3698, #3752; a script that detaches a child itself, or a
detaching program behind a wrapper not read, `sudo`, is not seen), it
was issued before the
derive boundary (if any), and a receipt change issued before that
boundary returned after both it and the draft were issued (#3697). The
runtime's shell keeps its directory between calls (#3719): after a call
not denied whose builtin `cd`, `pushd` or `popd` (or one `eval` runs, or
may run as a word supplied at run time, `eval "$X"`, #3815) may
leave it anywhere but where that call started -- plain, or behind a
brace, a compound keyword (`if`, `then`, `elif`, `else`, `while`,
`until`, `do`), `!`, `time`, `builtin` or `command` (#3797) -- or which
may run in it code not on its command line (#3782): `source` or `.`, or
a program named by a bare word this does not read, which may be a
function or an alias (not a path, a reader, a reserved word or builtin
that changes no directory, `poetry run` or a wrapper read here, a d4d
call, a validator or arithmetic, `(( i++ ))`) -- a later call's `python
-c`, `-m` or `poetry run` part is read as after a directory change in
its own command, and a relative `--full` in it cannot be placed. One in
a subshell, an unquoted command or process substitution (`(cd x)`,
`$(cd x)`, `<(cd x)`), a pipe's left side or a `&` job does not move
the shell, but it counts all the same, the rule's cost: which parts a
child runs is not read from the tokenizer's brackets and joins, since a
`)` or `|` it returns may come from a case pattern, a here-document
body, a backquote, a `${...}` or an arithmetic `$((...))`, where reading
it so placed a `--full` after a real change (#3810, #3904, #3911,
#3912); that waits for a shell grammar (#3830). A case pattern after
the first on a `case ... in` line, or on a line of its own, is read as a
command too (`a)`, `*)`), so its word may count; the first is read with
its `case` word. One in a
backquoted or double-quoted substitution (`` `cd x` ``, `"$(cd x)"`) is
kept inside one word and not read; it moves nothing (#3841), though a
backquoted command with a space in it is split, and its pieces are read
as parts. A command the tokenizer cannot split counts, whatever its
words (#3782). Wherever the transcript records a working directory
other than the first it records, such a part is read as after a change
too, and, where no earlier call's change was seen, a relative `--full`
resolves against the recorded directory, where the call started
(#3798). Where both hold, the earlier change decides and the `--full` is
not placed (#3812): a call's recorded directory may be one inherited
from the transcript's init event, which an earlier `cd` does not update,
so it is not trusted after one, even where the call's own event records
it (#3824 stays open: no transcript here records a per-event directory
to check the runtime's against); the cost is a false `unknown` in a
transcript that records the directory on every event. In the same
command, a directory change `eval` runs (or may run), or code run in
this shell as above, leaves no known directory for the parts after it,
as one behind a brace does (#3815).
A resumed run's next transcript starts afresh. A package in the
directory the session's shell started in that such a part imports first
is not read, nor a function or alias named as a program read here
(`cat() { cd x; }`), defined in the session or by the profile its shell
started with. The words before a command's program are read past wherever these
rules look for one: a redirection, with its target and any descriptor
before it (`2>/dev/null cd /tmp`, #3845), as well as the prefixes above.
A part whose program word bash builds at run time (a `$` or backquote
anywhere in it, a glob or a brace expansion: `$C /tmp`, `c${X}d /tmp`)
may be the builtin, and counts as a change; it may be a detaching
program, too, and makes the call open-ended (#3852). That is read at a
part's head, a real command position, and in the command of a
substitution a word carries whole (`"$($X ./derive.sh)"`), never in an
argument: `echo "$(bash derive.sh)"` is not such a part.
The command `eval` runs is its words joined by spaces and tokenised
again, which removes a second level of quotes, and each part of it is
read by the same rules however deep (`eval '"cd" /tmp'`, #3844); an
`eval` whose command carries a word supplied at run time, or cannot be
split, counts as a change and as open-ended (#3844, #3846). Every
argument of a shell program given `-c` in any option cluster is read as
a command it may run, since which word `-c` receives depends on the
options that take values (`bash -ceo pipefail 'cmd'`, #3843), and so is
the command `eval` runs and each run of `ssh`'s arguments to the end,
one of which is the command it runs remotely (#3846); a positional
argument read so is a false open-ended run, the rule's cost. Such a
command string that carries a word supplied at run time, or cannot be
split, may run anything, and is open-ended as an `eval` of it is (`bash
-c "$X"`, #3852). A command the tokenizer cannot split is open-ended
where any word in it starts with `$` or a backquote, as well as by the
text rules above.
Its cost is a false `unknown` for such a program that derived nothing. A
call the runtime backgrounded is ambiguous too: its result is the launch,
not the end. A
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
changed by anything other than a Write or a replayed edit (an edit whose
success is unsettled, any other tool given its path, or a shell command
that names it, is not known to be read-only and was not denied by the
native control; a command substitution -- backticks, `$(...)` unquoted or
double-quoted, `<(...)` or `>(...)` -- is never known to be read-only,
since the inner command is not parsed, #3240) where the change can reach
the pre-draft or derive-time snapshot, or the full record is changed that
way before its first Write; the first observed Write of either file updated
an existing file, or carries no create/update metadata to say it did not; a
`derive core` of the full record cannot be placed, or a shell call may have
run one unseen where it would move the boundary (#3369); a receipt Write was in
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
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

INSTRUMENT = "receipt_origin v6 (#2933, #3047, #3369, #3693, #3781, #3782)"
ORIGINS = ("contemporaneous", "phase1_correction", "phase3_backport")

#: The native runtime's refusal to overwrite a file the session has not read
#: (#2285), as the pinned `native_control.UNREAD_WRITE_MESSAGE` names it.
UNREAD_WRITE_ERROR = ("<tool_use_error>File has not been read yet. "
                      "Read it first before writing to it.</tool_use_error>")

#: Tools that only read. Any other tool given a path that names a tracked
#: file (NotebookEdit, ...) changes it other than by a Write, and so does an
#: edit of the full record or an unsettled edit of the receipt; a successful
#: edit of the receipt is replayed instead (`EDIT_TOOLS`, #3047).
READ_TOOLS = frozenset({"Read", "Grep", "Glob", "LS", "NotebookRead"})
#: The runtime's in-place edit tools, replayed on the receipt (`_replay`).
EDIT_TOOLS = frozenset({"Edit", "MultiEdit"})
#: A replacement pattern JavaScript's `String.prototype.replace` (and
#: `replaceAll`) expands in a string replacement when the search pattern is
#: a string: `$$`, `$&`, `` $` `` and `$'`. `$1`..`$99` and `$<name>` refer
#: to capture groups, which a string pattern has none of, so they stay
#: literal ("ab".replace("a", "$1x") is "$1xb"; #3555). Whether the runtime
#: passes the new string as a string or through a function (which expands
#: nothing) is not known here, so a replacement carrying one of the four
#: cannot be replayed exactly; a dollar amount such as "$10 million" can.
_JS_REPLACEMENT = re.compile(r"\$[$&`']")
# What JavaScript's `String.prototype.trim()` removes: WhiteSpace (tab, VT,
# FF, space, NBSP, BOM and every Zs character) and LineTerminator (#3604).
_JS_TRIM = frozenset("\t\v\f \u00a0\ufeff\n\r\u2028\u2029")


def _js_blank(text: str) -> bool:
    """`text.trim() === ""` in JavaScript: the runtime's test for a file an
    empty `old_string` may create over (#3604)."""
    return all(c in _JS_TRIM or unicodedata.category(c) == "Zs" for c in text)
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
    "a `derive core` run by anything other than a shell call in the transcripts given (a "
    "subagent's own calls, which are in its own transcript). One run without the words `derive "
    "core` on the command line (a script, an alias or function, a variable or substitution "
    "supplying the word `derive` itself (`d4d $SUB`), `python -c` building the argument list, "
    "or a file that an earlier call wrote the words into and a later call runs) is not placed "
    "by the words (#3137, #3384) but by position (#3369): a shell call that runs a program not "
    "read here -- neither a reader, a directory change (the builtin `cd`, `pushd` or `popd`; a "
    "path-qualified lookalike, `./cd`, or `poetry run cd`, is a program not read, #3753), a d4d "
    "call of a literal subcommand, nor "
    "`linkml-validate` or `linkml-term-validator` with options read here, each counted only where "
    "it runs what its words name: a bare name or an absolute path as its program, never a "
    "variable or a relative path (`$PY`, `./python`), and no assignment before it or as an "
    "earlier part (`PYTHONPATH=./hack`, `PATH=./bin:$PATH;`, `printf -v PATH`), #3689, #3700, "
    "nor, for a `python -c` or `python -m` part, a directory change before it in the command, "
    "since the interpreter imports from the directory it starts in first (#3699), nor, for a "
    "part run through `poetry run`, one either, since poetry takes its virtualenv from the "
    "project that directory is in (#3723), a d4d `derive core` call aimed at another record "
    "included (#3722) -- or runs a "
    "command or process substitution, whose inner command is not read (#3675), or cannot be "
    "split by the tokenizer, that had not returned "
    "when the draft was issued (one issued before the draft that returned after it, or one "
    "whose run is open-ended, counts: #3676), was issued before the derive boundary, and has a "
    "receipt change issued before that boundary returning after both it and the draft were "
    "issued (#3697), is a reason; its cost is "
    "a false `unknown` for such a program that derived nothing. A call's run is open-ended "
    "where the runtime backgrounded it (its `run_in_background` input or its result's metadata "
    "says so, #3744), a part is started with `&` (at the top level, or ending "
    "a command inside a word a nested shell may run: `bash -c './derive.sh &'`, and, as that "
    "shell splits a word with a space in it, `bash -c './derive.sh&echo started'` (#3745); in a "
    "word with no space, in a word inside that one that no program in it runs as a command (the "
    "argument a shell program's `-c` receives there, and `eval`'s and `ssh`'s, are read by the "
    "whole rule in turn, however deep, #3748: `bash -c \"bash -c './derive.sh&echo x'\"`), and in a "
    "command the tokenizer cannot split, only a `&` followed by a "
    "space, `)`, `}`, `;`, `#` or the end counts, so `R&D` does not) or by `coproc` "
    "(#3690), or a part's program detaches what it runs (`setsid`, `daemon`, `disown`, "
    "`screen`, `tmux`, `at`, `batch`, `systemd-run`, `start-stop-daemon`, #3674), read through "
    "`timeout`, `env`, `nice`, `nohup`, `exec` and `command` and as a command's first word "
    "inside such a nested word (#3690), or a part starts a process substitution, which bash does "
    "not wait for (`true <(bash step.sh)`: a `<(` or `>(` outside quotes, anywhere after a "
    "command substitution opens, or in a nested shell's word with a space in it, #3752), each "
    "read in the words a nested shell runs as a command however deep (#3748), and a "
    "command the tokenizer cannot split is open-ended where its whole text carries such a `&`, "
    "`coproc`, detaching program, `<(` or `>(` (#3698, #3752); a script "
    "or program that backgrounds or daemonises a "
    "child itself, or a detaching program behind any other wrapper (`sudo`, `xargs`), is not "
    "seen as open-ended, so where the call returned before the draft was issued a derive that "
    "child ran after it is missed. Nor is an environment set outside the command (exported "
    "earlier or inherited) read: a bare name is taken to be the program `PATH` finds, and an "
    "absolute path the program it names (#3689); nor is a package in the directory the session's "
    "shell started in that a `python -c` or `python -m` part imports before the installed one "
    "(a `linkml` or `data_sheets_schema` directory there, #3699), nor the project there whose "
    "virtualenv a `poetry run` part takes (#3723). A directory an earlier call left the shell in "
    "is read (#3719): after a call not denied whose builtin `cd`, `pushd` or `popd`, or one "
    "`eval` runs or may run as a word supplied at run time (`eval \"$X\"`, #3815), may leave "
    "anywhere but where it started (plain or behind a brace, a compound "
    "keyword, `!`, `time`, `builtin` or `command`, #3797), or which may run in that shell code not "
    "on its command line (#3782: `source` or `.`, or a program named by a bare word not read here, "
    "which may be a function or an alias -- not a path, a reader, a reserved word or builtin that "
    "changes no directory, `poetry run` or a wrapper read here, a d4d call, a validator or "
    "arithmetic), such a part counts as after a directory change and a relative `--full` cannot be "
    "placed. One in a subshell, an unquoted command or process substitution (`(cd x)`, `$(cd x)`, "
    "`<(cd x)`), a pipe's left side or a `&` job does not move the shell but counts all the same, "
    "the rule's cost: which parts a child runs is not read from the tokenizer's brackets and joins, "
    "where a `)`, `|` or `&` may come from a case pattern, a here-document body, a backquote, a "
    "`${...}` or an arithmetic `$((...))` (#3810, #3904, #3911, #3912; it waits for a shell grammar, "
    "#3830), and a case pattern is read as a command, so its word may count; one in a backquoted or "
    "double-quoted substitution is kept in "
    "one word, not read, and moves nothing (#3841), though a backquoted command with a space is "
    "split and its pieces read as parts; and a command the tokenizer cannot split counts, whatever "
    "its words (#3782). Where the transcript records a working directory other than its first, such "
    "a part counts as after a change too, and, where no earlier call's change was seen, a relative "
    "`--full` resolves against the recorded directory (#3798); where both hold the earlier change "
    "decides and the `--full` is not placed, as a recorded directory may be inherited from the init "
    "event and is not trusted after a change (#3812), even one the call's own event records (#3824), "
    "a false `unknown` in a transcript that records the directory on every event; in the same "
    "command a change `eval` runs, or code run in this shell as above, leaves no known directory "
    "for the parts after it "
    "(#3815). Before a command's program a "
    "redirection with its target and descriptor is read past (`2>/dev/null cd /tmp`, #3845), and a part "
    "whose program word bash builds at run time (a `$` or backquote anywhere in it, a glob or a brace "
    "expansion: `$C /tmp`, `c${X}d /tmp`) counts as a change and as open-ended, as it may be a "
    "detaching program (`$X ./derive.sh`, `$(which setsid) ./derive.sh`, #3852), read at a part's "
    "head and in the command of a substitution a word carries whole (`\"$($X ./derive.sh)\"`), never "
    "in an argument (`echo \"$(bash derive.sh)\"`); the command `eval` runs is its words joined and "
    "tokenised again, each part read by "
    "the same rules (`eval '\"cd\" /tmp'`, #3844), and one carrying a word supplied at run time or "
    "that cannot be split counts as a change and as open-ended (#3846); every argument of a shell "
    "program given `-c` is read as a command it may run (`bash -ceo pipefail 'cmd'`, #3843), and so "
    "are the command `eval` runs and each run of `ssh`'s arguments to the end (#3846), and such a "
    "command string that carries a word supplied at run time or cannot be split is open-ended "
    "(`bash -c \"$X\"`, #3852); a command the tokenizer cannot split is open-ended where any word "
    "in it starts with `$` or a backquote. Still not read: a function or alias named as a program "
    "read here (`cat() { cd x; }`), defined in the session or by the profile the session's shell "
    "started with; a program bash builds at run time behind `nohup`, `exec` or `command` "
    "(`nohup $X ./derive.sh`), which is not read as detaching; and, in a command the tokenizer "
    "cannot split, a program word built other than from a leading `$` or backquote (`set${X}sid`, "
    "a glob, a brace expansion), which is not read as detaching there (#3923); a brace expansion "
    "with a quoted or escaped space in it (`{cd,'/tmp/a b'}`, `{setsid,'./derive script.sh'}`), "
    "which the tokenizer splits so it is not read as built at run time (#3924); and a substitution "
    "whose command holds a case pattern's `)` (`\"$(case x in x) $X ./derive.sh;; esac)\"`), whose "
    "command is read only up to that `)` (#3925). Both wait for a shell grammar (#3830). "
    "A d4d call whose program, "
    "or a wrapper's, is a variable or a relative path (`$PY -m data_sheets_schema.cli`, `./d4d`) "
    "is read as one, but a `derive core` of the full record it spells cannot be placed, since "
    "the program may be a wrapper that did not run it, and no subcommand of it is read-only "
    "(#3693). Nor can a `derive core` of the full record with an assignment before its program, "
    "on the part, given to `env`, as an earlier part of the command or by `printf -v` "
    "(`PYTHONPATH=src python -m data_sheets_schema.cli derive core`, `PATH=./bin:$PATH; d4d "
    "derive core`), since the assignment may make the part run other code; no assignment is "
    "exempt, `PYTHONPATH=src` included, and the cost is a false `unknown` (#3781); an earlier part "
    "of appends or array elements (`PATH+=:./bin;`, `BASH_CMDS[d4d]=./x;`) counts too. An assignment "
    "made any other way (by `export`, `declare` or `read`, in a sourced script, a function or an "
    "`eval`, or outside the command) is not read as one, so a derive after `export "
    "PYTHONPATH=./hack;` is placed. The words are matched "
    "after quote and escape "
    "characters are removed, and `derive` followed by a word supplied at run time (`derive "
    "$SUB`, `derive $(echo core)`, `xargs ... derive {}`) counts as a derive that cannot be "
    "placed (#3397), as does a word carrying any replacement string an `xargs` in the command "
    "sets (`xargs -I% ... derive %`, `-J %`, `-i`, `--replace`) and a `derive` ending an `xargs` "
    "command that sets none, where xargs appends the word (#3426), redirections (`2>&1`, "
    "`>log`, `< args`) aside, since they are the shell's (#3453), and a `derive` with a "
    "redirection directly after it in an xargs command, whatever follows (#3457). A command "
    "the tokenizer cannot split (an apostrophe in a here-document body) is tested whole, "
    "quote characters removed, by the same rules (#3458). A derive call with a redirection "
    "among its words (`--full 2>/dev/null F`) cannot be placed (#3478). Last, a command-wide "
    "backstop (#3478-#3480): a call carrying more whole-word `derive`s than these rules gave "
    "rows, whose raw text, quote and "
    "escape characters removed, carries the word `derive` as a whole word anywhere (in a "
    "substitution, an assignment, a `cd` part, an `xargs` argument) beside a `d4d`, "
    "`data_sheets_schema` or `$`-variable invocation, is one derive that cannot be placed; its "
    "cost is a false `unknown` (`grep 'd4d derive core' notes.md`, the recorder's `--phase "
    "'derive core'`). So a word the shell builds some other way (a glob, `derive c*`), or one "
    "xargs appends after a `derive` mid-command, is left to the backstop, and what no word rule sees "
    "is a command with no whole word `derive`, or with one but no such invocation (a script, "
    "alias or program under another name: `run.sh derive core`), which is left to the position "
    "rule",
)

_ABSENT = object()
_LABEL = {"receipt": "receipt", "full": "full record"}
_OPERATORS = frozenset({"&&", "||", ";", "|", "&", "|&", "(", ")", ";;", ";&", ";;&"})
_PUNCT = frozenset("();<>|&")
_CLEAN_PATH = re.compile(r"[A-Za-z0-9_./+@-]+")
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
#: Any of bash's assignment words: `NAME=`, an append (`NAME+=`) or an array
#: element (`NAME[KEY]=`, `NAME[KEY]+=`). `_ASSIGNMENT` reads the first only,
#: and the rules that use it still read the others as a program; this reads
#: a part made of them alone as an assignment-only part (#3781).
_ASSIGNMENT_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\+?=.*")
_PYTHON = re.compile(r"python(\d+(\.\d+)*)?")
_VARIABLE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})")
_DURATION = re.compile(r"\d+(\.\d+)?[smhd]?")
_DERIVE_CORE = re.compile(r"(?<![\w.-])derive\s+(core(?![\w.-])|[$`{])")
#: Quote and escape characters, removed before the words are matched: the
#: outer tokenizer removes only the outer level, so inside a nested shell or
#: `eval` string `d4d derive "core"` still carries its quotes (#3397).
_QUOTING = re.compile(r"[\"'\\]")
#: A subcommand word spelled literally; anything else (`$SUB`, `{}`, a
#: substitution) is supplied at run time.
_LITERAL_WORD = re.compile(r"[A-Za-z0-9_-]+")
#: The command-wide backstop (#3478-#3480): the word `derive` anywhere in a
#: command, after quote and escape removal, and something that may invoke
#: the CLI -- `d4d`, `data_sheets_schema`, or a `$` variable that may hold
#: either.
_DERIVE_WORD = re.compile(r"(?<![\w.-])derive(?![\w.-])")
_INVOCATION = re.compile(r"(?<![\w.-])d4d(?![\w.-])|data_sheets_schema|\$\{?[A-Za-z_]")


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
    # The first working directory each transcript records, its init's or an
    # event's: where its shell started (#3719).
    start_of: dict[int, str] = {}
    for t, n, event in events:
        kind = event.get("type")
        if isinstance(event.get("cwd"), str):
            start_of.setdefault(t, event["cwd"])
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
                        "transcript": t, "line": n, "pos": len(calls), "cwd": cwd,
                        "start_cwd": start_of.get(t)}
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


def _backgrounded(result: dict | None, inputs: dict | None = None) -> bool:
    """The runtime ran the call in the background: its input asked for it
    (`run_in_background` other than absent or `false`, as the native phase
    history reads it), or its result's metadata names a background task.
    The input is read too because the metadata is per event and absent where
    an event carries several results or none (#3744)."""
    if isinstance(inputs, dict) and inputs.get("run_in_background") not in (None, False):
        return True
    metadata = result["metadata"] if isinstance(result, dict) else None
    return isinstance(metadata, dict) and bool(metadata.get("backgroundTaskId")
                                               or metadata.get("background_task_id"))


def _shell_outcome(result: dict | None, inputs: dict | None = None) -> str:
    """The same for a shell call's command as a whole, read as the phase
    history reads it: an explicit `is_error: false`, not interrupted, exit 0.
    A backgrounded call (`_backgrounded`, given the call's `inputs`) is
    `ambiguous`: its result is the launch, not the command's end (#3113)."""
    if result is None:
        return "pending"
    flag, metadata = result["is_error"], result["metadata"]
    if not isinstance(flag, bool):
        return "ambiguous"
    if flag:
        return "failed"
    if _backgrounded(result, inputs):
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
        # Only a string id is an id, as `reference_rescore` takes one: a list
        # or mapping there corroborates nothing, and is not hashed (#3454).
        listed = Counter(d["tool_use_id"] for d in denials
                         if isinstance(d, dict) and isinstance(d.get("tool_use_id"), str))
        for denial in denials:
            if not isinstance(denial, dict) or not isinstance(denial.get("tool_use_id"), str):
                continue
            identity = denial["tool_use_id"]
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


def _derive_outcome(result: dict | None, basis: str, denied: bool = False, inputs: dict | None = None) -> str:
    """A `derive core` part's own outcome from its call's result (#3113).
    `basis` says what the call's status tells about the part: `command` (it
    is the part's status), `and_chain` (a success is the part's; a failure
    may be a later part's), `none` (piped, backgrounded, grouped, after
    `||`, followed by `;`, or in a multi-line command), `unparsed` (a
    spelling the parser does not read, #3137), `unnamed_program` (a
    variable or relative-path program, which may be a wrapper, #3693) or
    `assigned_environment` (an assignment before the program, on the part,
    given to `env`, as an earlier part or by `printf -v`, which may make it
    run other code, #3781). A part whose status the
    result does not carry is `ambiguous`, unless the call was `denied` --
    by the native control or, corroborated, by the runtime (#3201) -- and
    so never ran. `inputs` are the call's, for `_backgrounded`."""
    overall = _shell_outcome(result, inputs)
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


def _process_substitutes(command: str) -> bool:
    """Whether the (comment-free) command may start a process substitution
    (`<(...)` or `>(...)`), which bash does not wait for: the substituted
    process can run on after the call's result (`true <(bash step.sh)`,
    #3752), as a part started with `&` does. That is a `<(` or `>(` outside
    quotes, as `_substitutes` reads it, or one anywhere after a command
    substitution opens (a backtick or `$(`), since the substitution's own
    command, quoted or not, may start one (`echo "$(cat <(./derive.sh))"`).
    Conservative: `$((a<(b)))` arithmetic and a quoted `'<('` inside a
    command substitution count too."""
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
            return bool(_PROCESS_SUBSTITUTION.search(command, i))
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


#: A word that starts with a `$` or a backquote, as a whole shell word:
#: in a command the tokenizer cannot split, any such word may be a
#: program supplied at run time, which may detach what it runs
#: (`_dynamic_program`, #3844, #3852).
_DYNAMIC_WORD = re.compile(r"(?<![^\s;&|(){}])[$`]")
#: The quote and escape characters the tokenizer removes (and a `$`
#: opening a `$'...'` or `$"..."` quote), dropped: a command the tokenizer
#: cannot split is also read in this form for a detaching program, so a
#: name spelled across quotes or escapes (`s\etsid`, `"setsid"`) is still
#: that name, as it is to bash and to the tokenised path (#3847).
_UNSPLIT_REMOVED = re.compile(r"\$(?=['\"])|[\"'\\]")
#: A `<(` or `>(` anywhere in a text, quotes not read: the rule for a
#: command the tokenizer cannot split (#3752), and for the rest of a
#: command once a command substitution opens.
_PROCESS_SUBSTITUTION = re.compile(r"[<>]\(")


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


#: bash's operators, longest first: its lexer takes the longest operator
#: at each point, and `_tokens` splits a run of operator characters the
#: same way (#3825). A function definition's `()` is kept as one word, as
#: the lexer always returned it: it is not a join, and the body after it
#: (`f() { cd x; }`) is defined, not run, so it heads no part of its own.
_SHELL_OPERATORS = ("&>>", ";;&", "<<<", "&&", "||", ";;", ";&", "|&", "&>", ">&", "<&", ">>", ">|",
                    "<>", "<<", "()", "(", ")", ";", "|", "&", "<", ">")


#: Arithmetic's brackets (`$((1+1))`, `(( i++ ))`), kept whole as words
#: as the lexer always returned them (#3840): arithmetic runs no command,
#: so neither is a join, and splitting them made `a && echo $((1+1))` read
#: as joins other than `&&` after `a`, which lost its `and_chain` basis.
#: A `))` that closes two substitutions or subshells at once stays one word
#: too; the join after it, if any, is still read.
_ARITHMETIC_WORDS = ("((", "))")


def _split_operators(run: str) -> list[str]:
    """A run of operator characters as the operators bash reads in it,
    each taken longest first as bash's lexer takes it, so `>&`, `&>`, `;;`
    and a definition's `()` stay whole while `);`, `)&&` and `)|` come
    apart (#3825). Arithmetic's `((` and `))` stay whole, as words
    (`_ARITHMETIC_WORDS`, #3840)."""
    out: list[str] = []
    i = 0
    while i < len(run):
        op = next((o for o in _ARITHMETIC_WORDS + _SHELL_OPERATORS if run.startswith(o, i)), run[i])
        out.append(op)
        i += len(op)
    return out


def _spaced_operators(text: str) -> str:
    """`text` with each unquoted, unescaped run of operator characters
    written as the operators bash reads in it, a space between each
    (#3825). shlex's `punctuation_chars` returns such a run as one token,
    so the `)` closing an unquoted `$(...)` came back joined to the
    operator after it (`$(pwd);cd data` gave `);`, and `$(pwd)&&cd` gave
    `)&&`), which `_layout` does not read as a join: the command after it
    stayed inside the substitution's part, and no rule that reads a part's
    head (a directory change, `eval`, a brace or keyword prefix, a derive,
    a validator, a reader) saw it. A quoted run (`grep '<(' f`, `echo
    ');'`) is text and is left as written."""
    out: list[str] = []
    i, n = 0, len(text)
    quote: str | None = None
    while i < n:
        ch = text[i]
        if quote is not None:
            if ch == "\\" and quote != "'" and i + 1 < n:
                out.append(text[i:i + 2])
                i += 2
                continue
            out.append(ch)
            if ch == quote[-1]:
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
            continue
        if ch == "$" and text[i + 1:i + 2] == "'":
            quote = "$'"
            out.append("$'")
            i += 2
            continue
        if ch in "'\"":
            quote = ch
        if ch in _PUNCT:
            j = i
            while j < n and text[j] in _PUNCT:
                j += 1
            out.append(" ".join(_split_operators(text[i:j])))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _tokens(command: str) -> list[str] | None:
    """The command's words and operators, or None when it does not tokenise.
    Comments are removed first, the way bash removes them, and the lexer's
    own comment rule is off: shlex ends a word at any `#`, which would drop
    everything after `s/#//g` (#3184). Each unquoted run of operator
    characters is split into bash's operators first (`_spaced_operators`,
    #3825), so a `;`, `&&`, `||` or `|` after an unquoted substitution's
    `)` is a join and the command after it heads its own part."""
    text = _spaced_operators(_newlines_as_joins(_strip_comments(command.replace("\\\n", " "))))
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
    """The arguments to the d4d CLI, when the segment's words name it: `d4d`,
    or `python* -m data_sheets_schema.cli` with the interpreter named or held
    in a variable (`$PY -m ...`, #3137). Whether the part runs what those
    words name is `_names_its_program`'s question (#3693)."""
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
    words, or inside one (`bash -c 'd4d derive core ...'`) (#3137), after
    quote and escape characters are removed as the shell that runs a nested
    string would remove them (`bash -c 'd4d derive "core"'`, `eval "d4d
    'derive' core"`, #3397). `derive` followed by a word supplied at run time
    (`derive $SUB`, `derive $(echo core)`, `xargs ... derive {}`) counts too:
    it may be `core`, so it is a derive that cannot be placed, never none.
    So does `derive` followed by a word carrying a replacement string that an
    `xargs` earlier in the same command sets with `-I`, `-J`, `-i` or
    `--replace` (`xargs -I% d4d derive %`), and `derive` as the last word of
    an `xargs` command that sets none, where xargs appends the word (#3426)."""
    text = _QUOTING.sub("", " ".join(segment))
    return bool(_DERIVE_CORE.search(text)) or _xargs_supplies_derive_word(text)


#: `xargs` options whose argument is the rest of the word or the next word;
#: `-I`/`-J` set a replacement string (GNU and BSD).
_XARGS_WITH_ARGUMENT = frozenset("IJLnPsEdaRS")
#: `xargs` options whose argument, if any, is only the rest of the word.
_XARGS_OPTIONAL_ARGUMENT = frozenset("iel")
_XARGS_LONG_WITH_ARGUMENT = frozenset({"--arg-file", "--delimiter", "--eof", "--max-lines", "--max-args",
                                       "--max-procs", "--max-chars", "--process-slot-var"})
#: A redirection operator, with any file-descriptor prefix (`2>`, `&>`,
#: `{fd}>`) and any target written against it (`2>&1`, `>/tmp/log`); `<(`
#: and `>(` are process substitutions, not redirections (#3453).
_REDIRECTION_OPERATOR = r"(?:\d+|\{[A-Za-z_][A-Za-z0-9_]*\})?(?:&>>|&>|>&|<&|>>|>\||<>|<<<|<<-?|>|<)(?!\()"
_REDIRECTION = re.compile(rf"({_REDIRECTION_OPERATOR})([^\s|;&()<>]*)")
_SHELL_WORDS = re.compile(rf"[<>]\(|{_REDIRECTION_OPERATOR}[^\s|;&()<>]*|[|;&()\n]+|[^\s|;&()<>]+")
_SEPARATOR_WORD = re.compile(r"[|;&()\n]+")


def _without_redirections(words: list[str]) -> tuple[list[str], list[bool]]:
    """`words` with every redirection and its target removed (#3453), and,
    for each word kept, whether a redirection came directly after it
    (#3457): a redirection is the shell's, so the program never sees it as
    an argument, and a `derive` before `2>&1` or `>log` is still the last
    word xargs receives. A bare operator (`>`, `2>`) takes the next word as
    its target. The command reaches here as the tokenizer's words joined by
    spaces, and shlex splits `2>&1` into `2`, `>&`, `1`, so a number or
    `{name}` word right before an operator is taken for its descriptor;
    where it was an argument (`derive 2 >&1`) the derive is then read as
    unplaceable, a false `unknown` rather than a miss. A quoted target
    holding spaces (`< "my args.txt"`, `<<< "core --full F"`) comes back
    here as several words, of which only the first is set aside; the flag
    is what keeps that from hiding the derive before it."""
    kept: list[str] = []
    redirected: list[bool] = []
    skip_target = False
    for at, word in enumerate(words):
        if skip_target:
            skip_target = False
            if not _SEPARATOR_WORD.fullmatch(word):
                continue
        if (re.fullmatch(r"\d+|\{[A-Za-z_][A-Za-z0-9_]*\}", word) and at + 1 < len(words)
                and _REDIRECTION.fullmatch(words[at + 1])):
            continue                                # the operator after it flags the word
        match = _REDIRECTION.fullmatch(word)
        if match:
            skip_target = not match.group(2)
            if redirected:
                redirected[-1] = True
            continue
        kept.append(word)
        redirected.append(False)
    return kept, redirected


def _backstop(command: str) -> bool:
    """The command-wide backstop (#3478-#3480): whether the raw command,
    quote and escape characters removed, carries the word `derive` as a
    whole word anywhere -- inside a substitution, an assignment, a `cd`
    part, an `xargs` argument, a redirection or an option value included --
    and also a `d4d`, `data_sheets_schema` or `$`-variable invocation.
    `_shell` applies it last, to a call the part-by-part reading gave no
    derive row, and a match is one derive that cannot be placed. Six review
    rounds each found a new spelling the special cases missed; this does not
    depend on how the command is spelled. Its cost is a false `unknown` for
    a call that only mentions the word beside such an invocation (`grep
    'd4d derive core' notes.md`, the recorder's `--phase 'derive core'`)."""
    return _backstop_count(command) > 0


def _backstop_count(command: str) -> int:
    """How many whole-word `derive`s the raw command carries, quote and
    escape characters removed; 0 when it names no d4d, `data_sheets_schema`
    or `$`-variable invocation. `_shell` adds an unparsed row when this
    exceeds the rows the part-by-part reading gave, so a row for one derive
    (`--help`, another record's) never accounts for a second one hidden in
    an assignment or substitution beside it (Codex review of #3374)."""
    text = _QUOTING.sub("", command)
    if not _INVOCATION.search(text):
        return 0
    return len(_DERIVE_WORD.findall(text))


def _redirection_interleaved(words: list[str]) -> bool:
    """Whether a redirection sits among a d4d call's words rather than after
    them (#3478): shlex splits `--full 2>/dev/null F` into `--full`, `2`,
    `>`, `/dev/null`, `F`, so the option would read `2` as its value. Only
    redirections (each with one target, and any descriptor word before its
    operator) may follow the first one; anything else means the words were
    not read as the program receives them, and the derive cannot be placed."""
    def operator(word: str) -> bool:
        return bool(word) and set(word) <= _PUNCT and ("<" in word or ">" in word)
    first = next((i for i, word in enumerate(words) if operator(word)), None)
    if first is None:
        return False
    j = first
    while j < len(words):
        if operator(words[j]):
            j += 2                                  # the operator and its target
        elif (re.fullmatch(r"\d+|\{[A-Za-z_][A-Za-z0-9_]*\}", words[j]) and j + 1 < len(words)
              and operator(words[j + 1])):
            j += 1                                  # a descriptor before its operator
        else:
            return True
    return False


def _xargs_supplies_derive_word(text: str) -> bool:
    """Whether an `xargs` in `text` supplies the word after `derive` at run
    time (#3426): through a replacement string (`-I%`, `-I %`, `-J %`, `-i`
    meaning `{}`, `-i%`, `--replace[=%]`, clustered as in `-0I%`) contained
    in that word, since `{}` is only a convention, or, with no replacement
    string, by appending it after a `derive` that ends the command -- read
    with the command's redirections removed, since they are the shell's
    (`xargs d4d derive 2>&1 | tail -5` still appends the word, #3453).
    A `derive` in an xargs command with a redirection directly after it
    counts whatever follows the redirection (#3457): a quoted target is
    re-split here (`xargs d4d derive <<< "core --full F"`, `< "my
    args.txt"`), so the words after it cannot be told from arguments, and
    reading them as arguments would hide a derive; the cost is a false
    `unknown` (`xargs d4d derive >log full`)."""
    words, redirected = _without_redirections(_SHELL_WORDS.findall(text))
    for start, word in enumerate(words):
        if os.path.basename(word) != "xargs":
            continue
        tokens: list[str] = []
        k = start + 1
        while k < len(words) and words[k].startswith("-"):
            option = words[k]
            k += 1
            if option == "--":
                break
            if option.startswith("--"):
                name, eq, value = option.partition("=")
                if name == "--replace":
                    tokens.append(value if eq else "{}")
                elif name in _XARGS_LONG_WITH_ARGUMENT and not eq:
                    k += 1
                continue
            for at, flag in enumerate(option[1:], start=1):
                rest = option[at + 1:]
                if flag in _XARGS_WITH_ARGUMENT:
                    if not rest:
                        rest = words[k] if k < len(words) else ""
                        k += 1
                    if flag in "IJ" and rest:
                        tokens.append(rest)
                    break
                if flag in _XARGS_OPTIONAL_ARGUMENT:
                    if flag == "i":
                        tokens.append(rest or "{}")
                    break
        end = k
        while end < len(words) and not _SEPARATOR_WORD.fullmatch(words[end]):
            end += 1
        command = words[k:end]
        for at, part in enumerate(command):
            if part != "derive":
                continue
            if redirected[k + at]:
                return True
            following = command[at + 1] if at + 1 < len(command) else None
            if following is None and not tokens:
                return True
            if following is not None and any(token in following for token in tokens):
                return True
    return False


#: The two schema validators the playbook runs, as the console script or as
#: the `python -c` program the pipeline itself spells them with
#: (`resources.linkml_validate`, `agentic_runtime.portable_text`), and the
#: options each may carry: `(valued, flags)`. An option outside them (a
#: `--config` file, `linkml-validate -m` loading a Python datamodel, an OAK
#: `--adapter`) is not admitted, since it may load code (#3369).
_VALIDATORS = {
    "linkml-validate": ("from linkml.validator.cli import cli; cli()", None,
                        frozenset({"-s", "--schema", "-C", "--target-class"}),
                        frozenset({"--exit-on-first-failure", "-D", "--include-context", "--no-include-context"})),
    "linkml-term-validator": ("from linkml_term_validator.cli import main; main()",
                              frozenset({"validate-data", "validate-schema", "validate"}),
                              frozenset({"-s", "--schema", "-t", "--target-class"}),
                              frozenset({"--bindings", "--no-bindings", "--dynamic-enums", "--no-dynamic-enums",
                                         "--labels", "--no-labels"})),
}


def _plain_word(word: str) -> bool:
    """Whether a program word names the program that runs (#3689): a bare
    name, looked up on `PATH` as the pipeline's console scripts are, or an
    absolute path, taken to be what its name says. A variable (`$PY`,
    `${PY}`, one the same command may assign), a substitution or a relative
    path (`./python`, `bin/linkml-validate`) may name any program."""
    return bool(word) and not any(c in word for c in "$`") and ("/" not in word or word.startswith("/"))


def _plainly_run(segment: list[str]) -> bool:
    """Whether the part runs the program its words name and nothing its
    environment adds (#3689): no assignment precedes the program, on the
    part itself or given to an `env` wrapper, since one (`PYTHONPATH`,
    `PATH`, `LD_PRELOAD`, ...) can make it load other code; and the program
    word, and every wrapper's, is a `_plain_word`. An environment set
    outside the command (exported earlier or inherited) is not read. A
    `derive core` part this rejects, or one after an assignment-only part
    or `printf -v`, is not placed (#3781)."""
    rest = list(segment)
    while rest:
        if _ASSIGNMENT.fullmatch(rest[0]):
            return False
        if rest[:2] == ["poetry", "run"]:
            rest = rest[2:]
            continue
        skip = _wrapper_skip(rest)
        if skip is None:
            break
        if not _plain_word(rest[0]) or skip >= len(rest):
            return False
        rest = rest[skip:]
    return bool(rest) and _plain_word(rest[0])


def _names_its_program(segment: list[str]) -> bool:
    """Whether the program word of a part, and every wrapper word
    `_unwrapped` reads through, is a `_plain_word` (#3693). A variable or a
    relative path (`$PY -m data_sheets_schema.cli`, `./d4d`) may name a
    wrapper rather than the interpreter or the CLI, so a `derive core` its
    words spell may not have run: the row is not placed. Assignments are
    `_plainly_run`'s part of the question, not this one; a derive with one
    is not placed either (#3781)."""
    rest = _program(segment)
    while (skip := _wrapper_skip(rest)) is not None and skip < len(rest):
        if not _plain_word(rest[0]):
            return False
        rest = _program(rest[skip:])
    return bool(rest) and _plain_word(rest[0])


def _imports_from_cwd(rest: list[str]) -> bool:
    """Whether a part (from its program on) is a `python*` interpreter run
    with `-c` or `-m`, which puts the directory it starts in first on
    `sys.path`: a `linkml` or `data_sheets_schema` package there is imported
    before the installed one (#3699). A console script run by a bare name or
    an absolute path puts its own `bin` directory there instead, which the
    working directory does not choose; one run through `poetry run` is
    `_poetry_run`'s case (#3723)."""
    return bool(rest) and bool(_PYTHON.fullmatch(os.path.basename(rest[0]))) and rest[1:2] in (["-c"], ["-m"])


def _poetry_run(segment: list[str]) -> bool:
    """Whether the part runs its program through `poetry run`, first or
    behind the assignments and wrappers `_unwrapped` reads (#3723). Poetry
    finds its project, and so the virtualenv whose `bin` supplies the
    program, from the `pyproject.toml` in the directory it starts in or the
    nearest above it: after a directory change the console script that runs
    (`linkml-validate`, `d4d`) is whatever that project installs."""
    rest = list(segment)
    while rest:
        while rest and _ASSIGNMENT.fullmatch(rest[0]):
            rest.pop(0)
        if rest[:2] == ["poetry", "run"]:
            return True
        skip = _wrapper_skip(rest)
        if skip is None or skip >= len(rest):
            return False
        rest = rest[skip:]
    return False


def _directory_builtin(segment: list[str]) -> str | None:
    """The directory-changing builtin a part runs -- `cd`, `pushd` or
    `popd` -- or None. It is that builtin only where the word, after the
    part's leading assignments, is exactly the builtin's name: bash finds a
    builtin before `PATH`, but `./cd`, `bin/pushd` or `/usr/bin/cd` names a
    file it runs as a program, and `poetry run cd` runs whatever `cd` its
    virtualenv's `PATH` finds (#3753). Such a lookalike changes no directory
    and runs a program not read here."""
    rest = list(segment)
    while rest and _ASSIGNMENT.fullmatch(rest[0]):
        rest.pop(0)
    return rest[0] if rest[:1] in (["cd"], ["pushd"], ["popd"]) else None


#: Words that stand before a command in the same part and leave it run by
#: this shell: a brace group's `{`, a pipeline's `!`, and the compound
#: keywords whose body or condition the segmenter keeps in the part that
#: follows them (`if`, `then`, `elif`, `else`, `while`, `until`, `do`).
#: A leading `((` is arithmetic's word (#3840), but where the arithmetic
#: does not parse bash reads it as two subshells (`((cd x); ls)`), so a
#: command behind it is read as the directory rule reads one in a
#: subshell: it counts.
_COMPOUND_PREFIXES = frozenset({"{", "!", "if", "then", "elif", "else", "while", "until", "do", "(("})


def _redirection_operator(word: str) -> bool:
    """Whether a token is a redirection operator (`>`, `2>`'s `>`, `>&`,
    `&>`, `<<`, `<<<`, ...): operator characters only, one of them `<` or
    `>`."""
    return bool(word) and set(word) <= _PUNCT and ("<" in word or ">" in word)


def _redirection_skip(rest: list[str]) -> int | None:
    """How many words a redirection at the head of `rest` takes -- its
    operator, the one target word after it, and a descriptor word (`2`,
    `{fd}`) before it -- or None where `rest` does not start with one
    (#3845). bash performs a redirection wherever it stands among a
    command's words, so `2>/dev/null cd /tmp` runs the builtin `cd`. The
    tokenizer keeps no spacing, so a number before an operator is always
    read as its descriptor: `2 >x cd y`, which runs a program `2`, is then
    read as a `cd`, a false move, the conservative side."""
    if len(rest) >= 2 and _redirection_operator(rest[0]):
        return 2
    if (len(rest) >= 3 and re.fullmatch(r"\d+|\{[A-Za-z_][A-Za-z0-9_]*\}", rest[0])
            and _redirection_operator(rest[1])):
        return 3
    return None


def _behind_prefixes(segment: list[str]) -> tuple[list[str], bool]:
    """The part from the command this shell runs behind any compound word
    (`_COMPOUND_PREFIXES`), `time` (and its `-p`), `builtin` or `command`
    (and its `-p`), or a redirection (`_redirection_skip`, #3845), with
    assignments dropped at each step, and whether any such word was there
    (#3797). None of them runs the command anywhere but
    in this shell, so `{ cd hack; }`, `if true; then cd hack; fi`, `builtin
    cd hack`, `command cd hack`, `time cd hack` and `! cd hack` each run the
    builtin `cd` in it. `command -v` or `-V` describes its word rather than
    running it: an empty part is returned for it."""
    rest, behind = list(segment), False
    while rest:
        while rest and _ASSIGNMENT.fullmatch(rest[0]):
            rest.pop(0)
        if not rest:
            break
        head = rest[0]
        if head in _COMPOUND_PREFIXES or head == "builtin":
            rest = rest[1:]
        elif (skip := _redirection_skip(rest)) is not None:
            rest = rest[skip:]                      # `2>/dev/null cd /tmp` (#3845)
        elif head == "time":
            rest = rest[1:]
            while rest[:1] in (["-p"], ["--"]):
                rest = rest[1:]
        elif head == "command":
            rest = rest[1:]
            while rest and rest[0].startswith("-") and rest[0] != "-":
                if rest[0] != "--" and set(rest[0][1:]) & {"v", "V"}:
                    return [], True
                rest = rest[1:]
        else:
            break
        if rest[:1] == ["--"] and head == "builtin":
            rest = rest[1:]
        behind = True
    return rest, behind


def _directory_builtin_behind(segment: list[str]) -> str | None:
    """The directory-changing builtin a part runs behind a word
    `_behind_prefixes` reads (`{ cd hack`, `then cd hack`, `builtin cd
    hack`, #3797), or None. `_directory_builtin` reads the plain form; this
    reads the rest, whose change the loop does not follow, so it leaves no
    known directory. One in a function body being defined (`f() { cd x; }`)
    is not read: the function is not run there."""
    rest, behind = _behind_prefixes(segment)
    return rest[0] if behind and rest[:1] in (["cd"], ["pushd"], ["popd"]) else None


def _eval_opaque(text: str) -> bool:
    """Whether the command `eval` runs, its words joined by spaces as eval
    joins them, is not known by its words: one supplied at run time (a `$`
    or a backquote anywhere in it) or one the tokenizer cannot split. Such
    an eval may run anything, so it counts as a possible directory change
    and as open-ended (#3844, #3846)."""
    return "$" in text or "`" in text or _tokens(text) is None


#: A brace expansion in a word (`{a,b}`, `{1..3}`), which bash expands
#: into words before it looks the program up (#3852).
_BRACE_EXPANSION = re.compile(r"\{[^{}\s]*(?:,|\.\.)[^{}\s]*\}")


def _built_at_run_time(word: str) -> bool:
    """Whether bash builds a program word at run time rather than taking it
    as spelled (#3852): a `$` or backquote anywhere in it (`$C`, `c${X}d`,
    the bare `$` the tokenizer leaves of `$(echo cd)`), a glob character
    (`*`, `?`, `[`, but not the programs `[` and `[[`), or a brace
    expansion. With `X` empty, `c${X}d` is `cd`."""
    return (any(c in word for c in "$`") or bool(_BRACE_EXPANSION.search(word))
            or (word not in ("[", "[[") and any(c in word for c in "*?[")))


def _dynamic_program(segment: list[str]) -> bool:
    """Whether the program the part runs, read through assignments, the
    wrappers `_unwrapped` reads or the words `_behind_prefixes` reads, is a
    word bash builds at run time (`_built_at_run_time`: `$C /tmp`, `` `echo
    cd` /tmp ``, `$(echo cd) /tmp`, `c${X}d /tmp`, a glob or a brace
    expansion). bash expands it before it looks the name up, so it may be
    the builtin `cd`, `pushd`, `popd` or `eval`, as the command an `eval` of
    a word supplied at run time may be (#3844), or a detaching program
    (#3852). It is read at a part's head only, a real command position, so
    `echo "$(bash derive.sh)"` is not such a part."""
    return any(rest[:1] and _built_at_run_time(rest[0])
               for rest in (_unwrapped(segment), _behind_prefixes(segment)[0]))


#: Reserved words and builtins that run no command a function, alias or
#: sourced script could supply and change no directory, taken by their
#: names as the readers are (#3782).
_STAYS_PUT = frozenset({"for", "case", "select", "in", "esac", "done", "fi", "}", "[[", "]]", ":", "false",
                        "alias", "unalias", "export", "set", "unset", "shift", "local", "declare", "typeset",
                        "readonly", "read", "wait", "exit", "return", "break", "continue", "exec"})


def _may_run_code_here(segment: list[str]) -> bool:
    """Whether the part may run, in this shell, code that is not on the
    command line and may change its directory (#3782): `source` or `.`
    (a script run in this shell), or a program named by a bare word this
    does not read, which may be a function or an alias defined earlier in
    the session. Read behind the words `_behind_prefixes` reads. Not such a
    part: a path (`./x`, `/usr/bin/x`), which bash runs as a file in a
    child process; a word built at run time, `_dynamic_program`'s; a
    function being defined (`f() { ...; }`); and a name read here -- a
    reader, a reserved word or builtin in `_STAYS_PUT`, a directory builtin
    or `eval` (read by their own rules), `poetry run` or a wrapper
    `_wrapper_skip` reads, whose program runs in a child, a d4d call or a
    validator. A function or alias named as one of those is not seen. Nor
    is an arithmetic command (`(( i++ ))`), which runs no command; only a
    part that is a whole arithmetic command (`((` at the program position
    and closing with `))`, #3922) is exempt, so `source env.sh
    $((1))` still counts (#3920). That exemption is this rule's alone, and
    the directory rules read the part as before."""
    rest = _behind_prefixes(segment)[0]
    if not rest:
        return False
    # `((` is read as a compound prefix, so an arithmetic command is the one
    # whose last prefix read is `((` (or whose head is, where it is not).
    read = segment[:len(segment) - len(rest)]
    # bash reads `((` as nested subshells unless the command closes with `))`
    # (#3922), so a part is exempt only when it is a whole arithmetic command.
    if ((read and read[-1] == "((") or rest[0] == "((") and segment[-1] == "))":
        return False
    head = rest[0]
    if head in ("source", "."):
        return True
    if rest[1:2] == ["()"] or head == "function" or not _plain_word(head) or "/" in head:
        return False
    if head in _STAYS_PUT or head in READ_ONLY_PROGRAMS or head in ("cd", "pushd", "popd", "eval"):
        return False
    if rest[:2] == ["poetry", "run"] or _wrapper_skip(rest) is not None:
        return False
    return _cli_args(rest) is None and not _validator(rest)


def _changes_directory(segment: list[str]) -> bool:
    """Whether the part may run a builtin `cd`, `pushd` or `popd`: plain,
    behind a word `_behind_prefixes` reads (a redirection included, #3845),
    in the command an `eval` runs (`_eval_may_change_directory`), or as a
    program word built at run time (`_dynamic_program`). Code a sourced
    script, a function or an alias runs is `_may_run_code_here`'s (#3782)."""
    return (_directory_builtin(segment) is not None or _directory_builtin_behind(segment) is not None
            or _eval_may_change_directory(segment) or _dynamic_program(segment))


def _eval_may_change_directory(segment: list[str]) -> bool:
    """Whether the part runs `eval` (plain, through a wrapper `_unwrapped`
    reads, or behind a word `_behind_prefixes` reads) on a command that may
    change this shell's directory. eval joins its words with spaces and
    parses the result as a command, removing a second level of quotes, so
    the joined text is tokenised again and each part of it read by the same
    rules, however deep (`eval '"cd" /tmp'`, `eval 'c\\d /tmp'`, #3844). A
    command that is opaque (`_eval_opaque`: a word supplied at run time, or
    text the tokenizer cannot split) may be a change (#3719, #3815), and so
    may a part of it that runs code not on the command line
    (`_may_run_code_here`, `eval myfunc`, #3782). `eval` runs its words in
    this shell, so the change holds for the parts after it and the calls
    after this one."""
    for rest in (_unwrapped(segment), _behind_prefixes(segment)[0]):
        if rest[:1] == ["eval"]:
            text = " ".join(rest[1:])
            if _eval_opaque(text) or any(_changes_directory(part) or _may_run_code_here(part)
                                         for part in _layout(_tokens(text) or [])[0]):
                return True
    return False


def _chosen_by_cwd(segment: list[str]) -> bool:
    """Whether the working directory may choose the code a part runs: a
    `python -c` or `-m` interpreter (`_imports_from_cwd`, #3699) or a program
    run through `poetry run` (`_poetry_run`, #3723)."""
    return _imports_from_cwd(_unwrapped(segment)) or _poetry_run(segment)


def _same_directory(a: str | None, b: str | None) -> bool:
    """Whether two directories are known to be the same, as spelled."""
    return a is not None and b is not None and os.path.normpath(a) == os.path.normpath(b)


def _printf_assigns(args: list[str]) -> bool:
    """Whether `printf`'s options carry `-v NAME` (or `-vNAME`), with which
    bash's builtin assigns the variable instead of printing (#3700)."""
    for word in args:
        if word == "--" or not word.startswith("-"):
            return False
        if word.startswith("-v"):
            return True
    return False


def _validator(rest: list[str]) -> bool:
    """Whether a part (from its program on) runs `linkml-validate` or
    `linkml-term-validator` with only the options `_VALIDATORS` admits: a
    program that validates the files it is given and cannot run a `derive
    core` (#3369). The program is the console script or a `python*`
    interpreter running the exact inline program, each named by a bare word
    or an absolute path, as the pipeline spells it: never a variable or a
    relative path (`$PY`, `./python`), which may name any program (#3689).
    Anything else, including another `python -c` program, is not."""
    if not rest or not _plain_word(rest[0]):
        return False
    program = os.path.basename(rest[0])
    args = None
    for name, (inline, commands, valued, flags) in _VALIDATORS.items():
        if program == name:
            args = rest[1:]
        elif _PYTHON.fullmatch(program) and rest[1:3] == ["-c", inline]:
            args = rest[3:]
        else:
            continue
        if commands is not None:
            if not args or args[0] not in commands:
                return False
            args = args[1:]
        i = 0
        while i < len(args):
            a = args[i]
            if a in valued:
                i += 2
            elif a in flags or not a.startswith("-") or a.split("=", 1)[0] in valued:
                i += 1
            else:
                return False
        return i == len(args)
    return False


#: Programs that start what they run detached from the call, so it may run
#: on after the call's result (#3674): `setsid` (with `-f`, or wherever it
#: forks), `daemon`, `disown`, `screen`/`tmux` sessions, `at`/`batch` jobs,
#: `systemd-run` and `start-stop-daemon`. `nohup` is not: it runs in the
#: foreground unless a `&` starts it, which the `&` rule reads.
_DETACHERS = frozenset({"setsid", "daemon", "disown", "screen", "tmux", "at", "batch", "systemd-run",
                        "start-stop-daemon"})
#: A `&` ending a command inside a word (a nested shell's command string):
#: not `&&`, `|&`, a redirection's `>&`, `<&` or `&>`; followed by a space,
#: `)`, `}`, `;`, a comment's `#` or the end. On its own this misses a `&`
#: followed directly by the next command (`./derive.sh&echo started`), which
#: in a word with no space in it cannot be told from a `&` inside a word
#: (`R&D`, `?a=1&b=2`); a word with a space in it is also read as the shell
#: reads it (`_nested_detaches`, #3745).
_NESTED_DETACH = re.compile(r"(?<![&|<>])&(?=[\s)};#]|$)")
#: Reserved words and prefixes that may stand before a command's program
#: without changing whether it detaches (#3690): a group or compound
#: opener, `!`, `time` (and its `-p`), and `nohup`, `exec` and `command`,
#: which run the program in the foreground.
_DETACH_PREFIXES = frozenset({"{", "!", "then", "do", "else", "elif", "if", "while", "until", "time", "-p",
                              "nohup", "exec", "command"})
#: bash's `coproc` starts its command asynchronously, and a non-interactive
#: shell exits without waiting for it, so it may run on after the call's
#: result as a `&` does (#3690).
_COPROC = "coproc"
#: The same, inside a word a nested shell may run (`bash -c 'coproc
#: ./derive.sh'`, `bash -c 'setsid ./derive.sh'`): `coproc` or a detaching
#: program as a command's first word, at the start of the word or after a
#: separator, an opening bracket or one of the prefixes above. Only a word
#: with a space in it is read so: a lone word (`grep at`) is an argument.
_NESTED_DETACHER = re.compile(
    r"(?:^|[;&|({\n])(?:\s*(?:[{!]|then|do|else|elif|if|while|until|time|-p|nohup|exec|command)(?=\s))*\s*"
    r"(?:coproc|(?:[^\s;&|()]*/)?(?:" + "|".join(re.escape(d) for d in sorted(_DETACHERS)) + r"))(?=[\s;&|)}]|$)")


#: Every operator of more than one character that carries a `&` and starts
#: nothing in the background: `&&`, `|&`, a case clause's `;;&` and `;&`,
#: and a redirection's `>&`, `<&`, `&>` and `&>>`. Derived from
#: `_SHELL_OPERATORS`, so an operator added there is excluded here too
#: (#3832: `;&` was missed when `;;&` was excluded by hand). They are
#: matched in one pass, left to right and longest first, as the lexer
#: reads them: `|&&` is `|&` then a background `&`, where removing `&&`
#: first, as a chain of replacements may, would leave no `&`.
_AMPERSAND_JOINS = re.compile("|".join(
    re.escape(op) for op in sorted((op for op in _SHELL_OPERATORS if "&" in op and len(op) > 1),
                                   key=len, reverse=True)))


def _lone_ampersand(token: str) -> bool:
    """An operator token that carries a `&` starting what precedes it in the
    background: never one of `_AMPERSAND_JOINS`, the operators of more than
    one character in `_SHELL_OPERATORS` that carry a `&` (`&&`, `|&`, a
    case clause's `;;&` or `;&`, a redirection's `>&`, `<&`, `&>` or
    `&>>`). `_tokens` splits an unquoted run into single operators (#3825),
    so a run such as `&)` reaches here only as a quoted word, which is read
    as the operators in it, conservatively."""
    return set(token) <= _PUNCT and "&" in _AMPERSAND_JOINS.sub("", token)


def _nested_detaches(word: str) -> bool:
    """Whether a `&` ends a command inside `word`, a string a nested shell
    may run: by `_NESTED_DETACH`, or, for a word with a space in it, as the
    shell splits that word -- a lone `&` among its tokens (`bash -c
    './derive.sh&echo started'`, #3745). A `&` the word quotes (`bash -c
    'echo "R&D team"'`) is text, and a word inside it is read here by
    `_NESTED_DETACH` alone; `_nested_open_ended` reads the words a shell
    nested in this one runs as a command by the whole rule (#3748). Its
    cost is a false open-ended run for such a word that is not a command, a
    message `R&D work`, where the call also runs a program not read."""
    if _NESTED_DETACH.search(word):
        return True
    if not re.search(r"\s", word):
        return False
    inner = _tokens(word)
    return inner is not None and any(
        _lone_ampersand(t) if set(t) <= _PUNCT else bool(_NESTED_DETACH.search(t)) for t in inner)


#: Shell programs whose arguments, given a `-c`, may be a command string,
#: and programs whose arguments make one: `eval` runs its arguments joined
#: in the shell, `ssh` its command on the host it names (#3748).
_SHELL_PROGRAMS = frozenset({"sh", "bash", "dash", "zsh", "ksh", "mksh", "ash"})
_COMMAND_ARGUMENTS = frozenset({"eval", "ssh"})


def _shell_command_strings(args: list[str]) -> list[str]:
    """The words a shell program's arguments may give its `-c` as the
    command string: every argument, where any argument is a short-option
    cluster carrying `c` (`-c`, `-lc`, `-ceo`), else none. Which word `-c`
    receives depends on how the options before it take values -- `-o NAME`,
    `+O NAME`, `--rcfile FILE` (#3813), and `o` or `O` inside a cluster,
    `bash -ceo pipefail 'cmd'` (#3843) -- so no word is chosen: each is read
    as one may be. The cost is a false open-ended run for a `$0` or a
    positional argument that reads as a command (`bash -c x 'a & b'`)."""
    given = any(len(a) > 1 and a[0] == "-" and a[1] != "-" and "c" in a[1:] for a in args)
    return list(args) if given else []


def _command_heads(tokens: list[str]):
    """Each part of a (nested) command from the program it runs: after
    assignments, `poetry run`, the prefixes `_DETACH_PREFIXES` names,
    `builtin`, a redirection (`_redirection_skip`, #3845) and the wrappers
    `_wrapper_skip` reads, in any order and repeated."""
    for segment in _layout(tokens)[0]:
        rest = _program(segment)
        while rest:
            if rest[0] in _DETACH_PREFIXES or rest[0] == "builtin":
                rest = _program(rest[1:])
                continue
            skip = _redirection_skip(rest)
            if skip is None:
                skip = _wrapper_skip(rest)
            if skip is None or skip >= len(rest):
                break
            rest = _program(rest[skip:])
        if rest:
            yield rest


def _command_strings(tokens: list[str]) -> list[str]:
    """The words of a (nested) command that a program in it runs as a
    command of their own (#3748), read from each part's `_command_heads`:
    every argument of a shell program given `-c` (`_shell_command_strings`,
    #3843); every argument of `eval` and the command eval runs, its
    arguments joined by spaces (`eval bash -c "'./derive.sh&echo x'"`,
    #3846); and every argument of `ssh` and each run of its arguments to
    the end joined by spaces, one of which is the remote command ssh
    builds after its options and destination, whatever they are (#3846).
    Any other word, `echo "R&D team"`'s included, is an argument, not a
    command."""
    out: list[str] = []
    for rest in _command_heads(tokens):
        program, args = os.path.basename(rest[0]), rest[1:]
        if program in _COMMAND_ARGUMENTS:
            out.extend(args)
            joins = [" ".join(args)] if program == "eval" else [" ".join(args[i:]) for i in range(len(args))]
            out.extend(j for j in joins if j and j not in args)
        elif program in _SHELL_PROGRAMS:
            out.extend(_shell_command_strings(args))
    return out


def _opaque_eval(tokens: list[str]) -> bool:
    """Whether a part of the command runs `eval` (read as `_command_heads`
    reads a part) on a command not known by its words (`_eval_opaque`: a
    word supplied at run time, `eval "$X"`, or text the tokenizer cannot
    split), which may start anything in the background (#3846)."""
    return any(rest[0] == "eval" and _eval_opaque(" ".join(rest[1:])) for rest in _command_heads(tokens))


def _nested_open_ended(word: str, *, command: bool = False) -> bool:
    """Whether `word`, a string a nested shell may run, may start what runs
    on after the call: a `&` ending a command in it (`_nested_detaches`),
    and, in a word with a space in it, `coproc` or a detaching program where
    a command starts (#3674, #3690) or a process substitution (#3752). The
    words a shell nested in it runs as a command (`_command_strings`: `bash
    -c "bash -c './derive.sh&echo x'"`) are read by the same rules in turn,
    however deep (#3748); any other word in it keeps the narrow rule, so
    `bash -c 'echo "R&D team"'` does not count. Its parts' programs are
    read as a top-level part's are (`_detacher`: `2>/dev/null setsid`,
    #3845), and an `eval` of a command not known by its words may start
    anything (`_opaque_eval`, #3846). Where `command` says the word is a
    command string a program runs (`_command_strings`), one carrying a word
    supplied at run time or that cannot be split may run anything, as an
    `eval` of it may (`bash -c "$X"`, `_eval_opaque`), and a program word
    built at run time at a command's head in it may be a detaching program
    (`_dynamic_program`, #3852); any other word is not read so, since it
    may be no command at all (`echo "$(bash derive.sh)"`)."""
    if _nested_detaches(word) or (command and _eval_opaque(word)):
        return True
    if not re.search(r"\s", word) and not command:
        return False
    if _NESTED_DETACHER.search(word) or _process_substitutes(word):
        return True
    inner = _tokens(word)
    return inner is not None and (_opaque_eval(inner) or any(_detacher(s) or (command and _dynamic_program(s))
                                                             for s in _layout(inner)[0])
                                  or any(_nested_open_ended(w, command=True) for w in _command_strings(inner)))


def _substitution_bodies(word: str) -> list[str]:
    """The commands inside the command substitutions a word carries whole
    (a quoted `"$(...)"` or a backquoted one, which the tokenizer keeps in
    one word), each read to its matching `)` by counting brackets, or to the
    end where none matches. Arithmetic's `$((` runs no command."""
    out, i = [], 0
    while i < len(word):
        if word.startswith("$(", i) and not word.startswith("$((", i):
            depth, j = 1, i + 2
            while j < len(word) and depth:
                depth += {"(": 1, ")": -1}.get(word[j], 0)
                j += 1
            out.append(word[i + 2:j - 1] if depth == 0 else word[i + 2:])
            i = j
        elif word[i] == "`":
            j = word.find("`", i + 1)
            out.append(word[i + 1:] if j < 0 else word[i + 1:j])
            i = len(word) if j < 0 else j + 1
        else:
            i += 1
    return out


def _substituted_runtime_program(word: str) -> bool:
    """Whether a command substitution a word carries whole runs, at a
    command's head, a program word built at run time (`"$($X ./derive.sh)"`,
    `_dynamic_program`), however deep, or cannot be split (#3852). Its
    other words are arguments: `"$(bash derive.sh)"` is not such a word."""
    for body in _substitution_bodies(word):
        inner = _tokens(body)
        if inner is None or any(_dynamic_program(s) for s in _layout(inner)[0]) or any(
                _substituted_runtime_program(t) for t in inner if not set(t) <= _PUNCT):
            return True
    return False


def _detacher(segment: list[str]) -> bool:
    """Whether the part is a `coproc`, or its program, or one a wrapper
    `_unwrapped` reads, a prefix `_DETACH_PREFIXES` names, `builtin` or a
    redirection (#3845) runs, is one of `_DETACHERS` (#3674, #3690). A
    program word built at run time (`$X ./derive.sh`) is
    `_dynamic_program`'s, read at a part's head (#3852)."""
    rest = _program(segment)
    while rest:
        if rest[0] == _COPROC or os.path.basename(rest[0]) in _DETACHERS:
            return True
        if rest[0] in _DETACH_PREFIXES or rest[0] == "builtin":
            rest = _program(rest[1:])
            continue
        skip = _redirection_skip(rest)
        if skip is None:
            skip = _wrapper_skip(rest)
        if skip is None or skip >= len(rest):
            return False
        rest = _program(rest[skip:])
    return False


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


def _shell(command: str, cwd: str | None, targets: list[_Target], *, moved: bool = False) -> dict[str, Any]:
    """What one shell command does to the tracked files: the targets it names,
    whether it is known to be read-only, and each part that derives the core
    (whether its `--full` is the tracked record, and what the call's status
    says about that part). `moved` says the call may not start where its
    session's shell started, as an earlier call changed directory or the
    transcript records another (#3719): a `python -c`/`-m` or `poetry run`
    part is then read as after a directory change in the command. A
    relative `--full` resolves against `cwd`; the caller passes None where
    that is not known (an earlier call's change) and the recorded directory
    where it is (#3798). `moves`
    in the result says the command itself may change the directory the next
    call starts in."""
    tokens = _tokens(command)
    named = [x for x in targets if x.name in command]
    # `runs_unread`: some part runs a program this does not read -- neither a
    # reader, a builtin directory change (#3753), nor a d4d call of a literal subcommand --
    # or the command substitutes one (#3675), so it may run a `derive core` whose words are not on the command line
    # (#3369).
    # A part counts only where it runs what its words name (`_plainly_run`,
    # after no assignment-only part: `PATH=./bin; cat x`), #3689.
    # `detaches`: a part is started with `&`, by `coproc` or by a program
    # that detaches it, so it may run on after the call's result, as a
    # backgrounded call does (#3674, #3690).
    out: dict[str, Any] = {"named": [], "read_only": False, "derives": [], "runs_unread": True,
                           "detaches": True, "moves": True}
    if tokens is None:
        # A command shlex cannot split (an apostrophe in a here-document's
        # body, #3458) is not read part by part, but the words may still be
        # on it: the whole command, quote characters removed, is tested for
        # them, and a match is a derive that cannot be placed, never none.
        out["named"] = [x.kind for x in named]
        full = next((x for x in targets if x.kind == "full"), None)
        if full is not None and (_mentions_derive([command]) or _backstop(command)):
            out["derives"].append({"targets_full": None, "segment": 0, "basis": "unparsed"})
        # Its run is open-ended by the same text rules a nested shell's word
        # with no space in it is read by, applied to the whole command (it
        # cannot be split, #3745): a `&` a space, `)`, `}`, `;`, `#` or the
        # end follows,
        # or `coproc` or a detaching program where a command may start (a
        # here-document body fed to a shell may carry either). Where neither
        # is there, a call that returned before the draft was issued could
        # not have derived after it (#3698). A `<(` or `>(` anywhere in it
        # may start a process substitution bash does not wait for (#3752).
        # A detaching program's name is read in the quote-removed form too
        # (`s\etsid ./derive.sh`, `"setsid" ./derive.sh`, #3847), and any
        # word starting with a `$` or a backquote may be a detaching program
        # supplied at run time (#3852).
        out["detaches"] = bool(_NESTED_DETACH.search(command) or _NESTED_DETACHER.search(command)
                               or _NESTED_DETACHER.search(_UNSPLIT_REMOVED.sub("", command))
                               or _PROCESS_SUBSTITUTION.search(command)
                               or any(_DYNAMIC_WORD.search(text)
                                      for text in (command, _UNSPLIT_REMOVED.sub("", command))))
        # Nor are its parts read for a directory change, so it counts as
        # one (#3782): any word at a command's start in it -- a here-document
        # body's line included, as the tokenised path reads one -- may be a
        # function, an alias, `source` or a builtin spelled across quotes or
        # an escape (`c\d /tmp`, #3847). Before #3782 its text was searched
        # for a `cd`, `pushd`, `popd` or `eval` word (#3719, #3839); every
        # such command now counts, which is at least that (a false
        # `unknown` is the cost).
        return out
    newline = "\n" in command.replace("\\\n", " ")
    segments, joins, leading = _layout(tokens)
    # A lone `&` (`_lone_ampersand`), never `&&`, `|&`, a case clause's
    # `;;&` or `;&`, or a redirection's `>&`, `<&`, `&>` or `&>>`; the same `&` ending a
    # command inside a word a nested shell may run (`bash -c './derive.sh &'`,
    # and `bash -c './derive.sh&echo started'` as that shell splits it, #3745);
    # or a part whose program detaches what it runs (`setsid`, `screen`,
    # `tmux`, ...), directly or under a wrapper `_unwrapped` reads (#3674),
    # or a `coproc`, at the top level or at a command's start inside such a
    # word, as a detaching program may be there too (#3690); or a process
    # substitution, which bash does not wait for (`true <(bash step.sh)`),
    # at the top level or in a word with a space in it that a nested shell
    # may run (`bash -c 'cat <(./derive.sh)'`), #3752.
    # The command an `eval` runs, its words joined, and the remote command
    # `ssh` builds are read so too (`_command_strings`, #3846), and an eval
    # of a command not known by its words (`eval "$X"`) may start anything.
    # So may a program word bash builds at run time at a command's head
    # (`$X ./derive.sh`, `$(which setsid) ./derive.sh`, `set${X}sid`), at
    # the top level, in a quoted substitution's command (`"$($X ./d)"`),
    # or in a command string a nested shell runs, which counts whole where
    # it carries a word supplied at run time (`bash -c "$X"`, #3852). Any
    # other word is an argument: `echo "$(bash derive.sh)"` is not.
    out["detaches"] = any(
        _lone_ampersand(t)
        or (not set(t) <= _PUNCT and (_nested_open_ended(t) or _substituted_runtime_program(t)))
        for t in tokens) or any(_detacher(s) or _dynamic_program(s)
                                for s in segments) or _process_substitutes(
        _strip_comments(command)) or _opaque_eval(tokens) or any(
        _nested_open_ended(w, command=True) for w in _command_strings(tokens))
    changes_directory = any(_program(s)[:1] in (["cd"], ["pushd"], ["popd"]) or _changes_directory(s)
                            or _may_run_code_here(s) for s in segments)
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
    # Per part: whether it may run a `derive core` whose words are not on the
    # command line (#3369): `runs_unknown`, less the two schema validators.
    may_derive = [False] * len(segments)
    # Whether an assignment-only part has run: it may set `PATH`,
    # `PYTHONPATH` or another variable the environment already exports, so a
    # later part may not run what its words name (#3689).
    assigned = False
    # `moved`: whether a directory change has run, in this command or, as
    # the caller says, an earlier call (#3719): `python -c` and `python -m`
    # put the directory they start in first on `sys.path`, so after one the
    # interpreter may import a `linkml` or `data_sheets_schema` package the
    # new directory holds rather than the installed one (#3699); `poetry
    # run` picks its project's virtualenv from that directory (#3723).
    # `leaves`: whether a change here may leave the shell somewhere other
    # than where the call started, for the calls after it (#3719); one back
    # to that directory (`cd /repo` run from `/repo`) does not.
    leaves = False
    mentioning_readers: list[int] = []
    for index, segment in enumerate(segments):
        before = leading if index == 0 else joins[index - 1]
        if unsettled and before != ["&&"]:
            local = None
            pushed = [None] * len(pushed)
        rest = _program(segment)
        if not rest:
            assigned = assigned or any(_ASSIGNMENT.fullmatch(word) for word in segment)
            continue
        # A part of assignments `_ASSIGNMENT` does not read -- an append or an
        # array element, `PATH+=:./bin`, or `BASH_CMDS[d4d]=./x`, after which
        # bash runs `./x` for `d4d` -- is still read below as a program not
        # read here, but it assigns as well, so a later part is not plainly
        # run and a derive after it is not placed (#3781).
        if all(_ASSIGNMENT_WORD.fullmatch(word) for word in segment):
            assigned = True
        program = os.path.basename(rest[0])
        # Only the builtin moves the directory, and only it leaves the loop
        # here: a path-qualified lookalike (`./cd`, `/usr/bin/cd`) or one run
        # through `poetry run` is a program like any other, read below as
        # one not read (#3753).
        change = _directory_builtin(segment)
        # One behind a brace, a compound keyword, `!`, `time`, `builtin` or
        # `command` (#3797), or a redirection (`2>/dev/null cd /tmp`, #3845),
        # runs the builtin in this shell too, but its part
        # is read below as the program it starts with, so it is not
        # followed: it leaves no known directory, for the parts after it
        # and for the calls after this one. Its `moved` changes nothing
        # today, as the part itself runs a program not read here (`{`,
        # `builtin`, `time`, ...) and so already makes the call unread; it
        # keeps the later parts right should such a part ever be read. A
        # change `eval` runs, or may run from a word supplied at run time,
        # is read the same way (#3815): `eval 'cd sub' && d4d derive core
        # --full data/X` runs the derive in `sub`, not where the call started.
        # So is a program supplied at run time (`$C /tmp`), which may be the
        # builtin (`_dynamic_program`).
        # So is a part that may run, in this shell, code not on the command
        # line (`_may_run_code_here`, #3782): `source`, `.`, or a program
        # not read here, which may be a function or an alias.
        if change is None and (_changes_directory(segment) or _may_run_code_here(segment)):
            unsettled = moved = leaves = True
            local = None
            pushed = [None] * len(pushed)
        if change is not None:
            reached = not newline and before in ([], [";"], ["&&"])
            unsettled = True
            moved = True
        if change in ("cd", "pushd"):
            if change == "pushd":
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
            leaves = leaves or not _same_directory(local, cwd)
            continue
        if change == "popd":
            local = pushed.pop() if pushed and len(rest) == 1 and reached else None
            if len(rest) > 1 or not reached:
                pushed = [None] * len(pushed)
            leaves = leaves or not _same_directory(local, cwd)
            continue
        # Whether the part may not run what its words name (#3689, #3699,
        # #3700, #3723): an assignment before it (on the part, to `env`, as an
        # earlier part or by `printf -v`), a variable or relative-path program
        # or wrapper, or, after a directory change, a program the new
        # directory chooses. A `derive core` part is held to it as well, since
        # one aimed at another record places nothing and must still count
        # where it may run something else (#3722).
        unplain = assigned or not _plainly_run(segment) or (moved and _chosen_by_cwd(segment))
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
            # A variable or relative-path program (`$PY -m
            # data_sheets_schema.cli`, `./d4d`) may be a wrapper that runs
            # something else, so its words say nothing of what it did
            # (#3693): no subcommand of it is read-only, and a derive it
            # spells is not placed. The words `derive core` elsewhere in
            # such a part are the backstop's (`_INVOCATION` matches `$`,
            # `d4d` and `data_sheets_schema`).
            named = _names_its_program(segment)
            if not named or sub not in READ_ONLY_D4D or any(
                    target.matches(o, local) is not False for o in outs for target in targets):
                read_only = False
            if sub == ("derive", "core") and full is not None:
                may_derive[index] = unplain
                spelled = _option(sub_args, "--full")
                if _redirection_interleaved(sub_args):
                    out["derives"].append({"targets_full": None, "segment": index, "basis": "unparsed"})
                    continue
                if not spelled:
                    verdict = False
                elif not _CLEAN_PATH.fullmatch(spelled[-1]):
                    verdict = None                  # a variable or glob: cannot be placed
                else:
                    verdict = full.matches(spelled[-1], local)
                # One whose `--full` names another record places nothing
                # either way, and the position rule holds it (#3722). Any
                # other is placed only where the part runs as its words
                # name it. A variable or relative-path program may be a
                # wrapper (#3693). An assignment before the program -- on the
                # part, given to `env`, as an earlier part of the command or
                # by `printf -v`: `assigned` or `_plainly_run`, as the
                # position rule reads one (#3689, #3700) -- may make the part
                # run other code (`PYTHONPATH=./hack`, `PATH=./bin:$PATH;`).
                # There is no allow-list, `PYTHONPATH=src` included (#3781,
                # the owner's decision of 2026-09-30): the cost is a false
                # `unknown`, never a false `checked`.
                if verdict is False:
                    basis = _status_basis(index, joins, leading, newline)
                elif not named:
                    verdict, basis = None, "unnamed_program"
                elif assigned or not _plainly_run(segment):
                    verdict, basis = None, "assigned_environment"
                else:
                    basis = _status_basis(index, joins, leading, newline)
                out["derives"].append({"targets_full": verdict, "segment": index, "basis": basis})
                continue
            # A d4d call runs only its own subcommand: `derive core` in an
            # option value (the recorder's `--phase`) runs nothing, unless
            # the subcommand itself was not read (`d4d -v derive core`).
            # Nor is a subcommand supplied at run time (`d4d derive $SUB`, #3397).
            opaque = len(sub) < 2 or not all(_LITERAL_WORD.fullmatch(word) and not word.startswith("-")
                                             for word in sub)
        else:
            reads = program in READ_ONLY_PROGRAMS and not (
                (program == "sed" and not _sed_reads_only(rest[1:]))
                or (program == "rg" and not _rg_reads_only(segment)))
            if not reads:
                read_only = False
            opaque = not reads
        runs_unknown[index] = opaque
        # A part read here (a reader, a d4d call, a validator) still counts
        # where it may not run what its words name (#3689).
        may_derive[index] = (opaque and not _validator(_unwrapped(segment))) or unplain
        # `printf -v NAME` assigns a shell variable, which a later part runs
        # under as it would after `NAME=...;` (`printf -v PATH %s ./bin;
        # linkml-validate`, #3700).
        if program == "printf" and _printf_assigns(rest[1:]):
            assigned = True
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
    # The command-wide backstop (#3478-#3480), after every rule above: a call
    # whose raw text carries more whole-word `derive`s than it gave rows, beside a d4d,
    # `data_sheets_schema` or `$`-variable invocation, anywhere in its raw
    # text, is one derive that cannot be placed. A false `unknown` is its cost.
    if full is not None and _backstop_count(command) > len(out["derives"]):
        out["derives"].append({"targets_full": None, "segment": 0, "basis": "unparsed"})
    out["derives"].sort(key=lambda row: row["segment"])
    out["read_only"] = read_only
    # The runtime's shell persists between calls, so a builtin directory
    # change, wherever it stands in the command, may leave the next call
    # starting elsewhere (#3719), unless it is known to go to the directory
    # the call started in. One behind a brace, a compound keyword, `!`,
    # `time`, `builtin` or `command` counts (#3797). One in a subshell
    # (`(cd x; ls)`), an unquoted command or process substitution (`X=$(cd
    # x; pwd)`, `<(cd x)`), a pipe's left side or a `&` job does not move
    # this shell, but it is read as one all the same, which is the rule's
    # cost: the segmenter does not say which parts a child runs, and
    # reading that from shlex's tokens has placed a `--full` after a real
    # parent-shell change more than once (#3810, #3904, #3911, #3912); it
    # waits for a shell grammar (#3830). One in a backquoted or
    # double-quoted substitution (`` X=`cd x` ``, `echo "$(cd x)"`) is not read, as the
    # tokenizer keeps it inside one word; it moves nothing, so nothing is
    # missed (#3841). `eval` runs its words in this shell, so a
    # `cd`, `pushd` or `popd` word among them counts too, behind those
    # words as well, and so does a word supplied at run time, which may
    # be one (`_eval_may_change_directory`, #3815): the loop above sets
    # `leaves` for each. The command eval runs is its words joined and
    # tokenised again, and one that is opaque counts (#3844); a redirection
    # before the builtin is read past (#3845); a program word built at run
    # time may be the builtin (`_dynamic_program`, #3852); and `source`,
    # `.` or a program not read here may run a sourced script, a function
    # or an alias that changes directory (`_may_run_code_here`, #3782).
    out["moves"] = leaves
    # A substitution runs its inner command inside one word of the part that
    # carries it (`echo "$(bash derive.sh)"`, `` echo `./derive.sh` ``, `cat
    # <(bash derive.sh)`), where no part is opaque; that command is not read
    # here, so the call may run a program this does not read (#3675), as a
    # substitution makes it not read-only (#3240).
    out["runs_unread"] = any(may_derive) or substitutes
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


def _replace(text: str, old: Any, new: Any, replace_all: Any) -> tuple[str | None, str | None]:
    """One edit applied exactly, or (None, why) when it cannot be (#3047)."""
    if not isinstance(old, str) or not isinstance(new, str):
        return None, "an `old_string` that is not a string, or a `new_string` that is not a string"
    if old == "":
        # The runtime accepts an empty `old_string` only on an absent file or
        # one blank under `trim()`, and its result is then the whole
        # `new_string`, whatever whitespace was there (#3588, #3604).
        if not _js_blank(text):
            return None, "an empty `old_string` on a receipt that is not blank as replayed"
        return new, None
    if replace_all not in (None, True, False):
        return None, "a `replace_all` that is not a boolean"
    found = text.count(old)
    if found == 0:
        return None, "its `old_string` does not occur in the receipt as replayed"
    if found > 1 and not replace_all:
        return None, f"its `old_string` occurs {found} times in the receipt as replayed, without `replace_all`"
    if new == "" and not old.endswith("\n") and old + "\n" in text:
        return None, "a deletion the runtime may extend to the newline after it"
    if _JS_REPLACEMENT.search(new):
        return None, "a `new_string` carrying a `$` pattern a JavaScript replace may expand"
    return (text.replace(old, new) if replace_all else text.replace(old, new, 1)), None


def _replay(name: str, inputs: dict, metadata: Any, prior: str) -> tuple[str | None, str | None]:
    """The receipt after a successful Edit or MultiEdit of `prior`, applied
    exactly as its input says, or (None, why) when the replay cannot be
    exact or the runtime's result metadata says it applied something else
    (#3047). A MultiEdit's edits apply in order, each to the text the one
    before it left."""
    if name == "Edit":
        edits = [{k: inputs.get(k) for k in ("old_string", "new_string", "replace_all")}]
    else:
        edits = inputs.get("edits")
        if not isinstance(edits, list) or not edits or not all(isinstance(e, dict) for e in edits):
            return None, "its `edits` is not a non-empty list of mappings"
    if isinstance(metadata, dict):
        if metadata.get("userModified") or metadata.get("staleRecovered"):
            return None, "its result says the edit applied was modified or the file changed since it was read"
        if isinstance(metadata.get("originalFile"), str) and metadata["originalFile"] != prior:
            return None, "its result's `originalFile` is not the receipt as replayed"
        if name == "Edit":
            said = {"oldString": inputs.get("old_string"), "newString": inputs.get("new_string"),
                    "replaceAll": bool(inputs.get("replace_all"))}
            if any(metadata.get(key) is not None and metadata[key] != value for key, value in said.items()):
                return None, "its result names a different edit from the one requested"
    text: str | None = prior
    for at, edit in enumerate(edits):
        text, why = _replace(text, edit.get("old_string"), edit.get("new_string"), edit.get("replace_all"))
        if text is None:
            return None, (why if name == "Edit" else f"edit {at}: {why}")
    return text, None


def _creates(name: str, inputs: dict) -> bool:
    """An Edit, or a MultiEdit whose first edit, has an empty `old_string`:
    the runtime's way to create a file with an edit tool (#3588)."""
    if name == "Edit":
        first = inputs
    else:
        edits = inputs.get("edits")
        first = edits[0] if isinstance(edits, list) and edits else None
    return isinstance(first, dict) and first.get("old_string") == ""


def _history(calls: list[dict], results: dict[str, dict], targets: list[_Target],
             reasons: list[str], runtime_denied: set[str] | frozenset = frozenset()) -> dict[str, Any]:
    """Every call that bears on the two files, sorted into successful Writes,
    unsettled Writes, refusals, other mutations, `derive core` runs and the
    shell calls that ran a program not read here (`unread`, #3369).
    `runtime_denied` names the shell calls `_runtime_denials` corroborated."""
    h: dict[str, Any] = {"writes": {"receipt": [], "full": []}, "unsettled": {"receipt": [], "full": []},
                         "mutations": [], "rejected": [], "derives": [], "unread": []}
    # Transcripts in which a shell call not denied may have changed the
    # directory: the runtime's shell keeps it, so every later call there may
    # start elsewhere (#3719). A resumed run's next transcript starts afresh.
    moved_in: set[int] = set()
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
                    h["writes"][target.kind].append({**where, "tool": name, "content": inputs["content"],
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
            # Where an earlier call changed directory the call's starting
            # directory is not known, whatever the transcript inherited from
            # its init; where the transcript records one other than where its
            # shell started, the call started there (#3719). Either way a
            # `python -c`/`-m` or `poetry run` part may take its code from it.
            # Only in the first is a relative `--full` unresolved: in the
            # second the recorded directory is where the call started, and
            # it resolves there (#3798). Where both hold, the first decides
            # (#3812): a call's `cwd` falls back to the init event's where
            # its own event records none, and an earlier `cd` does not move
            # that, so after one it is not trusted. The cost is a false
            # `unknown` where every event records the directory.
            earlier = call["transcript"] in moved_in
            elsewhere = (call["cwd"] is not None and call["start_cwd"] is not None
                         and os.path.normpath(call["cwd"]) != os.path.normpath(call["start_cwd"]))
            shell = _shell(command, None if earlier else call["cwd"], targets, moved=earlier or elsewhere)
            # A call the native control refused (#3185), or the runtime in
            # `dontAsk` mode with its terminal listing to say so (#3201),
            # never ran.
            denial = ("native_denial" if _denied(result) else
                      "runtime_denial" if call["id"] in runtime_denied else None)
            if shell["moves"] and denial is None:
                moved_in.add(call["transcript"])
            # One row per part that derives the core, with that part's own
            # outcome (#3113): `targets_full` is None when its `--full`
            # cannot be placed.
            h["derives"].extend({**where, "segment": part["segment"], "targets_full": part["targets_full"],
                                 "outcome": _derive_outcome(result, part["basis"], denial is not None, inputs),
                                 "command_outcome": _shell_outcome(result, inputs), "status_basis": part["basis"]}
                                for part in shell["derives"])
            if shell["runs_unread"] and denial is None:
                # A call that ran a program this does not read may have run
                # a `derive core` whose words are not on its command line
                # (#3369); `_boundaries` decides whether that could matter.
                # A backgrounded call's result is its launch, and a part
                # started with `&` may outlive the result: either may still
                # be running after it, so `_ran_until` is then open. The
                # call's own `run_in_background` says so where the result
                # carries no metadata (#3744).
                background = shell["detaches"] or _backgrounded(result, inputs)
                h["unread"].append({**where, "outcome": _shell_outcome(result, inputs),
                                    "_ran_until": None if background else where["_settled"]})
            if shell["read_only"]:
                continue
            if denial is not None:
                # Refused before it ran: listed like a refused Edit, never a
                # possible change.
                h["rejected"].extend({**_where(call, result), "target": kind, "tool": name,
                                      "rejection": denial} for kind in shell["named"])
            else:
                h["mutations"].extend({**where, "target": kind, "tool": name, "outcome": _shell_outcome(result, inputs)}
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
                elif state == "succeeded" and name in EDIT_TOOLS and target.kind == "receipt":
                    # Replayed on the receipt as it last stood (#3047). With
                    # no earlier state the row is the first change, which
                    # `_boundaries` reports; a failed replay is a reason here.
                    if any(target.matches(p, call["cwd"]) is None
                           for p in spelled if _touches(target, p, call["cwd"])):
                        reasons.append(f"{name} {call['id']} names the receipt by a relative path with no "
                                       "working directory")
                    earlier = h["writes"]["receipt"]
                    prior = earlier[-1]["content"] if earlier else None
                    created = "edit"
                    if not earlier and _creates(name, inputs):
                        # An empty first `old_string` is accepted only on an
                        # absent file or a blank one, and the result is the
                        # call's `new_string` either way (#3588). The text it
                        # edited is the blank `originalFile` its result names,
                        # else taken as empty (#3604).
                        said = result["metadata"].get("originalFile") if isinstance(result["metadata"], dict) else None
                        prior = said if isinstance(said, str) and _js_blank(said) else ""
                        created = "create"
                    content = None
                    if prior is not None:
                        content, why = _replay(name, inputs, result["metadata"], prior)
                        if why is not None:
                            reasons.append(f"{name} {call['id']} of the receipt (transcript {call['transcript']} "
                                           f"line {call['line']}) cannot be replayed: {why}")
                    earlier.append({**where, "tool": name, "content": content, "created": created})
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
        # An edit with an empty first `old_string` opens as "create" (#3588).
        opening = h["writes"][kind][0]["created"] if h["writes"][kind] else "create"
        if opening == "edit":
            reasons.append(f"the first observed change of the {_LABEL[kind]} is an edit: the text it "
                           "edited is not in the transcripts")
        elif opening == "update":
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
                   "unnamed_program": "its program is a variable or a relative path (`$PY -m "
                                      "data_sheets_schema.cli`, `./d4d`), which may name a wrapper that did "
                                      "not run the derive its words spell (#3693)",
                   "assigned_environment": "an assignment comes before its program, on the part, given to "
                                           "`env`, as an earlier part of the command or by `printf -v` "
                                           "(`PYTHONPATH=src`, `PATH=./bin:$PATH;`), which may make it run "
                                           "code other than the derive its words spell; no assignment is "
                                           "exempt (#3781)",
                   "unparsed": "a spelling of `derive core` the parser does not follow (a nested shell, "
                               "`xargs`, a substitution, a wrapper or option it does not read, a redirection "
                               "among its words, a command the tokenizer cannot split, or the command-wide "
                               "backstop: the word `derive` beside a d4d, `data_sheets_schema` or "
                               "`$`-variable invocation)"}.get(
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
    # A replayed Edit/MultiEdit sits among the receipt's Writes; each reason
    # names the tool the call used (#3556).
    for i, row in enumerate(receipt_writes):
        for other in receipt_writes[i + 1:]:
            if in_flight(row, other):
                pair = (f"receipt Writes {row['tool_use_id']} and {other['tool_use_id']}"
                        if row["tool"] == other["tool"] == "Write" else
                        f"receipt {row['tool']} {row['tool_use_id']} and receipt {other['tool']} "
                        f"{other['tool_use_id']}")
                reasons.append(f"{pair} were in flight together: which landed last cannot be told")
        for label, boundary in (("the first full-record Write", first), ("the derive core boundary", derived)):
            if boundary is not None and in_flight(row, boundary):
                reasons.append(f"receipt {row['tool']} {row['tool_use_id']} was in flight with {label} "
                               f"({boundary['tool_use_id']}): which took effect first cannot be told")
    # A `derive core` whose words are not on the command line (a script, an
    # alias or function, `d4d $SUB`, `python -c` building the argument list)
    # is not seen by the rules above (#3369). A shell call that ran a program
    # not read here could have run one, and that moves the boundary only
    # where it could have run once the full record existed (it had not
    # returned before the draft was issued), was issued before the derive
    # boundary (after it, the first derive has run), and a receipt change
    # issued before the boundary could have landed after a derive it ran:
    # settled after the call was issued and after the draft was issued,
    # since no derive ran before the full record existed (#3697). A receipt
    # change that returned before the draft was issued is in `pre_draft` and
    # `at_derive_core` alike whether the call derived or not. Anywhere else
    # the snapshots are the same whether it derived or not.
    h["possible_derives"] = []
    for row in h["unread"] if first is not None else []:
        if row["_ran_until"] is not None and row["_ran_until"] < first["_at"]:
            continue
        if derived is not None and not row["_at"] < derived["_at"]:
            continue
        if any(w["_settled"] > max(row["_at"], first["_at"]) and (derived is None or w["pos"] < derived["pos"])
               for w in receipt_writes):
            h["possible_derives"].append(row)
            reasons.append(f"Bash call {row['tool_use_id']} (transcript {row['transcript']} line {row['line']}) "
                           "runs a program this does not read and had not returned when the full record's first Write "
                           "was issued, was issued before "
                           + ("the derive core boundary" if derived is not None else "the end of the transcripts")
                           + ", with a receipt change after it: a `derive core` it ran without the words on "
                           "its command line would move the Phase 1 / Phase 3 boundary (#3369)")
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


def origin(transcripts: list[Path], receipt: Path, full: Path, *, receipt_at_run: Path | None = None,
           full_at_run: Path | None = None) -> dict[str, Any]:
    """The receipt-origin block for one run: its transcripts in order (a
    killed-and-resumed run's files, first invocation first), its coverage
    receipt and its full record. `receipt_at_run` and `full_at_run` name
    the two files as the transcript spelled them, where they have moved
    since the run (#3047): the transcript's calls are matched against those
    spellings, and the receipt read for the final sha256 is `receipt`."""
    reasons: list[str] = []
    info, events = _load([Path(p) for p in transcripts], reasons)
    calls, results = _pair(events, reasons)
    spelled_receipt = Path(receipt_at_run) if receipt_at_run is not None else Path(receipt)
    spelled_full = Path(full_at_run) if full_at_run is not None else Path(full)
    h = _history(calls, results, [_Target("receipt", spelled_receipt), _Target("full", spelled_full)], reasons,
                 _runtime_denials(events, calls, results))
    first, derived = _boundaries(h, reasons)
    writes = h["writes"]["receipt"]
    try:
        on_disk = _sha256(Path(receipt).read_bytes())
    except OSError as exc:
        on_disk = None
        reasons.append(f"the receipt cannot be read ({type(exc).__name__})")
    last = writes[-1] if writes else None
    rebuilt = _sha256(last["content"].encode("utf-8")) if last and last["content"] is not None else None
    if last is None:
        reasons.append("no successful Write of the receipt in the transcripts")
    elif on_disk is not None and rebuilt is not None and rebuilt != on_disk:
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
    # A successful edit of the receipt is replayed where its row carries the
    # text it left; one whose replay failed, or that followed a failed one
    # before the next successful Write of the receipt, carries None and is
    # listed apart (#3589). An edit after such a Write is replayed on the
    # Write's content (#3605).
    edit_rows = [w for w in writes if w["tool"] != "Write"]
    listed = lambda rows: [{k: v for k, v in strip(w).items() if k != "created"} for w in rows]
    block: dict[str, Any] = {
        "instrument": INSTRUMENT,
        "status": "unknown" if reasons else "checked",
        "reasons": reasons,
        "transcripts": info,
        "receipt": {"path": str(receipt), "at_run": str(receipt_at_run) if receipt_at_run is not None else None,
                    "sha256": on_disk, "rebuilt_sha256": rebuilt,
                    "writes": sum(1 for w in writes if w["tool"] == "Write"),
                    "edits": len(edit_rows)},
        "full": {"path": str(full), "at_run": str(full_at_run) if full_at_run is not None else None,
                 "writes": len(h["writes"]["full"])},
        "replayed_edits": listed(w for w in edit_rows if w["content"] is not None),
        "unreplayed_edits": listed(w for w in edit_rows if w["content"] is None),
        "boundaries": {"full_record_write": strip(first) if first else None,
                       "derive_core": strip(derived) if derived else None},
        "derive_core_attempts": [strip(r) for r in h["derives"]],
        "possible_unseen_derives": [strip(r) for r in h["possible_derives"]],
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
    replayed, unreplayed = len(block["replayed_edits"]), len(block["unreplayed_edits"])
    if replayed and block["receipt"]["rebuilt_sha256"] is not None:
        lines.append(f"receipt rebuilt from {block['receipt']['writes']} Write(s) and {replayed} replayed edit(s)")
    if unreplayed:
        lines.append(f"{unreplayed} successful edit(s) of the receipt not replayed")
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
