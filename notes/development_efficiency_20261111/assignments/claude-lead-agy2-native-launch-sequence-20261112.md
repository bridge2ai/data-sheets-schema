# Assignment to AGY2: a first draft of the native launch sequence script

From the Claude lead, 2026-11-12. You write one new module and its tests in a worktree the lead made for you. Offline tests only. Nothing here launches anything.

## Standing

Your launch-input inventory is accepted (11 subcommands, 48 argument registrations; my own count of the subcommands agrees). This assignment builds on it.

## Why

Amendment N1, draft v8, requires that the capture, guard and launch commands of a native attempt run as **one reviewed sequence**: one script, no pause between the commands, a stop on any refusal or error, and **no automatic retry**. The time between the capture event and the reservation is limited, so nothing may be lost between steps. The script will be reviewed with the registration packet and pinned by sha256, so it has to be small and plain. The Codex helper wrote an unexecuted template for it; it is in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-critical-path-20261112.md` under "Exact operator sequence".

## Where you work

- Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112`, branch `agy/native-launch-sequence-20261112`, at the merged candidate with the freshness commit (`a68efbd687e5caa31223415e6397f6a66638f37b`). Leave your work uncommitted; the lead reviews and commits.
- Do not touch any other worktree, and nothing in `d4d-executions/launch-a21`.

## What to write

`src/data_sheets_schema/native_launch_sequence.py`, runnable as `python -m data_sheets_schema.native_launch_sequence`, and `tests/test_native_launch_sequence.py`.

Behaviour:

1. **Arguments:** the registration, the review bundle, the launch word, the account-choice file, the CI evidence, the capture root, the guard output path, and a packet directory for this run's outputs. Take the exact flags each of the three subcommands needs from your inventory; do not invent any.
2. **It runs three commands with the same interpreter that runs it,** in this order, each as a subprocess of `-m data_sheets_schema.native_generation`: `capture-subscription-event`, then `prepare-subscription-guard-v2` on the capture manifest the first command reported, then `launch` with the guard and the guard sha256 the second command reported.
3. **Each command's standard output is saved** to a new file in the packet directory before it is parsed. An existing output file is a refusal: the script never overwrites.
4. **Any nonzero exit, any output that is not the expected JSON, or a missing field stops the sequence** at once with a nonzero exit and a one-line reason. Nothing is retried. There is no loop.
5. **It records times:** a UTC timestamp before and after each command, written to a `sequence.json` in the packet directory at the end and also when it stops early.
6. **It takes no value from the environment** and passes the child an environment it does not edit. It prints no secret and reads none.
7. No other feature. No option to skip a step, to resume, to reuse an earlier capture, or to continue after a refusal.

How the first two commands report the capture manifest and the guard sha256 is in the Codex template (`.result.capture_manifest`, `.result.guard_sha256`). Check each field name against `native_generation.py` in your worktree and cite the line; if the source disagrees with the template, follow the source and say so.

Tests (offline; the three commands are replaced by a fake `native_generation` that the test puts first on the child's module path, or by patching `subprocess.run`):

- the three commands run in order with exactly the expected arguments;
- the capture manifest and the guard sha256 are passed on unchanged;
- a nonzero exit at each of the three steps stops the sequence and the later commands never start;
- malformed JSON and a missing field stop it;
- an existing output file is refused before any command starts;
- no command is ever started twice in one run;
- `sequence.json` is written on success and on an early stop.

Run them with `PYTHONPATH=<worktree>/src`, `-p no:cacheprovider`, and `--basetemp` under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy2-launch-sequence-20261112/`.

## Deliverables

- The two new files in your worktree, uncommitted.
- In the report worktree `codex-development-efficiency-20261111`: `notes/development_efficiency_20261111/handoffs/agy2-native-launch-sequence-20261112.md` with the answer first (what it does, what it refuses, the test counts from the saved pytest output), the source line for each field name you relied on, and anything in the source that surprised you. Compute every hash in the command that prints it.

## Rules

- Never run the real `native_generation` subcommands. No provider, model or native-binary call. No commit, push or GitHub write.
- Edit only the two new files. If you think another file must change, say so and stop.
- No at-sign characters in the handoff. Stop when done.
