# AGY2 Handoff — First Draft of the Native Launch Sequence Script and Offline Tests (2026-11-12)

## Answer First

- **What `src/data_sheets_schema/native_launch_sequence.py` does**:
  - Runs as `python -m data_sheets_schema.native_launch_sequence` in worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112` (branch `agy/native-launch-sequence-20261112`, head `a68efbd687e5caa31223415e6397f6a66638f37b`, left uncommitted).
  - Accepts the 8 explicit CLI inputs (`allow_abbrev=False`): `--registration`, `--review`, `--launch-word`, `--account-choice`, `--ci`, `--output-directory`, `--subscription-guard` (alias `--output`), and `--packet-directory` (alias `--packet`).
  - Invokes the three `data_sheets_schema.native_generation` subcommands in strict order as subprocesses of `sys.executable -m data_sheets_schema.native_generation` with `stdin=subprocess.DEVNULL` and an unedited child environment:
    1. `capture-subscription-event` with `--registration`, `--review`, `--launch-word`, `--output-directory`, and `--account-choice`.
    2. `prepare-subscription-guard-v2` with `--registration`, `--review`, `--launch-word`, `--capture` set to the exact `.result.capture_manifest` string emitted by step 1, `--output` set to the guard output path, and `--account-choice`.
    3. `launch` with `--registration`, `--review`, `--ci`, `--launch-word`, `--subscription-guard` set to the guard output path, `--subscription-guard-sha256` set to the exact `.result.guard_sha256` string emitted by step 2, and `--account-choice`.
  - Saves each step's raw stdout to its new packet file (`capture-command.json`, `guard-command.json`, `launch-command.json`) with `O_CREAT | O_EXCL | O_NOFOLLOW` (`0600`) and `os.fsync` **before** checking the return code or parsing JSON.
  - Records microsecond-precision UTC timestamps (`YYYY-MM-DDTHH:MM:SS.ffffffZ`) before and after the overall sequence and before and after each step, writing `sequence.json` in the packet directory both on completion (`status: "completed"`) and on any early stop (`status: "stopped"`, with one-line `stop_reason`).
- **What `src/data_sheets_schema/native_launch_sequence.py` refuses**:
  - Any non-canonical or relative path, or any missing/symlinked parent directory, on any of the 8 path arguments.
  - Any missing, empty, oversized, symlinked, or non-regular input file among `--registration`, `--review`, `--launch-word`, `--account-choice`, and `--ci`, or a non-directory/symlink `--output-directory` or `--packet-directory`.
  - Any pre-existing file or symlink at `capture-command.json`, `guard-command.json`, `launch-command.json`, `sequence.json`, or `--subscription-guard` (`--output`), or a `--subscription-guard` path that collides with one of the four packet filenames; nothing is ever overwritten.
  - Any nonzero subprocess return code at any step (stops immediately after saving that step's raw stdout and recording its timestamps; never starts subsequent steps and never retries).
  - Any empty stdout, malformed or duplicate-key JSON (`native_subscription_guard.strict_json`), non-object JSON root, mismatched top-level `command` field, missing or empty `result` object, missing or empty `.result.capture_manifest` from step 1, missing or empty `.result.guard_sha256` (or mismatched `.result.path`) from step 2, or a step 3 `launch` result with `.result.state == "failed"` or `.result.runtime_gates_passed != True`.
  - Any flag to skip a step, resume, reuse an earlier capture, continue after an error, or abbreviate CLI flags (`allow_abbrev=False`).
- **Offline test counts from the saved pytest output (`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy2-launch-sequence-20261112/pytest-output.txt`)**:
  - **Collected**: `35 items`
  - **Passed**: `35 passed in 5.10s` (`0 failed`, `0 skipped`, exit code `0`)
  - Covers:
    - Exact 3-step ordering and byte-for-byte forwarding of `.result.capture_manifest` (`capture-subscription-event` -> `prepare-subscription-guard-v2 --capture`) and `.result.guard_sha256` (`prepare-subscription-guard-v2` -> `launch --subscription-guard-sha256`) (`1` test).
    - Verification inside the parser hook that each step's stdout file already exists on disk with identical bytes before JSON parsing begins (`1` test).
    - Nonzero exit at step 1, step 2, and step 3 stopping immediately without starting later steps and writing `sequence.json` (`status: "stopped"`) (`3` parametrized tests).
    - Empty stdout, malformed JSON, duplicate JSON keys, non-object JSON root, missing/empty `result`, mismatched `command`, missing/empty `.result.capture_manifest`, missing/empty `.result.guard_sha256`, mismatched `.result.path`, and `launch` returning `.result.state == "failed"` or `.result.runtime_gates_passed == False` (`18` parametrized tests).
    - Refusal of pre-existing output files (`capture-command.json`, `guard-command.json`, `launch-command.json`, `sequence.json`, and `--subscription-guard`) before any command starts, leaving existing file bytes untouched (`5` parametrized tests).
    - Real subprocess execution (`sys.executable -m data_sheets_schema.native_launch_sequence`) with a fake `data_sheets_schema.native_generation` placed first on `PYTHONPATH`, verifying unedited child environment propagation and `sequence.json` creation (`1` test).
    - Verification that `tests.utils.run_spec_boundaries.discover` finds `0` RunSpec boundary candidates in `src/data_sheets_schema/native_launch_sequence.py` (`1` test).
    - Input preflight refusal on reserved packet filename collision and missing input file (`1` test).
    - Parser rejection of `--skip`, `--resume`, `--reuse-capture`, and `--continue-on-error` (`4` parametrized tests).

---

## Source Lines for Every Relied-On Field Name and CLI Flag

All line numbers below are in worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112` at commit `a68efbd687e5caa31223415e6397f6a66638f37b`:

| Subcommand / Artifact | Field or Flag | Source File and Line(s) | Exact Definition in Source |
|---|---|---|---|
| All `native_generation` subcommands | Top-level JSON envelope (`command`, `result`, `account_choice_sha256`, `account_choice_basis`, `account_label`, `effort`, `selected_receipt_instrument`, `verification_scope`) | `src/data_sheets_schema/native_generation.py` lines `63-81` | `_emit(command, result, ..., account_choice=args.account_choice)` sets `"result": result` (line `77`) and `"command": command` (line `81`) and prints `guard.canonical(payload).decode("utf-8")` |
| All `native_generation` subcommands | `--account-choice` | `src/data_sheets_schema/native_generation.py` lines `137-140` | `sub.add_argument("--account-choice", required=True, help="Closed D105/D106 account-choice path")` |
| Step 1: `capture-subscription-event` | `--registration`, `--review`, `--launch-word`, `--output-directory` | `src/data_sheets_schema/native_generation.py` lines `117-120` | `_add_common(capture)` (`--registration`, `--review`, `--launch-word` at lines `111-114`) + `capture.add_argument("--output-directory", required=True)` (line `120`) |
| Step 1: `capture-subscription-event` | `.result.capture_manifest` and `.result.sha256` | `src/data_sheets_schema/native_generation.py` lines `232-235` | `path = probe.capture_subscription_event(...)` then `result = {"capture_manifest": str(path), "sha256": guard.sha(_read(path))}` (line `235`) |
| Step 2: `prepare-subscription-guard-v2` | `--registration`, `--review`, `--launch-word`, `--capture`, `--output` | `src/data_sheets_schema/native_generation.py` lines `125-128` | `_add_common(prep2)` (`--registration`, `--review`, `--launch-word` at lines `111-114`) + `prep2.add_argument("--capture", required=True)` (line `127`) + `prep2.add_argument("--output", required=True)` (line `128`) |
| Step 2: `prepare-subscription-guard-v2` | `.result.guard_sha256` and `.result.path` | `src/data_sheets_schema/native_generation.py` lines `236-247` | `raw = guard.write_guard(...)` then `result = {"guard_sha256": guard.sha(raw), "path": args.output}` (line `247`) |
| Step 3: `launch` | `--registration`, `--review`, `--ci`, `--launch-word`, `--subscription-guard`, `--subscription-guard-sha256` | `src/data_sheets_schema/native_generation.py` lines `129-133` | `_add_common(launch_cmd)` (`--registration`, `--review`, `--launch-word` at lines `111-114`) + `--ci` (line `131`), `--subscription-guard` (line `132`), `--subscription-guard-sha256` (line `133`) |
| Step 3: `launch` | `.result` (`final` dict with `state`, `runtime_gates_passed`, `attempt_id`, `first_stop`) | `src/data_sheets_schema/native_generation.py` lines `259-265`; `src/data_sheets_schema/native_shared_execution_orchestration.py` lines `80-104`; `src/data_sheets_schema/native_execution_orchestration.py` lines `609-641` | `native_generation.py` line `262` assigns `result = shared_orchestration.launch(...)`, which delegates to `native_execution_orchestration.launch(...)` returning `final` with `'state': 'completed_pending_independent_review' if completed else 'failed'` (line `611`) and `'runtime_gates_passed': completed` (line `612`) |
| Strict JSON & canonical bytes helpers | `strict_json`, `canonical`, `read_regular`, `sha` | `src/data_sheets_schema/native_subscription_guard.py` lines `94-129` | `sha` (line `94`), `canonical` (line `98`), `strict_json` rejecting duplicate keys and non-finite constants (lines `102-119`), `read_regular` enforcing bounded regular non-symlink files (lines `122-129`) |

---

## Surprises Found in the Source

1. **`launch` exits with return code `0` even when post-reservation child execution or runtime gates fail**:
   - In `src/data_sheets_schema/native_execution_orchestration.py` (lines `477-485`, `535-538`, `609-641`), exceptions raised after attempt reservation during child invocation, runtime observation, or post-run gate/replay verification are caught, recorded inside `final.json` (`'state': 'failed'`, `'runtime_gates_passed': False`, `'first_stop': ...`), and returned normally in the `final` dict rather than re-raised.
   - `src/data_sheets_schema/native_generation.py` (lines `262-271`) then emits that `final` dict inside `.result` and returns `0`.
   - Because relying on `completed.returncode != 0` alone would treat a post-reservation failed launch as a sequence success, `native_launch_sequence.py` (lines `317-320`) also inspects `launch_result.get("state") == "failed"` and `launch_result.get("runtime_gates_passed") is not True` and fails fast with exit code `1` and a one-line stop reason in `sequence.json`.
2. **Step 2 and Step 3 use different flag names (`--output` vs `--subscription-guard`) for the same guard file path**:
   - `prepare-subscription-guard-v2` takes `--output` (`native_generation.py` line `128`), whereas `launch` takes `--subscription-guard` (`native_generation.py` line `132`) for the exact same guard file.
   - `native_launch_sequence.py` accepts `--subscription-guard` (with `--output` as an alias, `dest="subscription_guard"`) and forwards it as `--output` to step 2 and `--subscription-guard` to step 3.
3. **No packet-directory flag exists in `native_generation.py`**:
   - In the Codex shell template (`codex-native-critical-path-20261112.md` lines `213`, `225`, `238`), `$PACKET` is a shell redirection directory (`> "$PACKET/capture-command.json"`), not a `native_generation.py` CLI flag.
   - `native_launch_sequence.py` defines `--packet-directory` (with `--packet` alias) for `capture-command.json`, `guard-command.json`, `launch-command.json`, and `sequence.json`.
4. **`native_subscription_guard.read_regular` rejects 0-byte files before JSON parsing**:
   - `guard.read_regular` (`native_subscription_guard.py` line `126`) checks `0 < st.st_size <= limit` and raises `Refusal("subscription evidence is not a bounded regular file")` when a file is 0 bytes.
   - When a child command produces empty stdout (`b""`), `native_launch_sequence.py` writes the 0-byte `*-command.json` file first and then checks `output_path.stat().st_size == 0` in `_parse_saved_step_output` (lines `113-114`) before calling `guard.read_regular`, so empty stdout is reported specifically as `<subcommand> produced empty stdout`.

---

## File Hashes (Computed in Command Output)

Computed via `shasum -a 256`:

```text
a48aba89c9d0d34de485dac17b5c4695357b368f6abcada7a418120663c329ae  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/src/data_sheets_schema/native_launch_sequence.py
82ab009e230ff8d4613c234657ae7053cd859ffd6d821b2bef4cd59456a39642  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/tests/test_native_launch_sequence.py
0c536e44144a30a02c1cb5224bfba68721e4ec2be7287ba12e71688f8640da73  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy2-launch-sequence-20261112/pytest-output.txt
265112dcffac32b3b46c3e810fa590ef075e7d43883c67173f28ac41fab25a0a  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/src/data_sheets_schema/native_generation.py
13573951995c5e7d27b164feaab1b328dad09b33c8dce9ff53afa50ec360a89b  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/src/data_sheets_schema/native_execution_orchestration.py
c77d692deafafb483e8ccf0781cad9434f1aee14aa4585fec4a2269d081025e5  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/src/data_sheets_schema/native_shared_execution_orchestration.py
ab72f90faf0b4ba6150a5dd53d1f832feb4f0f5496485734228b00c613c65edc  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-launch-sequence-20261112/src/data_sheets_schema/native_subscription_guard.py
```
