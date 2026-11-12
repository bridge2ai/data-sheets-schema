# Assignment to AGY2: what a production native launch takes as input, as data

From the Claude lead, 2026-11-12. Read-only. No run of repository code.

## Why

The owner directed on 2026-11-12 (D134): the native agentic arm is the main result. Before the first native canary someone has to build the real registration, review bundle, launch word and the other input files. The lead needs to know exactly which inputs the launch commands take and which of them have a builder in the source today.

## Source

Commit `1a137b58860416a31618de44173180d021dfcc61`, read with `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show <commit>:<path>` and `git grep <pattern> <commit> -- <paths>`. Check first with `git cat-file -e` that the commit is present. Do not check anything out and do not import or execute any file from that commit.

## What I need

1. **Commands and arguments.** Parse `src/data_sheets_schema/native_generation.py` at that commit with Python's `ast` module (from the text that `git show` prints). For every subcommand: its name, and for every argument its flags, its destination name, whether it is required, and its help text.
2. **Where each argument is used.** For every argument destination, every line in that file where `args.<destination>` appears, with the line number and the stripped line.
3. **Builders.** For each of these words, every function definition in `src/` and `scripts/` at that commit whose name contains it, with file and line, split into test paths (`tests/`) and non-test paths: `registration`, `review`, `bundle`, `launch_word`, `word`, `account_choice`, `statement`, `runtime`, `capture`, `guard`, `ci_evidence`, `probe`. Use `git grep -n -E '^\s*def [A-Za-z0-9_]*<word>'`. List them; do not judge which one is the builder.
4. **Fixture builders.** The same search restricted to `tests/utils/`, as a separate list.

## Deliverables (in the report worktree `codex-development-efficiency-20261111`)

- `scripts/adhoc/native_launch_inputs_20261112.py`: does the extraction and writes the JSON. Header comment with purpose, inputs, outputs, date.
- `notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.json`
- `notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.md`: the tables printed by the script from the JSON, the command, and the counts (subcommands, arguments, builder functions outside tests, fixture builders). No row written by hand and no conclusion of your own.

## Rules

- No test run, no import of repository code, no checkout or branch switch in any worktree, nothing in `d4d-executions/launch-a21`, no GitHub write, no commit or push.
- Every name, line number and count comes from the script's output. Every path in backticks must exist.
- No at-sign characters.
- Stop when the three files are written. Print their paths and SHA-256.
