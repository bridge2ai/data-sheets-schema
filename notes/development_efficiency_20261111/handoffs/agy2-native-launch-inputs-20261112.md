# Production Native Launch Inputs and Builder Inventory (2026-11-12)

## Command and Provenance

- Assignment file: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy2-native-launch-inputs-20261112.md`
- Extraction script: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_launch_inputs_20261112.py`
- Structured JSON output: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.json`
- Markdown handoff output: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-native-launch-inputs-20261112.md`
- Repository git object store: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`
- Commit read via git show and git grep: 1a137b58860416a31618de44173180d021dfcc61
- CLI module parsed with Python ast: src/data_sheets_schema/native_generation.py

```bash
python3 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/native_launch_inputs_20261112.py
```

## Summary Counts

| Metric | Count |
|---|---:|
| Subcommands in native_generation.py | 11 |
| Total subcommand argument registrations across subcommands | 48 |
| Unique subcommand argument destinations (excluding subparser selector command) | 19 |
| Unique argument destinations including subparser selector command | 20 |
| Total args.<destination> line occurrences (19 argument destinations) | 41 |
| Total args.<destination> line occurrences (including args.command) | 59 |
| Builder search words | 12 |
| Builder function word-matches outside tests (src/ and scripts/ excluding */tests/*) | 267 |
| Unique builder functions outside tests (src/ and scripts/ excluding */tests/*) | 264 |
| Builder function word-matches in all of src/ and scripts/ (including scripts/.../tests/*) | 287 |
| Unique builder functions in all of src/ and scripts/ (including scripts/.../tests/*) | 284 |
| Builder function word-matches in scripts/.../tests/* | 20 |
| Builder function word-matches in top-level tests/ | 810 |
| Unique builder functions in top-level tests/ | 766 |
| Fixture builder word-matches in tests/utils/ | 6 |
| Unique fixture builder functions in tests/utils/ | 6 |

## 1. Subcommands and Arguments in src/data_sheets_schema/native_generation.py

### 1A. Subcommands

| # | Subcommand | Parser Variable | Defined Line | Argument Count | Subcommand Help Text |
|---:|---|---|---:|---:|---|
| 1 | permission-probe | probe | 87 | 4 | LIVE pinned binary against an isolated scripted local provider |
| 2 | validate-probe | validate | 92 | 3 | Offline verification of saved observations; never produces a probe |
| 3 | observation-probe | observation | 96 | 3 | LIVE authorized provisional observation against the scripted local provider only |
| 4 | bound-permission-probe | bound | 100 | 3 | LIVE authorized bound permission protocol after the saved observation |
| 5 | validate-probe-sequence | sequence | 104 | 3 | Offline reconstruction of the observation-to-permission binding |
| 6 | prepare-subscription-guard | prepare | 108 | 8 | Offline binding of existing quota/word evidence; never creates authority |
| 7 | capture-subscription-event | capture | 117 | 5 | LIVE one fixed-prompt pinned-binary capture, only after its exact owner word |
| 8 | record-capture-word | record_word | 121 | 4 | Record a supplied newer word and supersede older capture authority without a process |
| 9 | prepare-subscription-guard-v2 | prepare_v2 | 125 | 6 | Offline guard v2 from the one registered capture and exact owner terms |
| 10 | launch | launch | 129 | 7 | LIVE one registered attempt; requires the complete admission chain |
| 11 | read-final | readback | 134 | 2 | Offline independent saved execution readback; never resumes an attempt |

### 1B. Arguments per Subcommand

| Subcommand | Flags | Destination | Required | Type | Defined Line | Help Text |
|---|---|---|---|---|---:|---|
| permission-probe | --expectation | expectation | yes | str | 89 | none |
| permission-probe | --output-directory | output_directory | yes | str | 90 | none |
| permission-probe | --deadline-seconds | deadline_seconds | yes | int | 91 | none |
| permission-probe | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| validate-probe | --expectation | expectation | yes | str | 94 | none |
| validate-probe | --probe | probe | yes | str | 95 | none |
| validate-probe | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| observation-probe | --authorization | authorization | yes | str | 98 | none |
| observation-probe | --runtime | runtime | yes | str | 99 | none |
| observation-probe | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| bound-permission-probe | --authorization | authorization | yes | str | 102 | none |
| bound-permission-probe | --expectation | expectation | yes | str | 103 | none |
| bound-permission-probe | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| validate-probe-sequence | --runtime | runtime | yes | str | 106 | none |
| validate-probe-sequence | --probe | probe | yes | str | 107 | none |
| validate-probe-sequence | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| prepare-subscription-guard | --registration | registration | yes | str | 110 | none |
| prepare-subscription-guard | --launch-word | launch_word | yes | str | 111 | none |
| prepare-subscription-guard | --event | event | yes | str | 112 | none |
| prepare-subscription-guard | --captured-at | captured_at | yes | str | 113 | none |
| prepare-subscription-guard | --max-starting-weekly-utilization | max_starting_weekly_utilization | yes | float | 114 | none |
| prepare-subscription-guard | --max-age-seconds | max_age_seconds | yes | int | 115 | none |
| prepare-subscription-guard | --output | output | yes | str | 116 | none |
| prepare-subscription-guard | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| capture-subscription-event | --registration | registration | yes | str | 120 | none |
| capture-subscription-event | --review | review | yes | str | 120 | none |
| capture-subscription-event | --launch-word | launch_word | yes | str | 120 | none |
| capture-subscription-event | --output-directory | output_directory | yes | str | 120 | none |
| capture-subscription-event | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| record-capture-word | --registration | registration | yes | str | 124 | none |
| record-capture-word | --review | review | yes | str | 124 | none |
| record-capture-word | --launch-word | launch_word | yes | str | 124 | none |
| record-capture-word | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| prepare-subscription-guard-v2 | --registration | registration | yes | str | 128 | none |
| prepare-subscription-guard-v2 | --review | review | yes | str | 128 | none |
| prepare-subscription-guard-v2 | --launch-word | launch_word | yes | str | 128 | none |
| prepare-subscription-guard-v2 | --capture | capture | yes | str | 128 | none |
| prepare-subscription-guard-v2 | --output | output | yes | str | 128 | none |
| prepare-subscription-guard-v2 | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| launch | --registration | registration | yes | str | 133 | none |
| launch | --review | review | yes | str | 133 | none |
| launch | --ci | ci | yes | str | 133 | none |
| launch | --launch-word | launch_word | yes | str | 133 | none |
| launch | --subscription-guard | subscription_guard | yes | str | 133 | none |
| launch | --subscription-guard-sha256 | subscription_guard_sha256 | yes | str | 133 | none |
| launch | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |
| read-final | --registration | registration | yes | str | 136 | none |
| read-final | --account-choice | account_choice | yes | str | 139 | Closed D105/D106 selected-intent document bound to exact subject/runtime bytes |

## 2. Where Each Argument Destination Is Used (args.<destination>)

| Destination | Declared On Subcommands | Line | Stripped Line |
|---|---|---:|---|
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 155 | if args.command in ('observation-probe', 'bound-permission-probe', 'validate-probe-sequence'): |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 157 | subject_path = args.expectation if args.command == 'bound-permission-probe' else args.runtime |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 160 | runtime = subject['runtime'] if args.command == 'bound-permission-probe' else subject |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 164 | if args.command == 'validate-probe-sequence': |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 170 | if args.command == 'observation-probe': |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 179 | _emit(result, choice_raw, command=args.command) |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 181 | if args.command in ("permission-probe", "validate-probe"): |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 189 | if args.command == "permission-probe": |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 203 | _emit(result, choice_raw, command=args.command) |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 218 | if args.command in ("capture-subscription-event", "prepare-subscription-guard-v2", 'record-capture-word'): |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 229 | if args.command == 'record-capture-word': |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 232 | elif args.command == "capture-subscription-event": |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 248 | _emit(result, choice_raw, command=args.command) |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 249 | elif args.command == "prepare-subscription-guard": |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 258 | _emit({"guard_sha256": guard.sha(raw), "path": args.output}, choice_raw, command=args.command) |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 259 | elif args.command == "launch": |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 265 | _emit(result, choice_raw, command=args.command) |
| command | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 270 | _emit(result, choice_raw, command=args.command) |
| expectation | permission-probe, validate-probe, bound-permission-probe | 157 | subject_path = args.expectation if args.command == 'bound-permission-probe' else args.runtime |
| expectation | permission-probe, validate-probe, bound-permission-probe | 182 | subject_raw = _read(args.expectation) |
| expectation | permission-probe, validate-probe, bound-permission-probe | 187 | captures = [(args.expectation, subject_raw, SUBJECT_LIMIT), |
| output_directory | permission-probe, capture-subscription-event | 194 | produced = probe.produce_saved_probe(expected, args.output_directory, |
| output_directory | permission-probe, capture-subscription-event | 234 | review_bundle_raw=bundle_raw, launch_word_raw=word_raw, directory=args.output_directory) |
| deadline_seconds | permission-probe | 195 | deadline_seconds=args.deadline_seconds) |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 161 | choice_raw = _account_choice(args.account_choice, subject_raw, runtime) |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 163 | (args.account_choice, choice_raw, CHOICE_LIMIT)] |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 186 | choice_raw = _account_choice(args.account_choice, subject_raw, expected["runtime"]) |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 188 | (args.account_choice, choice_raw, CHOICE_LIMIT)] |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 215 | choice_raw = _account_choice(args.account_choice, subject_raw, value["runtime"]) |
| account_choice | permission-probe, validate-probe, observation-probe, bound-permission-probe, validate-probe-sequence, prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 217 | (args.account_choice, choice_raw, CHOICE_LIMIT)] |
| probe | validate-probe, validate-probe-sequence | 165 | result = sequence.validate_bound_probe(runtime, args.probe) |
| probe | validate-probe, validate-probe-sequence | 200 | saved_raw = _read(args.probe, MAX_WIRE) |
| probe | validate-probe, validate-probe-sequence | 202 | _unchanged(*captures, (args.probe, saved_raw, MAX_WIRE)) |
| authorization | observation-probe, bound-permission-probe | 167 | authorization_raw = _read(args.authorization) |
| authorization | observation-probe, bound-permission-probe | 168 | captures.append((args.authorization, authorization_raw, SUBJECT_LIMIT)) |
| runtime | observation-probe, validate-probe-sequence | 157 | subject_path = args.expectation if args.command == 'bound-permission-probe' else args.runtime |
| registration | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 208 | subject_raw = _read(args.registration) |
| registration | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch, read-final | 216 | captures = [(args.registration, subject_raw, SUBJECT_LIMIT), |
| launch_word | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 224 | bundle_raw, word_raw = _read(args.review), _read(args.launch_word) |
| launch_word | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 227 | (args.launch_word, word_raw, SUBJECT_LIMIT)]) |
| launch_word | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 250 | word_raw, event_raw = _read(args.launch_word), _read(args.event) |
| launch_word | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 255 | _unchanged(*captures, (args.launch_word, word_raw, SUBJECT_LIMIT), |
| launch_word | prepare-subscription-guard, capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 263 | launch_word_path=args.launch_word, subscription_guard_path=args.subscription_guard, |
| event | prepare-subscription-guard | 250 | word_raw, event_raw = _read(args.launch_word), _read(args.event) |
| event | prepare-subscription-guard | 256 | (args.event, event_raw, SUBJECT_LIMIT)) |
| captured_at | prepare-subscription-guard | 252 | launch_word_raw=word_raw, event_raw=event_raw, captured_at=args.captured_at, |
| max_starting_weekly_utilization | prepare-subscription-guard | 253 | maximum_starting_utilization=args.max_starting_weekly_utilization, |
| max_age_seconds | prepare-subscription-guard | 254 | max_age_seconds=args.max_age_seconds) |
| output | prepare-subscription-guard, prepare-subscription-guard-v2 | 246 | _new_file(args.output, raw) |
| output | prepare-subscription-guard, prepare-subscription-guard-v2 | 247 | result = {"guard_sha256": guard.sha(raw), "path": args.output} |
| output | prepare-subscription-guard, prepare-subscription-guard-v2 | 257 | _new_file(args.output, raw) |
| output | prepare-subscription-guard, prepare-subscription-guard-v2 | 258 | _emit({"guard_sha256": guard.sha(raw), "path": args.output}, choice_raw, command=args.command) |
| review | capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 224 | bundle_raw, word_raw = _read(args.review), _read(args.launch_word) |
| review | capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 226 | captures.extend([(args.review, bundle_raw, SUBJECT_LIMIT), |
| review | capture-subscription-event, record-capture-word, prepare-subscription-guard-v2, launch | 262 | result = launch(subject_raw, review_path=args.review, ci_path=args.ci, |
| capture | prepare-subscription-guard-v2 | 237 | saved = capture.read_capture(args.capture, registration_raw=subject_raw, |
| ci | launch | 262 | result = launch(subject_raw, review_path=args.review, ci_path=args.ci, |
| subscription_guard | launch | 263 | launch_word_path=args.launch_word, subscription_guard_path=args.subscription_guard, |
| subscription_guard_sha256 | launch | 264 | subscription_guard_sha256=args.subscription_guard_sha256) |

## 3. Builder Function Definitions by Word

### 3A. Counts per Word Across Path Categories

| Word | Regex Pattern | Non-Test Paths (src/ and scripts/ excluding */tests/*) | Test Paths Inside scripts/ (scripts/.../tests/*) | All src/ and scripts/ | Top-Level tests/ | All Test Paths Combined | Fixture Builders (tests/utils/) |
|---|---|---:|---:|---:|---:|---:|---:|
| registration | ^\s*def [A-Za-z0-9_]*registration | 34 | 11 | 45 | 116 | 127 | 1 |
| review | ^\s*def [A-Za-z0-9_]*review | 17 | 0 | 17 | 91 | 91 | 1 |
| bundle | ^\s*def [A-Za-z0-9_]*bundle | 39 | 3 | 42 | 82 | 85 | 1 |
| launch_word | ^\s*def [A-Za-z0-9_]*launch_word | 0 | 0 | 0 | 0 | 0 | 0 |
| word | ^\s*def [A-Za-z0-9_]*word | 14 | 0 | 14 | 48 | 48 | 0 |
| account_choice | ^\s*def [A-Za-z0-9_]*account_choice | 1 | 0 | 1 | 2 | 2 | 0 |
| statement | ^\s*def [A-Za-z0-9_]*statement | 7 | 0 | 7 | 8 | 8 | 0 |
| runtime | ^\s*def [A-Za-z0-9_]*runtime | 30 | 0 | 30 | 86 | 86 | 1 |
| capture | ^\s*def [A-Za-z0-9_]*capture | 88 | 2 | 90 | 271 | 273 | 0 |
| guard | ^\s*def [A-Za-z0-9_]*guard | 21 | 4 | 25 | 78 | 82 | 2 |
| ci_evidence | ^\s*def [A-Za-z0-9_]*ci_evidence | 0 | 0 | 0 | 1 | 1 | 0 |
| probe | ^\s*def [A-Za-z0-9_]*probe | 16 | 0 | 16 | 27 | 27 | 0 |

### 3B. Non-Test Paths in src/ and scripts/ (Excluding */tests/*)

| Word | File | Line | Function Name | Stripped Definition Line |
|---|---|---:|---|---|
| registration | scripts/adhoc/build_native_u2_20261106.py | 39 | registration | def registration(spec):'''), |
| registration | scripts/adhoc/split_native_u3d_round8_20261107.py | 200 | _registration_body | def _registration_body(composition_path, system_path, **kwargs): |
| registration | scripts/build_api_registrations.py | 610 | check_registration_sizing | def check_registration_sizing(registration_path: Path \| str, raw: bytes, *, root_dir: Path \| None = None) -> dict[str, Any] \| None: |
| registration | scripts/build_api_registrations.py | 1016 | build_registration | def build_registration(project: str, label: str, *, write_to_disk: bool = True, replace: bool = False, |
| registration | scripts/build_api_registrations.py | 1030 | prepare_registration | def prepare_registration( |
| registration | scripts/build_api_registrations.py | 1430 | validate_registration_document | def validate_registration_document(reg: dict[str, Any]) -> dict[str, Any]: |
| registration | scripts/build_api_registrations.py | 1437 | verify_registration_input_pins | def verify_registration_input_pins( |
| registration | src/data_sheets_schema/bc1_selection.py | 108 | registration_block | def registration_block(*, fan_in=2) -> dict: |
| registration | src/data_sheets_schema/bc1_selection.py | 133 | validate_registration | def validate_registration(reg: dict, *, shared_version=1) -> None: |
| registration | src/data_sheets_schema/cli/api.py | 71 | _bounded_registration_bytes | def _bounded_registration_bytes(path): |
| registration | src/data_sheets_schema/cli/api.py | 89 | _capture_shared_registration | def _capture_shared_registration(path, *, expect_sha256: str \| None = None): |
| registration | src/data_sheets_schema/cross_family_judge_analysis.py | 133 | executor_registration | def executor_registration(capture, pin): |
| registration | src/data_sheets_schema/cross_family_panel.py | 123 | _registration | def _registration(capture, declaration_raw, read_path, read_authority=None): |
| registration | src/data_sheets_schema/dollar_readout.py | 726 | registration_from_ledger | def registration_from_ledger(ledger_data: Mapping[str, Any]) -> dict[str, Any] \| None: |
| registration | src/data_sheets_schema/native_attempt_supervisor.py | 128 | registration | def registration(composition_path, fixture_path, *, attempt_id, attempt_directory, |
| registration | src/data_sheets_schema/native_attribution_registration.py | 66 | registration | def registration(spec): |
| registration | src/data_sheets_schema/native_attribution_registration.py | 127 | write_registration | def write_registration(spec, destination): |
| registration | src/data_sheets_schema/native_attribution_registration_v2.py | 72 | registration | def registration(spec): |
| registration | src/data_sheets_schema/native_attribution_registration_v2.py | 134 | write_registration | def write_registration(spec, destination): |
| registration | src/data_sheets_schema/native_execution_registration.py | 237 | registration | def registration(composition_path, system_path, *, permission_probe_path, attempt_id, |
| registration | src/data_sheets_schema/native_execution_registration.py | 327 | write_registration | def write_registration(destination, **kwargs): |
| registration | src/data_sheets_schema/native_launch_review.py | 67 | _registration_commit | def _registration_commit(evidence, registration_raw, runtime): |
| registration | src/data_sheets_schema/native_launch_review.py | 304 | registration_fields | def registration_fields(raw): |
| registration | src/data_sheets_schema/native_shared_registration.py | 231 | _registration_body | def _registration_body(composition_path, system_path, *, permission_probe_path, attempt_id, |
| registration | src/data_sheets_schema/native_shared_registration_orchestration.py | 31 | _registration_body | def _registration_body(composition_path, system_path, **kwargs): |
| registration | src/data_sheets_schema/native_shared_registration_orchestration.py | 54 | registration | def registration(composition_path, system_path, **kwargs): |
| registration | src/data_sheets_schema/native_shared_registration_orchestration.py | 67 | synthetic_registration | def synthetic_registration(composition_path, system_path, **kwargs): |
| registration | src/data_sheets_schema/nested_support_execution.py | 226 | _registration | def _registration(capture, descriptor_raw, declaration, identity): |
| registration | src/data_sheets_schema/receipt_completion.py | 56 | registration | def registration(spec) -> dict: |
| registration | src/data_sheets_schema/receipt_completion.py | 73 | registration_identity | def registration_identity(spec) -> dict: |
| registration | src/data_sheets_schema/receipt_completion.py | 510 | _check_registration_identity | def _check_registration_identity(inputs, selected_registration): |
| registration | src/data_sheets_schema/receipt_completion_policy.py | 60 | parse_registration | def parse_registration(raw: bytes, *, version: int = 1) -> dict: |
| registration | src/data_sheets_schema/receipt_completion_policy.py | 119 | registration_identity | def registration_identity(raw: bytes, *, version: int = 1) -> dict: |
| registration | src/data_sheets_schema/shared_generation.py | 341 | parse_registration | def parse_registration(raw: bytes) -> dict: |
| review | scripts/reference_rescore_cborg_batch.py | 101 | require_review | def require_review(r, filename, hash_key, expected): |
| review | scripts/reference_rescore_cborg_batch.py | 131 | verify_reviewed_retry | def verify_reviewed_retry(r, job, registration, attempts): |
| review | src/data_sheets_schema/api_runner.py | 5107 | require_source_reviews | def require_source_reviews(spec: RunSpec, carry: dict[str, str], *, evidence=None) -> None: |
| review | src/data_sheets_schema/api_runner.py | 5137 | _refuse_unusable_source_review | def _refuse_unusable_source_review(spec: RunSpec, phase: str, problem: str, |
| review | src/data_sheets_schema/api_runner.py | 5192 | _pending_source_review | def _pending_source_review(spec: RunSpec, phase: str, response) -> dict: |
| review | src/data_sheets_schema/cli/review.py | 18 | review | def review(): |
| review | src/data_sheets_schema/evaluation/blind_review_pack.py | 458 | build_blind_review_pack | def build_blind_review_pack(records: Iterable[Record], output_dir: Path, *, key_output: Path, seed: str \| int, |
| review | src/data_sheets_schema/evidence_assertions.py | 52 | _review_authority | def _review_authority(protocol_version, source_manifest_raw, project): |
| review | src/data_sheets_schema/native_launch_review.py | 31 | _review_document | def _review_document(document): |
| review | src/data_sheets_schema/removals.py | 1153 | source_review_judgments | def source_review_judgments(audit: Any, snapshot_sha256: str \| None = None |
| review | src/data_sheets_schema/review_pack.py | 1042 | review_evidence_why | def review_evidence_why(block: Any) -> str \| None: |
| review | src/data_sheets_schema/review_pack.py | 1079 | review_evidence | def review_evidence(block: Any) -> int \| None: |
| review | src/data_sheets_schema/review_pack.py | 1089 | check_review | def check_review(pack: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]: |
| review | src/data_sheets_schema/review_pack.py | 1146 | reviewed_at_reports | def reviewed_at_reports(value: Any) -> list[dict[str, Any]]: |
| review | src/data_sheets_schema/rocrate_map.py | 759 | _preview | def _preview(value: Any, limit: int = 90) -> str: |
| review | src/data_sheets_schema/status_context.py | 1232 | review_status_expression | def review_status_expression(audit: dict[str, Any], *, record_raw: str \| None = None, |
| review | src/data_sheets_schema/usage_ledger.py | 761 | require_source_review_admission | def require_source_review_admission(spec) -> None: |
| bundle | scripts/arm_comparison.py | 1539 | bundle_drift_by_arm | def bundle_drift_by_arm(data): |
| bundle | scripts/measure_unhyphenated_line_splits.py | 109 | bundle_versions | def bundle_versions(corpus: Path) -> tuple[dict[tuple[str, str], int], list[str]]: |
| bundle | scripts/recall_target_baseline.py | 250 | hashed_bundle | def hashed_bundle(inputs: dict[str, Any], root: Path) -> tuple[bytes \| None, str]: |
| bundle | src/data_sheets_schema/api_runner.py | 2999 | chunk_marked_bundle | def chunk_marked_bundle(bundle: Path, manifest: Path \| None = None, *, |
| bundle | src/data_sheets_schema/attainability.py | 1151 | provenance_bundle | def provenance_bundle(record: Path) -> dict[str, Any] \| None: |
| bundle | src/data_sheets_schema/attainability.py | 1200 | evaluation_bundle | def evaluation_bundle(evaluation: dict[str, Any]) -> dict[str, Any] \| None: |
| bundle | src/data_sheets_schema/awards.py | 106 | bundle_awards | def bundle_awards(bundle: Path) -> dict[str, Any]: |
| bundle | src/data_sheets_schema/backfill_checks.py | 89 | declared_bundle | def declared_bundle(record: dict[str, Any], provenance: Path \| None = None) -> Path \| None: |
| bundle | src/data_sheets_schema/chunking.py | 287 | bundle_path | def bundle_path(project: str, concat_dir: Path \| None = None) -> Path: |
| bundle | src/data_sheets_schema/chunking.py | 291 | project_bundles | def project_bundles(project: str, concat_dir: Path \| None = None) -> list[Path]: |
| bundle | src/data_sheets_schema/cli/api.py | 447 | _require_bundle | def _require_bundle(spec, project, bundle): |
| bundle | src/data_sheets_schema/cli/bundle.py | 14 | bundle | def bundle(): |
| bundle | src/data_sheets_schema/cli/download.py | 494 | audit_bundles | def audit_bundles(project, strict, manifest): |
| bundle | src/data_sheets_schema/cli/healthsheet.py | 27 | bundle | def bundle(record, output_dir, project, name): |
| bundle | src/data_sheets_schema/cli/provenance.py | 2911 | backfill_bundle_md5 | def backfill_bundle_md5(execute, label): |
| bundle | src/data_sheets_schema/cli/rocrate.py | 271 | bundle | def bundle(project, packages_dir): |
| bundle | src/data_sheets_schema/evaluation/arm_comparison.py | 109 | bundle_drift | def bundle_drift( |
| bundle | src/data_sheets_schema/evaluation/arm_comparison.py | 210 | compare_bundle_drift | def compare_bundle_drift( |
| bundle | src/data_sheets_schema/evaluation/arm_comparison.py | 240 | recorded_bundle_identity | def recorded_bundle_identity(comparisons: Mapping[str, Any]) -> dict[str, Any]: |
| bundle | src/data_sheets_schema/evaluation/arm_comparison.py | 279 | render_bundle_drift | def render_bundle_drift(comparisons: Mapping[str, Any]) -> list[str]: |
| bundle | src/data_sheets_schema/evidence_score.py | 119 | bundle_fingerprint | def bundle_fingerprint(bundle: str) -> str: |
| bundle | src/data_sheets_schema/healthsheet.py | 36 | bundle_name | def bundle_name() -> str \| None: |
| bundle | src/data_sheets_schema/healthsheet.py | 154 | build_bundle | def build_bundle(record_path: Path \| None = None, |
| bundle | src/data_sheets_schema/name_grounding.py | 1134 | bundle_text | def bundle_text(raw: bytes) -> tuple[str \| None, str \| None]: |
| bundle | src/data_sheets_schema/name_grounding.py | 1151 | record_bundle_bytes | def record_bundle_bytes(record: dict[str, Any], provenance: Path |
| bundle | src/data_sheets_schema/native_launch_review.py | 228 | validate_bundle | def validate_bundle(registration_raw, review_bundle_raw, launch_word_raw): |
| bundle | src/data_sheets_schema/provenance.py | 2383 | bundle_bytes_for | def bundle_bytes_for(bundle_path: str, md5: str \| None = None, |
| bundle | src/data_sheets_schema/provenance.py | 2422 | bundle_blob_history | def bundle_blob_history(bundle_path: str) -> tuple[dict[str, str], ...]: |
| bundle | src/data_sheets_schema/provenance.py | 2487 | resolve_bundle_md5 | def resolve_bundle_md5(record_path: Path, |
| bundle | src/data_sheets_schema/provenance.py | 2532 | apply_bundle_md5 | def apply_bundle_md5(record_path: Path, history=bundle_blob_history) -> dict[str, Any] \| None: |
| bundle | src/data_sheets_schema/rocrate_normalize.py | 611 | build_crate_bundle | def build_crate_bundle( |
| bundle | src/data_sheets_schema/rocrate_normalize.py | 788 | build_crate_only_bundle | def build_crate_only_bundle( |
| bundle | src/data_sheets_schema/runs.py | 1380 | bundle_drift | def bundle_drift(method: str, label: str, project: str, |
| bundle | src/data_sheets_schema/runs.py | 1423 | bundle_drift_detail | def bundle_drift_detail(method: str, label: str, project: str, |
| bundle | src/data_sheets_schema/scope.py | 103 | in_bundle_of | def in_bundle_of(entry: Any) -> list[str \| int \| float]: |
| bundle | src/data_sheets_schema/scope.py | 119 | _in_bundle_as_written | def _in_bundle_as_written(entry: Any) -> list[Any]: |
| bundle | src/data_sheets_schema/shared_generation.py | 961 | marked_bundle | def marked_bundle(spec): |
| bundle | src/data_sheets_schema/verifiable.py | 146 | declared_bundle | def declared_bundle(method: str, label: str, project: str) -> Path \| None: |
| bundle | src/data_sheets_schema/verifiable.py | 705 | normalise_bundle | def normalise_bundle(bundle: str) -> str: |
| launch_word | none | none | none | none |
| word | scripts/measure_unhyphenated_line_splits.py | 131 | interior_words | def interior_words(lines: Iterable[str]) -> set[str]: |
| word | scripts/measure_unhyphenated_line_splits.py | 244 | load_words | def load_words(path: Path \| None) -> tuple[set[str], dict[str, Any]]: |
| word | src/data_sheets_schema/name_grounding.py | 773 | words_in_capitals | def words_in_capitals(name: str) -> frozenset[str]: |
| word | src/data_sheets_schema/name_grounding.py | 867 | leaf_words | def leaf_words(name: str) -> frozenset[str]: |
| word | src/data_sheets_schema/native_subscription_capture.py | 439 | activate_capture_word | def activate_capture_word(*, registration_raw, review_bundle_raw, launch_word_raw, now=None): |
| word | src/data_sheets_schema/native_subscription_guard_v2.py | 259 | _word | def _word(raw, registration_raw): |
| word | src/data_sheets_schema/receipt_origin.py | 1761 | _xargs_supplies_derive_word | def _xargs_supplies_derive_word(text: str) -> bool: |
| word | src/data_sheets_schema/receipt_origin.py | 1841 | _plain_word | def _plain_word(word: str) -> bool: |
| word | src/data_sheets_schema/receipt_origin.py | 2496 | _keyword_mode | def _keyword_mode(segments: list[list[str]]) -> bool: |
| word | src/data_sheets_schema/receipts.py | 1170 | _normalise_number_words | def _normalise_number_words(text: str) -> str: |
| word | src/data_sheets_schema/redundancy.py | 109 | _content_words | def _content_words(sentence: str) -> set[str]: |
| word | src/data_sheets_schema/removals.py | 1029 | _words | def _words(value: Any, *, identifier_bases: IdentifierBases \| None = None) -> frozenset[str]: |
| word | src/data_sheets_schema/removals.py | 1037 | _words_cached | def _words_cached(value: Any, identifier_bases: tuple[tuple[str, str], ...] \| None) -> frozenset[str]: |
| word | src/data_sheets_schema/self_disclaimed.py | 250 | _word | def _word(terms) -> re.Pattern: |
| account_choice | src/data_sheets_schema/native_generation.py | 39 | _account_choice | def _account_choice(path, subject_raw, runtime): |
| statement | scripts/adhoc/mutate_d76_integration_order_20261102.py | 63 | direct_call_statement | def direct_call_statement(node, name): |
| statement | scripts/adhoc/mutate_d76_integration_order_20261102.py | 67 | statement_containing | def statement_containing(fn, call_name): |
| statement | scripts/adhoc/propose_native_u4b_a4_producer_20261108.py | 68 | _statement | def _statement(text): |
| statement | src/data_sheets_schema/redundancy.py | 118 | restatements | def restatements(record: dict, threshold: float = THRESHOLD |
| statement | src/data_sheets_schema/report_audit_totals.py | 200 | _severity_statement | def _severity_statement(report_text: str, start: int, end: int) -> str: |
| statement | src/data_sheets_schema/self_disclaimed.py | 985 | _statement_head | def _statement_head(lexicon, subject: str): |
| statement | src/semantic_exchange/generate_structural_mapping.py | 653 | _check_statement | def _check_statement(width: int = 76) -> str: |
| runtime | scripts/adhoc/native_wp1_synthetic_smoke_20261110.py | 103 | runtime_binaries | def runtime_binaries(): |
| runtime | scripts/adhoc/run_d76_round3_validation_20261102.py | 55 | runtime | def runtime(): |
| runtime | scripts/adhoc/run_d76_validation_20261031.py | 45 | runtime | def runtime(): |
| runtime | scripts/reference_rescore_cborg.py | 151 | verify_runtime_transport | def verify_runtime_transport(events: list[dict]) -> None: |
| runtime | src/data_sheets_schema/cli/api.py | 536 | _warn_method_runtime | def _warn_method_runtime(method, runtime, condition=None): |
| runtime | src/data_sheets_schema/cli/api.py | 561 | _runtime_method | def _runtime_method(arm, runtime, condition): |
| runtime | src/data_sheets_schema/native_catalog_reuse.py | 442 | runtime_token | def runtime_token(): |
| runtime | src/data_sheets_schema/native_execution.py | 106 | _probe_runtime | def _probe_runtime(value): |
| runtime | src/data_sheets_schema/native_execution.py | 134 | expected_runtime_observation | def expected_runtime_observation(value): |
| runtime | src/data_sheets_schema/native_execution_gates.py | 161 | runtime_observation_result | def runtime_observation_result(raw, admitted, selected_identity): |
| runtime | src/data_sheets_schema/native_execution_registration.py | 81 | validate_runtime | def validate_runtime(value): |
| runtime | src/data_sheets_schema/native_permission_probe.py | 36 | require_u4_runtime | def require_u4_runtime(runtime): |
| runtime | src/data_sheets_schema/native_shared_execution_orchestration.py | 141 | _synthetic_runtime_observation | def _synthetic_runtime_observation(value): |
| runtime | src/data_sheets_schema/native_shared_gate_primitives.py | 146 | runtime_observation_result | def runtime_observation_result(raw, admitted, selected_identity): |
| runtime | src/data_sheets_schema/native_shared_permissions.py | 114 | _runtime | def _runtime(value): |
| runtime | src/data_sheets_schema/native_shared_registration_orchestration.py | 272 | _require_runtime_observation | def _require_runtime_observation(value): |
| runtime | src/data_sheets_schema/native_shared_render.py | 111 | _runtime | def _runtime(raw, provider, effort): |
| runtime | src/data_sheets_schema/native_shared_runtime_values.py | 98 | validate_runtime | def validate_runtime(value): |
| runtime | src/data_sheets_schema/native_shared_runtime_values.py | 161 | validate_runtime_v2 | def validate_runtime_v2(value): |
| runtime | src/data_sheets_schema/native_u4b_policy.py | 53 | validate_runtime_terms | def validate_runtime_terms(runtime): |
| runtime | src/data_sheets_schema/native_u4b_probe_sequence.py | 85 | validate_provisional_runtime | def validate_provisional_runtime(value): |
| runtime | src/data_sheets_schema/native_u4b_runtime.py | 202 | prepare_runtime | def prepare_runtime(runtime, *, probe_init_path, native_request_path, updater_source, updater_root, |
| runtime | src/data_sheets_schema/native_u4b_runtime.py | 261 | validate_prepared_runtime | def validate_prepared_runtime(runtime): |
| runtime | src/data_sheets_schema/native_u4b_runtime.py | 312 | is_prepared_runtime | def is_prepared_runtime(runtime): |
| runtime | src/data_sheets_schema/provenance.py | 255 | runtime_reads_playbooks | def runtime_reads_playbooks(runtime: str \| None) -> bool \| None: |
| runtime | src/data_sheets_schema/receipt_origin.py | 1120 | _runtime_denials | def _runtime_denials(events: list[tuple[int, int, dict]], calls: list[dict], |
| runtime | src/data_sheets_schema/receipt_origin.py | 2750 | _substituted_runtime_program | def _substituted_runtime_program(word: str) -> bool: |
| runtime | src/data_sheets_schema/runs.py | 100 | is_claude_code_runtime | def is_claude_code_runtime(runtime: str \| None) -> bool: |
| runtime | src/data_sheets_schema/runs.py | 107 | canonical_runtime | def canonical_runtime(runtime: str \| None) -> str \| None: |
| runtime | src/data_sheets_schema/runs.py | 120 | runtime_of | def runtime_of(record: dict) -> str \| None: |
| capture | scripts/adhoc/bc1_g2_bytes_20261103.py | 37 | capture | def capture(root, side): |
| capture | scripts/adhoc/bc1_g2_round2_20261103.py | 37 | recapture | def recapture(root, ref): |
| capture | scripts/adhoc/d41_legacy_controls_20261029.py | 72 | capture | def capture(source, dest): |
| capture | scripts/adhoc/d41_legacy_controls_20261029_v1.py | 68 | capture | def capture(source, dest): |
| capture | scripts/adhoc/d41_request_parity_20261026.py | 284 | capture | def capture(root, code_root, fixture, output, mode, *, project, partition, context_path): |
| capture | scripts/adhoc/generality_g1_request_proof_20261029.py | 15 | capture | def capture(output): |
| capture | scripts/adhoc/generality_g1_round2/proof.py | 44 | capture | def capture(revision): |
| capture | scripts/adhoc/measure_bc1_d59_20261028.py | 82 | captured | def captured(reg): |
| capture | scripts/adhoc/native_wp1_quiet_20261110.py | 379 | _capture_lock | def _capture_lock(lock_path, candidate_path): |
| capture | scripts/adhoc/native_wp1_validation_20261110.py | 254 | capture_recheck_claim | def capture_recheck_claim(out, manifest_sha, source_commit, *, create=False): |
| capture | scripts/adhoc/native_wp1_validation_20261110.py | 269 | require_capture_recheck_result | def require_capture_recheck_result(out, manifest_sha, source_commit): |
| capture | scripts/adhoc/probe_native_u3a_round6_c_integration_20261108.py | 17 | test_real_c_verified_loader_preparer_capture_identity | def test_real_c_verified_loader_preparer_capture_identity(inputs, monkeypatch, record_property): |
| capture | src/data_sheets_schema/attainability.py | 826 | _validate_captured_text | def _validate_captured_text(text: str, name: str \| None = None, *, |
| capture | src/data_sheets_schema/attainability_aggregation.py | 782 | capture | def capture(selection_path, *, limits=DEFAULT_LIMITS): |
| capture | src/data_sheets_schema/attainability_aggregation.py | 809 | recheck_captured | def recheck_captured(closure, *, limits=DEFAULT_LIMITS): |
| capture | src/data_sheets_schema/audit_omissions.py | 59 | captured_asset_bytes | def captured_asset_bytes(captured_assets=None) -> dict[str, bytes]: |
| capture | src/data_sheets_schema/bc1_audit.py | 284 | capture_response | def capture_response(request, response): |
| capture | src/data_sheets_schema/bc1_registration.py | 91 | capture_inputs | def capture_inputs(registration, *, context_raw, schema_snapshot): |
| capture | src/data_sheets_schema/cli/api.py | 89 | _capture_shared_registration | def _capture_shared_registration(path, *, expect_sha256: str \| None = None): |
| capture | src/data_sheets_schema/d4d_pair_consistency.py | 748 | _captured_pair_history | def _captured_pair_history(core_path: Path) -> tuple[dict[str, Any], dict[str, Any] \| None]: |
| capture | src/data_sheets_schema/evaluation/historical_eval_binding.py | 172 | capture_for_pack | def capture_for_pack(bindings, *, cohort_pin, decisions): |
| capture | src/data_sheets_schema/fitness_schema.py | 325 | capture | def capture(class_name="Dataset", schema_path=None, *, profile): |
| capture | src/data_sheets_schema/grounding.py | 500 | _capture_declared_naming | def _capture_declared_naming(): |
| capture | src/data_sheets_schema/historical_digest.py | 225 | render_captured | def render_captured(raw_schema: bytes, logical_path: str, family: str, *, |
| capture | src/data_sheets_schema/historical_digest.py | 261 | _render_captured | def _render_captured(raw_schema: bytes, logical_path: str, family: str, *, |
| capture | src/data_sheets_schema/legacy_route_dispositions.py | 107 | capture_mapping | def capture_mapping(loader, raw, rows): |
| capture | src/data_sheets_schema/native_attribution_results.py | 563 | capture | def capture(composition_path, transcript_path, control_path, *, config_root=None): |
| capture | src/data_sheets_schema/native_attribution_results.py | 787 | check_capture | def check_capture(prepared): |
| capture | src/data_sheets_schema/native_execution_gates.py | 21 | capture | def capture(value, controls, *, authority_inputs, registration_raw): |
| capture | src/data_sheets_schema/native_permission_probe.py | 648 | _produce_captured | def _produce_captured(expected, directory, deadline, p, controls, controller_sources, |
| capture | src/data_sheets_schema/native_shared_capture.py | 250 | _captured | def _captured(role, path, raw): |
| capture | src/data_sheets_schema/native_shared_capture_orchestration.py | 236 | capture_stage | def capture_stage(selection_registration_path, *, _catalogs=None): |
| capture | src/data_sheets_schema/native_shared_controller.py | 30 | _captured_wire | def _captured_wire(raw): |
| capture | src/data_sheets_schema/native_shared_controller.py | 43 | captured_execution_body | def captured_execution_body(raw): |
| capture | src/data_sheets_schema/native_shared_controller.py | 50 | captured_preparation_body | def captured_preparation_body(raw): |
| capture | src/data_sheets_schema/native_shared_controller.py | 59 | captured_composition | def captured_composition(raw): |
| capture | src/data_sheets_schema/native_shared_controller.py | 147 | capture_phase | def capture_phase(run, *, complete): |
| capture | src/data_sheets_schema/native_shared_controller_orchestration.py | 618 | capture_phase | def capture_phase(run, *, complete): |
| capture | src/data_sheets_schema/native_shared_results.py | 77 | _captured_selection | def _captured_selection(pool, value): |
| capture | src/data_sheets_schema/native_shared_results_orchestration.py | 31 | _capture_member | def _capture_member(snapshot, path, role, limit, expected=None): |
| capture | src/data_sheets_schema/native_shared_results_orchestration.py | 39 | capture | def capture(value, controls, *, authority_inputs, registration_raw): |
| capture | src/data_sheets_schema/native_shared_results_orchestration.py | 221 | check_capture | def check_capture(prepared, *, controls): |
| capture | src/data_sheets_schema/native_shared_results_orchestration.py | 274 | incomplete_capture | def incomplete_capture(composition_path, attempt, adapter, reason): |
| capture | src/data_sheets_schema/native_shared_selection.py | 128 | descriptor_capture | def descriptor_capture() -> contract.DescriptorCapture: |
| capture | src/data_sheets_schema/native_shared_selection.py | 478 | capture_assets | def capture_assets() -> tuple[contract.CapturedArtifact, ...]: |
| capture | src/data_sheets_schema/native_shared_selection.py | 487 | capture | def capture(selection_path: str \| Path) -> contract.NativeSelectionCapture: |
| capture | src/data_sheets_schema/native_subscription_capture.py | 400 | capture_subscription | def capture_subscription(*, registration_raw, review_bundle_raw, launch_word_raw, directory): |
| capture | src/data_sheets_schema/native_subscription_capture.py | 439 | activate_capture_word | def activate_capture_word(*, registration_raw, review_bundle_raw, launch_word_raw, now=None): |
| capture | src/data_sheets_schema/native_subscription_capture.py | 457 | capture_admission_lease | def capture_admission_lease(*, registration_raw, review_bundle_raw, launch_word_raw, now=None): |
| capture | src/data_sheets_schema/native_subscription_capture.py | 472 | require_current_capture_authority | def require_current_capture_authority(*, registration_raw, review_bundle_raw, launch_word_raw, now=None): |
| capture | src/data_sheets_schema/native_subscription_capture.py | 521 | _perform_capture | def _perform_capture(directory, claim, binding, authority, reservation_directory, |
| capture | src/data_sheets_schema/native_subscription_capture.py | 605 | _capture_manifest_root | def _capture_manifest_root(manifest_path, registration_raw, review_bundle_raw, launch_word_raw): |
| capture | src/data_sheets_schema/native_subscription_capture.py | 618 | _read_capture_records | def _read_capture_records(path, directory, authority, *, registration_raw, launch_word_raw, |
| capture | src/data_sheets_schema/native_subscription_capture.py | 673 | _read_capture_with_authority | def _read_capture_with_authority(manifest_path, initial_authority, *, registration_raw, |
| capture | src/data_sheets_schema/native_subscription_capture.py | 685 | read_capture | def read_capture(manifest_path, *, registration_raw, review_bundle_raw, launch_word_raw, |
| capture | src/data_sheets_schema/native_subscription_capture.py | 704 | read_capture_for_event | def read_capture_for_event(directory, *, registration_raw, review_bundle_raw, launch_word_raw, |
| capture | src/data_sheets_schema/native_supervisor_gates.py | 124 | capture | def capture(composition_path, attempt, controls): |
| capture | src/data_sheets_schema/native_supervisor_gates.py | 188 | incomplete_capture | def incomplete_capture(composition_path, attempt, adapter, reason): |
| capture | src/data_sheets_schema/nested_support_execution.py | 519 | capture_run | def capture_run(output: Path): |
| capture | src/data_sheets_schema/nested_support_execution.py | 544 | recheck_captured | def recheck_captured(capture, ledger): |
| capture | src/data_sheets_schema/profile_identity.py | 222 | capture | def capture(record: dict[str, Any]) -> dict[str, Any]: |
| capture | src/data_sheets_schema/reasoning.py | 131 | capture | def capture(resp) -> ReasoningCapture: |
| capture | src/data_sheets_schema/receipt_completion.py | 85 | schema_capture | def schema_capture(spec=None) -> dict: |
| capture | src/data_sheets_schema/receipt_origin.py | 861 | _captured_path | def _captured_path(value: str) -> str: |
| capture | src/data_sheets_schema/receipt_origin.py | 904 | _captured_identities | def _captured_identities(aliases: tuple[tuple[str, str], ...], paths: tuple[str, str]): |
| capture | src/data_sheets_schema/receipt_origin.py | 3978 | origin_captured | def origin_captured(transcripts: tuple[tuple[str, bytes], ...], *, receipt_raw: bytes, |
| capture | src/data_sheets_schema/related_dataset_diagnostics.py | 104 | _capture | def _capture(path: Path) -> tuple[bytes, dict[str, Any]]: |
| capture | src/data_sheets_schema/schema_snapshot.py | 264 | capture_schema | def capture_schema(path: str \| Path, *, content: bytes \| None = None, |
| capture | src/data_sheets_schema/schema_snapshot.py | 290 | _capture_native_schema | def _capture_native_schema(path: Path, members: tuple[tuple[Path, bytes], ...], |
| capture | src/data_sheets_schema/schema_snapshot.py | 324 | _capture_schema | def _capture_schema(root, read, *, content=None, namespace_orders=None, |
| capture | src/data_sheets_schema/schema_view.py | 236 | captured_view | def captured_view(snapshot: SchemaSnapshot) -> Iterator[SchemaView]: |
| capture | src/data_sheets_schema/shared_generation.py | 112 | captured_assets | def captured_assets(*, version=1) -> dict[str, bytes]: |
| capture | src/data_sheets_schema/shared_generation.py | 511 | capture | def capture(spec) -> Capture: |
| capture | src/data_sheets_schema/shared_generation.py | 568 | _capture_bytes | def _capture_bytes(raw, reg, files, *, captured_only=False): |
| capture | src/data_sheets_schema/shared_generation.py | 695 | _context_capture | def _context_capture(spec): |
| capture | src/data_sheets_schema/source_heading_completed.py | 249 | _captured_form | def _captured_form(spec, full, core, rules): |
| capture | src/data_sheets_schema/source_heading_completed.py | 443 | capture_completed | def capture_completed(spec): |
| capture | src/data_sheets_schema/source_heading_completed.py | 509 | _captured_json_schema | def _captured_json_schema(snapshot, *, cls, closed=True, descendants=True): |
| capture | src/data_sheets_schema/source_heading_completed.py | 530 | _captured_validator | def _captured_validator(snapshot, plugins): |
| capture | src/data_sheets_schema/source_heading_routing.py | 179 | _capture_schema | def _capture_schema(path): |
| capture | src/data_sheets_schema/source_heading_routing.py | 608 | _check_captured_files | def _check_captured_files(files): |
| capture | src/data_sheets_schema/source_metadata.py | 62 | _captured | def _captured(value): |
| capture | src/data_sheets_schema/top_level_fitness_results.py | 395 | _recheck_captured | def _recheck_captured(capture, raw): |
| capture | src/data_sheets_schema/top_level_fitness_results.py | 686 | _capture_execution | def _capture_execution(capture, path): |
| capture | src/data_sheets_schema/transformation_measure.py | 446 | _measure_captured | def _measure_captured(full: dict, core: dict, schema: Any, snapshots: dict, |
| capture | src/data_sheets_schema/typed_audit.py | 107 | _capture | def _capture(path): |
| capture | src/data_sheets_schema/typed_audit.py | 477 | capture_response | def capture_response(request, response): |
| capture | src/data_sheets_schema/verifiable.py | 217 | _captured_owner_rules | def _captured_owner_rules(raw: bytes, kind: str) -> Mapping[str, _OwnerClass]: |
| guard | scripts/adhoc/d76_pytest_observer_20261031.py | 39 | install_guard | def install_guard(): |
| guard | scripts/adhoc/d76_round3_pytest_observer_20261102.py | 71 | install_guard | def install_guard(): |
| guard | scripts/adhoc/mutate_d76_integration_order_20261102.py | 75 | remove_guard | def remove_guard(source, name, guard): |
| guard | scripts/adhoc/native_u1_offline/sitecustomize.py | 5 | guard | def guard(event, args): |
| guard | scripts/adhoc/native_u4b_a4_real_events_20261108.py | 150 | make_guard | def make_guard(module, case, *, seed=False): |
| guard | scripts/adhoc/run_native_u1u3_20261108.py | 30 | guarded_popen | def guarded_popen(command, *args, **kwargs): |
| guard | scripts/adhoc/test_d76_round4_sg2_portability_20261103.py | 67 | offline_guard | def offline_guard(output): |
| guard | scripts/adhoc/test_pr5212_writer_main_controls_20261102.py | 29 | test_actual_writer_artifact_with_owner_guard_passing | def test_actual_writer_artifact_with_owner_guard_passing(tmp_path, monkeypatch, writer): |
| guard | src/data_sheets_schema/bc1_runtime.py | 452 | resume_guard | def resume_guard(spec, progress, *, record=None): |
| guard | src/data_sheets_schema/latch_journal.py | 1075 | _carry_guard_fields | def _carry_guard_fields(spec, data, previous, mine): |
| guard | src/data_sheets_schema/latch_journal.py | 1249 | guarded_launch | def guarded_launch(spec, expected, acquire): |
| guard | src/data_sheets_schema/native_execution_orchestration.py | 215 | _admit_subscription_guard | def _admit_subscription_guard(guard, attempt, file, write): |
| guard | src/data_sheets_schema/native_execution_orchestration.py | 226 | _guarded_observer | def _guarded_observer(guard, adapter, budget_stop): |
| guard | src/data_sheets_schema/native_execution_orchestration.py | 248 | _guarded_classifier | def _guarded_classifier(adapter, budget_stop): |
| guard | src/data_sheets_schema/native_shared_callback_orchestration.py | 56 | _worker_load_guard | def _worker_load_guard(dependencies): |
| guard | src/data_sheets_schema/native_subscription_guard.py | 235 | load_guard | def load_guard(path, expected_sha256, *, registration_raw, runtime, launch_word_path, clock=None): |
| guard | src/data_sheets_schema/native_subscription_guard.py | 307 | prepare_guard | def prepare_guard(*, registration_raw, runtime, launch_word_raw, event_raw, |
| guard | src/data_sheets_schema/native_subscription_guard_v2.py | 506 | load_guard | def load_guard(path, expected_sha256, *, registration_raw, runtime, launch_word_path, |
| guard | src/data_sheets_schema/native_subscription_guard_v2.py | 677 | prepare_guard | def prepare_guard(*, registration_raw, runtime, launch_word_raw, event_raw, captured_at, |
| guard | src/data_sheets_schema/receipt_completion.py | 807 | resume_guard | def resume_guard(spec, progress: dict) -> None: |
| guard | src/data_sheets_schema/typed_audit_runtime.py | 423 | resume_guard | def resume_guard(spec, progress, *, record=None): |
| ci_evidence | none | none | none | none |
| probe | scripts/adhoc/test_d76_phase_accounting_20261031.py | 86 | test_retained_interrupted_probe_ledger_has_only_two_complete_passes | def test_retained_interrupted_probe_ledger_has_only_two_complete_passes(): |
| probe | src/data_sheets_schema/native_execution.py | 106 | _probe_runtime | def _probe_runtime(value): |
| probe | src/data_sheets_schema/native_execution_permissions.py | 82 | probe_cases | def probe_cases(expected): |
| probe | src/data_sheets_schema/native_execution_permissions.py | 99 | probe_argv | def probe_argv(expected): |
| probe | src/data_sheets_schema/native_execution_permissions.py | 281 | verify_saved_probe | def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict: |
| probe | src/data_sheets_schema/native_permission_probe.py | 108 | _loaded_probe_inputs | def _loaded_probe_inputs(expected): |
| probe | src/data_sheets_schema/native_permission_probe.py | 625 | produce_saved_probe | def produce_saved_probe(expected, directory, *, deadline_seconds): |
| probe | src/data_sheets_schema/native_shared_permission_orchestration.py | 30 | verify_saved_probe | def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict: |
| probe | src/data_sheets_schema/native_shared_permission_orchestration.py | 39 | probe_argv | def probe_argv(expected, probe_policy): |
| probe | src/data_sheets_schema/native_shared_permissions.py | 415 | probe_argv | def probe_argv(expected, probe_policy): |
| probe | src/data_sheets_schema/native_shared_permissions.py | 536 | probe_cases | def probe_cases(expected, selection, launch, session_id, *, policy=None, recipe=None): |
| probe | src/data_sheets_schema/native_shared_permissions.py | 997 | verify_saved_probe | def verify_saved_probe(raw_manifest: bytes, *, expected: dict, controls, controller_sources) -> dict: |
| probe | src/data_sheets_schema/native_u4b_probe_sequence.py | 401 | produce_bound_probe | def produce_bound_probe(authorization_raw, expected, directory=None): |
| probe | src/data_sheets_schema/native_u4b_probe_sequence.py | 440 | validate_bound_probe | def validate_bound_probe(runtime, permission_probe_path): |
| probe | src/data_sheets_schema/native_u4b_runtime.py | 80 | _saved_probe | def _saved_probe(path, model_pair=None): |
| probe | src/data_sheets_schema/schema_sync.py | 325 | _probe | def _probe(class_name, schema, vocabulary, name, profile): |

### 3C. Test Paths Inside scripts/ (scripts/.../tests/*)

| Word | File | Line | Function Name | Stripped Definition Line |
|---|---|---:|---|---|
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/round2_binding_source.py | 152 | test_all_runspec_registration_and_version_axes_have_a_binding_classification | def test_all_runspec_registration_and_version_axes_have_a_binding_classification(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/round2_binding_source.py | 163 | test_registration_spelling_policy_is_version_agnostic | def test_registration_spelling_policy_is_version_agnostic(mechanism, version): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/round2_binding_source.py | 179 | test_shared_generation_requires_registration_to_select_binding | def test_shared_generation_requires_registration_to_select_binding(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/round2_binding_source.py | 185 | test_standalone_receipt_registration_has_no_input_authority | def test_standalone_receipt_registration_has_no_input_authority(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_r3_anchor_probes.py | 230 | test_native_write_registration_with_cached_instruction | def test_native_write_registration_with_cached_instruction(external, monkeypatch, tmp_path): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/round2_binding_source.py | 152 | test_all_runspec_registration_and_version_axes_have_a_binding_classification | def test_all_runspec_registration_and_version_axes_have_a_binding_classification(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/round2_binding_source.py | 163 | test_registration_spelling_policy_is_version_agnostic | def test_registration_spelling_policy_is_version_agnostic(mechanism, version): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/round2_binding_source.py | 179 | test_shared_generation_requires_registration_to_select_binding | def test_shared_generation_requires_registration_to_select_binding(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/round2_binding_source.py | 185 | test_standalone_receipt_registration_has_no_input_authority | def test_standalone_receipt_registration_has_no_input_authority(): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/test_new_public_registration.py | 13 | test_native_registration_refuses_drift_before_reading_input_pins | def test_native_registration_refuses_drift_before_reading_input_pins(case, monkeypatch, tmp_path, entry): |
| registration | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/test_recheck_edges.py | 85 | test_cwd_dependent_chunk_discovery_cannot_silently_change_registration | def test_cwd_dependent_chunk_discovery_cannot_silently_change_registration(external, tmp_path, monkeypatch, selected_manifest): |
| review | none | none | none | none |
| bundle | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_probe_recorder_residuals.py | 77 | test_c_different_byte_identical_bundle_is_never_a_match | def test_c_different_byte_identical_bundle_is_never_a_match(project_tree, monkeypatch): |
| bundle | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/test_new_guard.py | 206 | test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction | def test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction(external, monkeypatch): |
| bundle | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/test_new_recorder.py | 28 | test_explicit_rendering_bundle_cannot_hide_a_different_recorded_input | def test_explicit_rendering_bundle_cannot_hide_a_different_recorded_input(project_tree, monkeypatch, same_bytes): |
| launch_word | none | none | none | none |
| word | none | none | none | none |
| account_choice | none | none | none | none |
| statement | none | none | none | none |
| runtime | none | none | none | none |
| capture | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_codex_r2_round2_adversarial_copy.py | 112 | test_uncaptured_binding_selectors_cannot_disable_a_captured_anchor | def test_uncaptured_binding_selectors_cannot_disable_a_captured_anchor( |
| capture | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/codex/test_round2_adversarial.py | 111 | test_uncaptured_binding_selectors_cannot_disable_a_captured_anchor | def test_uncaptured_binding_selectors_cannot_disable_a_captured_anchor( |
| guard | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_r2_boundary_probes.py | 72 | test_private_binding_replacement_bypasses_the_guard | def test_private_binding_replacement_bypasses_the_guard(external, monkeypatch): |
| guard | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_r2_boundary_probes.py | 136 | test_order_native_offline_refusal_precedes_the_guard | def test_order_native_offline_refusal_precedes_the_guard(external, monkeypatch): |
| guard | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_r2_boundary_probes.py | 148 | test_order_historical_replay_precedes_the_guard | def test_order_historical_replay_precedes_the_guard(external, monkeypatch): |
| guard | scripts/adhoc/d76_round4_review_witnesses_20261103/tests/claude/test_r2_boundary_probes.py | 160 | test_dry_run_is_guarded_and_free | def test_dry_run_is_guarded_and_free(external, monkeypatch): |
| ci_evidence | none | none | none | none |
| probe | none | none | none | none |

### 3D. Test Paths in Top-Level tests/

| Word | File | Line | Function Name | Stripped Definition Line |
|---|---|---:|---|---|
| registration | tests/test_anonymous_removal_renderer.py | 78 | test_generation_registration_exposes_explicit_v15_without_changing_its_default | def test_generation_registration_exposes_explicit_v15_without_changing_its_default(): |
| registration | tests/test_api_dollar_readout.py | 260 | test_uncounted_pending_uses_pinned_registration_window | def test_uncounted_pending_uses_pinned_registration_window(phase, cap): |
| registration | tests/test_audit_batch_context.py | 187 | test_registration_context_errors_fail_closed | def test_registration_context_errors_fail_closed(staged, damage): |
| registration | tests/test_audit_recall_leak.py | 181 | registration_records | def registration_records(): |
| registration | tests/test_audit_recall_leak.py | 297 | test_a_new_registrations_prompts_and_requests_are_found_by_name | def test_a_new_registrations_prompts_and_requests_are_found_by_name(tmp_path): |
| registration | tests/test_audit_recall_leak.py | 318 | test_no_registration_record_under_notes_does | def test_no_registration_record_under_notes_does(needles): |
| registration | tests/test_audit_recall_leak_rendered.py | 329 | direct_registration | def direct_registration(tmp_path, monkeypatch): |
| registration | tests/test_audit_record_contract.py | 132 | test_registration_selects_the_new_contract_and_retains_default | def test_registration_selects_the_new_contract_and_retains_default(tmp_path, runtime): |
| registration | tests/test_bc1_registration.py | 106 | test_registration_allowances_include_all_groups_and_separate_final | def test_registration_allowances_include_all_groups_and_separate_final(fan, workers): |
| registration | tests/test_build_api_registrations.py | 179 | test_build_registration_chorus_baseline | def test_build_registration_chorus_baseline(tmp_path: Path) -> None: |
| registration | tests/test_build_api_registrations.py | 231 | test_build_registration_arms | def test_build_registration_arms(tmp_path: Path) -> None: |
| registration | tests/test_build_api_registrations.py | 252 | test_build_registration_custom_limits_and_prefix | def test_build_registration_custom_limits_and_prefix(tmp_path: Path) -> None: |
| registration | tests/test_build_api_registrations.py | 275 | test_build_registration_error_cases | def test_build_registration_error_cases(tmp_path: Path) -> None: |
| registration | tests/test_build_api_registrations.py | 541 | test_build_registration_kids_first_neutral_profile | def test_build_registration_kids_first_neutral_profile(tmp_path: Path) -> None: |
| registration | tests/test_build_draft_contexts.py | 158 | test_build_registration_finds_draft_contexts | def test_build_registration_finds_draft_contexts(tmp_path): |
| registration | tests/test_canary_attempt_caps.py | 120 | test_legacy_default_registration_remains_five_dollars | def test_legacy_default_registration_remains_five_dollars(tmp_path): |
| registration | tests/test_canary_budget_continuation.py | 97 | test_relocated_registration_shares_all_subsequent_accounting | def test_relocated_registration_shares_all_subsequent_accounting(tmp_path,condition): |
| registration | tests/test_dc_output_caps.py | 65 | test_readout_without_a_v10_registration_keeps_the_historical_caps | def test_readout_without_a_v10_registration_keeps_the_historical_caps(): |
| registration | tests/test_dc_output_caps.py | 77 | test_the_readout_finds_a_v10_ledgers_registration_itself | def test_the_readout_finds_a_v10_ledgers_registration_itself(): |
| registration | tests/test_direct_keep_awake.py | 110 | registration | def registration(tmp_path): |
| registration | tests/test_direct_keep_awake.py | 138 | test_changed_registration_or_spent_attempt_refuses_before_acquisition | def test_changed_registration_or_spent_attempt_refuses_before_acquisition(registration, monkeypatch, change): |
| registration | tests/test_e3x_guard_kills.py | 59 | test_kill_I5_provenance_embeds_another_registration | def test_kill_I5_provenance_embeds_another_registration(registered_case): |
| registration | tests/test_evaluation/test_cross_family_judge_panel.py | 259 | test_closed_registration_and_real_identity_refuse_aliases | def test_closed_registration_and_real_identity_refuse_aliases(fixture, tmp_path, seam): |
| registration | tests/test_evaluation/test_cross_family_judge_panel.py | 453 | test_atomic_registration_refuses_racing_output_without_overwrite | def test_atomic_registration_refuses_racing_output_without_overwrite(fixture, tmp_path, monkeypatch, winner): |
| registration | tests/test_evaluation/test_cross_family_panel_adversarial.py | 275 | test_returned_registration_mutation_cannot_change_pair_or_recheck_authority | def test_returned_registration_mutation_cannot_change_pair_or_recheck_authority(case): |
| registration | tests/test_evaluation/test_cross_family_panel_results.py | 127 | test_old_validator_panel_is_preserved_unsupported_then_fresh_predecessor_registration | def test_old_validator_panel_is_preserved_unsupported_then_fresh_predecessor_registration(prepared, tmp_path): |
| registration | tests/test_evaluation/test_support_calibration_adversarial.py | 160 | test_same_targets_from_another_registration_are_not_an_implicit_retry | def test_same_targets_from_another_registration_are_not_an_implicit_retry(scenario): |
| registration | tests/test_g2_comparator.py | 71 | test_named_captures_preserve_prior_evidence_and_bind_selected_registration | def test_named_captures_preserve_prior_evidence_and_bind_selected_registration(captures): |
| registration | tests/test_g2_round2.py | 317 | test_incomplete_registration_cannot_borrow_calibration | def test_incomplete_registration_cannot_borrow_calibration(tmp_path): |
| registration | tests/test_generality_tuned.py | 8 | test_new_tuned_registration_refused_before_outputs | def test_new_tuned_registration_refused_before_outputs(project, tmp_path): |
| registration | tests/test_installed_agentic_identity.py | 138 | test_preimage_registration_uses_only_the_selected_checkout | def test_preimage_registration_uses_only_the_selected_checkout(tmp_path, monkeypatch): |
| registration | tests/test_installed_agentic_identity.py | 172 | test_preimage_registration_rejects_cross_checkout_paths | def test_preimage_registration_rejects_cross_checkout_paths(tmp_path, monkeypatch, damage): |
| registration | tests/test_native_authority_v2.py | 36 | test_v2_registration_composition_and_supervisor | def test_v2_registration_composition_and_supervisor(isolated): |
| registration | tests/test_native_authority_v2.py | 65 | test_v2_registration_cannot_name_v1 | def test_v2_registration_cannot_name_v1(isolated): |
| registration | tests/test_native_execution.py | 318 | test_registration_output_cannot_consume_its_own_future_attempt | def test_registration_output_cannot_consume_its_own_future_attempt(case): |
| registration | tests/test_native_execution_observation.py | 56 | test_expected_identity_preserves_registration_across_fingerprint_boundary | def test_expected_identity_preserves_registration_across_fingerprint_boundary(tmp_path,monkeypatch,change): |
| registration | tests/test_native_generation_frontdoor.py | 252 | test_v4_choice_cannot_bless_rehashed_v5_registration_metadata | def test_v4_choice_cannot_bless_rehashed_v5_registration_metadata(saved_case, tmp_path, monkeypatch): |
| registration | tests/test_native_generation_frontdoor.py | 295 | test_bad_registration_refuses_without_guard_or_native_side_effects | def test_bad_registration_refuses_without_guard_or_native_side_effects(tmp_path, monkeypatch): |
| registration | tests/test_native_phase_scope_rendering.py | 46 | test_registration_cli_accepts_the_new_renderer_without_changing_default | def test_registration_cli_accepts_the_new_renderer_without_changing_default(tmp_path): |
| registration | tests/test_native_receipt_origin_reporting.py | 32 | _registration | def _registration(case, family, selector=_OMITTED): |
| registration | tests/test_native_receipt_origin_reporting.py | 52 | test_default_and_explicit_zero_preserve_registration_bytes | def test_default_and_explicit_zero_preserve_registration_bytes(registered_case): |
| registration | tests/test_native_receipt_origin_reporting.py | 70 | test_registration_derives_paths_and_refuses_forged_declarations | def test_registration_derives_paths_and_refuses_forged_declarations(registered_case): |
| registration | tests/test_native_registered_provenance.py | 52 | test_registration_to_rendered_command_to_recording_to_exact_replay | def test_registration_to_rendered_command_to_recording_to_exact_replay(native): |
| registration | tests/test_native_shared_consumer_census.py | 119 | test_real_c_dependent_registration_graph_must_be_accepted_for_integration | def test_real_c_dependent_registration_graph_must_be_accepted_for_integration(isolated_modules): |
| registration | tests/test_native_shared_initial_receipts.py | 72 | test_pending_registration_is_disclosed_without_certifying_a_final_floor | def test_pending_registration_is_disclosed_without_certifying_a_final_floor(case): |
| registration | tests/test_native_shared_registration.py | 52 | test_closed_registration_checks_actual_selected_policy_and_does_not_reserve | def test_closed_registration_checks_actual_selected_policy_and_does_not_reserve(execution, record_property): |
| registration | tests/test_native_shared_registration.py | 100 | test_registration_refuses_separate_count_and_rehashed_permission_contradiction | def test_registration_refuses_separate_count_and_rehashed_permission_contradiction(execution): |
| registration | tests/test_native_source_attribution.py | 198 | test_registration_drift_duplicate_keys_no_overwrite_and_execution_refusal | def test_registration_drift_duplicate_keys_no_overwrite_and_execution_refusal(case, tmp_path, monkeypatch): |
| registration | tests/test_native_source_attribution.py | 257 | test_actual_old_launcher_refuses_new_registration_before_any_launch_action | def test_actual_old_launcher_refuses_new_registration_before_any_launch_action(case, tmp_path): |
| registration | tests/test_native_source_attribution.py | 382 | test_registration_will_not_add_itself_to_the_captured_checker_tree | def test_registration_will_not_add_itself_to_the_captured_checker_tree(case): |
| registration | tests/test_native_subscription_capture.py | 269 | test_registration_reconstruction_refusal_prevents_capture | def test_registration_reconstruction_refusal_prevents_capture(tmp_path, monkeypatch): |
| registration | tests/test_native_subscription_capture.py | 375 | test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root | def test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root( |
| registration | tests/test_native_synthetic_profiles.py | 261 | test_real_registration_refuses_before_observation | def test_real_registration_refuses_before_observation(runtime, monkeypatch): |
| registration | tests/test_native_u1_selector_refusals.py | 63 | test_each_old_registration_refuses_before_discovery | def test_each_old_registration_refuses_before_discovery(native_spec, monkeypatch, axis): |
| registration | tests/test_native_u3d_round9_boundaries.py | 167 | test_unmasked_shared_registration_constants_equal_the_real_a_contract | def test_unmasked_shared_registration_constants_equal_the_real_a_contract(isolated_modules): |
| registration | tests/test_native_u3f2_construction.py | 114 | test_registration_factory_checks_real_constructed_replay_with_genuine_controls | def test_registration_factory_checks_real_constructed_replay_with_genuine_controls(composed): |
| registration | tests/test_native_u3f2_construction.py | 152 | test_registration_scanner_literals_equal_shared_contract | def test_registration_scanner_literals_equal_shared_contract(): |
| registration | tests/test_native_u4b_a3_captures.py | 50 | test_any_limits_mismatch_permanently_refuses_registration_across_words | def test_any_limits_mismatch_permanently_refuses_registration_across_words(tmp_path, monkeypatch, mode, index): |
| registration | tests/test_native_u4b_a3_captures.py | 240 | test_activation_requires_explicit_registration_validity_before_state_creation | def test_activation_requires_explicit_registration_validity_before_state_creation(tmp_path, monkeypatch, location): |
| registration | tests/test_native_u4b_a3_policy.py | 121 | test_guard_runtime_is_exactly_the_runtime_in_registration_bytes | def test_guard_runtime_is_exactly_the_runtime_in_registration_bytes(case): |
| registration | tests/test_native_u4b_a4_review.py | 29 | test_real_documents_and_registration_commit_rechecked_on_each_validation | def test_real_documents_and_registration_commit_rechecked_on_each_validation(evidence): |
| registration | tests/test_native_u4b_a4_review.py | 146 | test_registration_commit_anchor_refusals | def test_registration_commit_anchor_refusals(evidence, tmp_path, mutation): |
| registration | tests/test_native_u4b_a4_review.py | 184 | test_registration_anchor_reads_objects_not_mutable_worktree_file | def test_registration_anchor_reads_objects_not_mutable_worktree_file(evidence): |
| registration | tests/test_native_u4b_registration_observation.py | 21 | registration_body | def registration_body(tmp_path): |
| registration | tests/test_native_u4b_registration_observation.py | 78 | test_public_registration_refuses_unobserved_or_contradictory_thinking | def test_public_registration_refuses_unobserved_or_contradictory_thinking( |
| registration | tests/test_pr5212_r3_fixes.py | 109 | test_batch_checks_registration_hash_and_journal_head_together | def test_batch_checks_registration_hash_and_journal_head_together(registered, tmp_path, monkeypatch, damage): |
| registration | tests/test_preflight_resource_authority.py | 55 | _registration | def _registration(directory): |
| registration | tests/test_receipt_completion_policy.py | 16 | registration | def registration(floor=None): |
| registration | tests/test_receipt_completion_policy.py | 46 | test_registration_refuses_ambiguous_or_unregistered_values | def test_registration_refuses_ambiguous_or_unregistered_values(change): |
| registration | tests/test_receipt_completion_policy.py | 52 | test_registration_requires_strict_json | def test_registration_requires_strict_json(raw): |
| registration | tests/test_receipt_completion_policy.py | 235 | test_disk_rebuild_selects_registration_instrument_and_retains_legacy | def test_disk_rebuild_selects_registration_instrument_and_retains_legacy(disk, snapshot, at_receipt): |
| registration | tests/test_receipt_completion_runtime.py | 28 | registration | def registration(condition='generic_v8', **changes): |
| registration | tests/test_receipt_completion_runtime.py | 131 | test_registration_is_required_and_cannot_be_silent_metadata | def test_registration_is_required_and_cannot_be_silent_metadata(external): |
| registration | tests/test_receipt_completion_runtime.py | 402 | test_cli_plan_selects_exact_registration_and_does_not_run | def test_cli_plan_selects_exact_registration_and_does_not_run(selected, tmp_path): |
| registration | tests/test_receipt_floor_basis.py | 446 | test_a_basis_is_refused_outside_v2_registrations | def test_a_basis_is_refused_outside_v2_registrations(): |
| registration | tests/test_reference_rescore.py | 817 | test_missing_output_does_not_allow_duplicate_current_registration_receipts | def test_missing_output_does_not_allow_duplicate_current_registration_receipts(retained_canary, entrypoint): |
| registration | tests/test_reference_rescore_cborg.py | 80 | test_identity_metadata_comes_from_registration_not_record_contents | def test_identity_metadata_comes_from_registration_not_record_contents(): |
| registration | tests/test_reference_rescore_cborg_batch.py | 76 | test_review_must_approve_the_exact_registration | def test_review_must_approve_the_exact_registration(tmp_path, monkeypatch): |
| registration | tests/test_reference_rescore_cborg_batch.py | 83 | test_pilot_acceptance_binds_the_output_and_registration | def test_pilot_acceptance_binds_the_output_and_registration(tmp_path, monkeypatch): |
| registration | tests/test_registered_eval_runner.py | 54 | registration | def registration(tmp_path_factory): |
| registration | tests/test_registered_eval_runner.py | 113 | test_copied_registration_run_control | def test_copied_registration_run_control(registration, tmp_path): |
| registration | tests/test_registered_eval_runner.py | 202 | test_preparation_validates_real_registration_and_separate_context | def test_preparation_validates_real_registration_and_separate_context(prepared, registration): |
| registration | tests/test_registered_eval_runner.py | 495 | test_registration_context_hash_and_shape_are_actually_checked | def test_registration_context_hash_and_shape_are_actually_checked(registration, tmp_path): |
| registration | tests/test_registered_eval_runner.py | 511 | test_changed_schema_closure_is_not_a_cosmetic_registration | def test_changed_schema_closure_is_not_a_cosmetic_registration(registration, tmp_path): |
| registration | tests/test_registered_eval_runner.py | 736 | test_record_cannot_borrow_another_run_registration | def test_record_cannot_borrow_another_run_registration(registration, tmp_path, mutation, match): |
| registration | tests/test_registration_input_sizing.py | 213 | test_the_sizing_is_recorded_beside_the_registration_and_checked_against_its_bytes | def test_the_sizing_is_recorded_beside_the_registration_and_checked_against_its_bytes(tmp_path): |
| registration | tests/test_routed_condition_reporting.py | 143 | test_recorded_registration_json_has_finite_closed_resource_behavior | def test_recorded_registration_json_has_finite_closed_resource_behavior(routed, payload): |
| registration | tests/test_semantic_v4_reporting_controller.py | 104 | test_bad_v4_registration_is_rejected_before_any_cli_call | def test_bad_v4_registration_is_rejected_before_any_cli_call(v4_environment, mutation): |
| registration | tests/test_shared_generation_cli.py | 100 | test_invalid_registration_selection_is_named_refusal | def test_invalid_registration_selection_is_named_refusal(registered, case): |
| registration | tests/test_shared_generation_cli.py | 122 | test_changed_registration_after_plan_refuses_before_execute | def test_changed_registration_after_plan_refuses_before_execute(registered, monkeypatch): |
| registration | tests/test_shared_generation_cli.py | 152 | test_batch_exact_roster_routes_each_registration | def test_batch_exact_roster_routes_each_registration(registered,monkeypatch): |
| registration | tests/test_shared_generation_cli.py | 278 | test_registration_special_file_is_refused_without_blocking | def test_registration_special_file_is_refused_without_blocking(tmp_path): |
| registration | tests/test_shared_generation_cli.py | 334 | test_a_shared_registration_names_its_own_method_without_the_runtime_default | def test_a_shared_registration_names_its_own_method_without_the_runtime_default(registered, monkeypatch): |
| registration | tests/test_shared_generation_scope_context.py | 26 | _context_registration | def _context_registration(base, update): |
| registration | tests/test_shared_generation_selection.py | 17 | registration_for | def registration_for(spec, *, condition='generic_v10'): |
| registration | tests/test_shared_generation_selection.py | 136 | test_registration_ambiguous_json_refuses | def test_registration_ambiguous_json_refuses(external): |
| registration | tests/test_shared_generation_selection.py | 155 | test_legacy_registration_never_admits_v10 | def test_legacy_registration_never_admits_v10(): |
| registration | tests/test_source_heading_runtime_api.py | 407 | test_selected_registration_binds_actual_normalization_bytes | def test_selected_registration_binds_actual_normalization_bytes(tmp_path, draft_files, monkeypatch, module): |
| registration | tests/test_source_heading_runtime_api.py | 626 | test_selected_registration_binds_live_historical_validation | def test_selected_registration_binds_live_historical_validation(tmp_path, draft_files, monkeypatch, module): |
| registration | tests/test_wave4_5095_review.py | 23 | registration | def registration(tmp_path): |
| registration | tests/test_wave4_a17_a13_integration.py | 16 | test_staged_replacement_roster_pins_the_new_registration | def test_staged_replacement_roster_pins_the_new_registration(tmp_path): |
| registration | tests/test_wave4_a17_a13_integration.py | 33 | test_existing_registration_roster_keeps_actual_serialization | def test_existing_registration_roster_keeps_actual_serialization(tmp_path): |
| registration | tests/test_wave5_5095_review.py | 32 | test_check_verifies_roster_registration_and_requires_out_dir_path | def test_check_verifies_roster_registration_and_requires_out_dir_path(checked_batch, tmp_path, drift): |
| registration | tests/test_wave5_5095_review.py | 55 | test_check_requires_out_dir_declared_registration_path | def test_check_requires_out_dir_declared_registration_path(checked_batch, tmp_path): |
| registration | tests/test_wave5_5095_review.py | 69 | test_check_requires_same_registration_bytes_at_roster_capture | def test_check_requires_same_registration_bytes_at_roster_capture(checked_batch, monkeypatch): |
| registration | tests/test_wave7_5213_d76_registration.py | 123 | test_native_execution_registration_from_corpus_root_verifies_saved_probe | def test_native_execution_registration_from_corpus_root_verifies_saved_probe(tmp_path, monkeypatch): |
| registration | tests/test_wave7_5213_d76_registration.py | 180 | test_no_input_pinning_registration_retains_relative_spelling | def test_no_input_pinning_registration_retains_relative_spelling(external, monkeypatch, receipt_only): |
| registration | tests/test_wave7_5213_d76_round2_binding.py | 210 | test_all_runspec_registration_and_version_axes_have_a_binding_classification | def test_all_runspec_registration_and_version_axes_have_a_binding_classification(): |
| registration | tests/test_wave7_5213_d76_round2_binding.py | 224 | test_registration_spelling_policy_is_version_agnostic | def test_registration_spelling_policy_is_version_agnostic(mechanism, version): |
| registration | tests/test_wave7_5213_d76_round2_binding.py | 240 | test_shared_generation_requires_registration_to_select_binding | def test_shared_generation_requires_registration_to_select_binding(): |
| registration | tests/test_wave7_5213_d76_round2_binding.py | 246 | test_standalone_receipt_registration_has_no_input_authority | def test_standalone_receipt_registration_has_no_input_authority(): |
| registration | tests/test_wave7_5213_d76_round3_binding.py | 144 | test_shared_binding_checks_parsed_registration_paths_before_authority | def test_shared_binding_checks_parsed_registration_paths_before_authority( |
| registration | tests/test_wave7_5213_d76_round4_boundaries.py | 73 | test_native_registration_refuses_drift_before_reading_input_pins | def test_native_registration_refuses_drift_before_reading_input_pins( |
| registration | tests/test_wave7_5213_d76_round4_boundaries.py | 147 | test_unchanged_native_spec_retains_valid_registration_and_exclusive_write | def test_unchanged_native_spec_retains_valid_registration_and_exclusive_write(case, tmp_path, entry): |
| registration | tests/test_wave7_5213_nf3.py | 55 | test_registration_fixture_authority_remains_absolute_when_inputs_relativize | def test_registration_fixture_authority_remains_absolute_when_inputs_relativize(external, monkeypatch): |
| registration | tests/utils/native_u4b_fixtures.py | 19 | registration_commit_for | def registration_commit_for(raw, directory, *, author_date): |
| review | tests/test_attainability.py | 818 | test_a_credit_on_an_item_a_route_entry_leaves_open_is_for_review_not_a_finding | def test_a_credit_on_an_item_a_route_entry_leaves_open_is_for_review_not_a_finding(tmp_path, capsys): |
| review | tests/test_attainability_figure.py | 70 | test_literal_state_score_and_review_oracle | def test_literal_state_score_and_review_oracle(tmp_path, name, readings, options, score, expected): |
| review | tests/test_audit_evaluation_comparability.py | 126 | test_current_bound_ratings_still_require_scientific_and_repeat_review | def test_current_bound_ratings_still_require_scientific_and_repeat_review(corpus): |
| review | tests/test_audit_evaluation_comparability.py | 187 | test_context_hash_presence_never_implies_target_selection_or_human_review | def test_context_hash_presence_never_implies_target_selection_or_human_review(corpus): |
| review | tests/test_audit_grammar.py | 32 | review_claim | def review_claim(value): |
| review | tests/test_audit_grammar.py | 194 | test_invalid_review_pointers | def test_invalid_review_pointers(pointer): |
| review | tests/test_audit_recall.py | 97 | test_review_path_hit_for_status_scope_and_the_supported_variant_misses | def test_review_path_hit_for_status_scope_and_the_supported_variant_misses(): |
| review | tests/test_audit_recall.py | 130 | test_an_unmatched_revise_path_is_a_review_candidate_not_a_false_positive | def test_an_unmatched_revise_path_is_a_review_candidate_not_a_false_positive(): |
| review | tests/test_audit_record_contract.py | 96 | test_record_names_cannot_replace_evidence_or_review_artifact_names | def test_record_names_cannot_replace_evidence_or_review_artifact_names(tmp_path, name, location): |
| review | tests/test_audit_record_contract.py | 108 | test_complete_example_still_requires_exact_originals_sources_and_review_coverage | def test_complete_example_still_requires_exact_originals_sources_and_review_coverage(tmp_path, damage): |
| review | tests/test_blind_review_pack.py | 97 | test_identical_scientific_records_can_keep_reviewer_bytes_when_seed_changes | def test_identical_scientific_records_can_keep_reviewer_bytes_when_seed_changes(tmp_path): |
| review | tests/test_blind_review_pack.py | 106 | test_key_hashes_blinding_review_sheet_and_permissions | def test_key_hashes_blinding_review_sheet_and_permissions(tmp_path): |
| review | tests/test_blind_review_pack.py | 247 | test_review_sheet_leakage_rejected_even_when_yaml_is_clean | def test_review_sheet_leakage_rejected_even_when_yaml_is_clean(tmp_path): |
| review | tests/test_blind_review_pack.py | 664 | test_short_arm_gate_checks_other_records_and_review_sheet | def test_short_arm_gate_checks_other_records_and_review_sheet(tmp_path): |
| review | tests/test_blind_review_pack.py | 684 | test_sorted_review_mapping_preserves_every_scientific_value_and_list_order | def test_sorted_review_mapping_preserves_every_scientific_value_and_list_order(tmp_path): |
| review | tests/test_blind_review_pack.py | 775 | test_key_cannot_resolve_inside_reviewer_directory | def test_key_cannot_resolve_inside_reviewer_directory(tmp_path, kind): |
| review | tests/test_blind_review_pack.py | 789 | test_private_key_published_and_read_back_before_reviewer_directory | def test_private_key_published_and_read_back_before_reviewer_directory(tmp_path, monkeypatch): |
| review | tests/test_blind_review_pack.py | 820 | test_key_publication_race_preserves_foreign_file_and_no_reviewer_output | def test_key_publication_race_preserves_foreign_file_and_no_reviewer_output(tmp_path, monkeypatch): |
| review | tests/test_blind_review_pack.py | 862 | test_key_and_review_are_rechecked_after_external_key_publication | def test_key_and_review_are_rechecked_after_external_key_publication(tmp_path, monkeypatch, change): |
| review | tests/test_d69_fail_closed.py | 29 | test_review_finding_one_single_artifact_refuses | def test_review_finding_one_single_artifact_refuses(tmp_path, name, resume): |
| review | tests/test_draft_grammar_protocol.py | 92 | test_source_review6_is_exactly5_for_positive_and_negative_scientific_cases | def test_source_review6_is_exactly5_for_positive_and_negative_scientific_cases(mutation): |
| review | tests/test_e3x_blinding_fixes.py | 65 | test_f5_review_campaign_identity_cannot_bypass_manifest | def test_f5_review_campaign_identity_cannot_bypass_manifest(tmp_path, fault): |
| review | tests/test_evaluation/test_cross_family_panel_adversarial.py | 186 | test_missing_context_is_unknown_even_with_record_claims_and_review_reference | def test_missing_context_is_unknown_even_with_record_claims_and_review_reference(case): |
| review | tests/test_evaluation/test_support_calibration.py | 92 | test_unreviewable_or_ambiguous_labels_refused_before_writing | def test_unreviewable_or_ambiguous_labels_refused_before_writing(controls, change): |
| review | tests/test_evaluation/test_support_calibration.py | 118 | test_duplicate_json_keys_cannot_change_review_status | def test_duplicate_json_keys_cannot_change_review_status(controls): |
| review | tests/test_evaluation/test_support_calibration_adversarial.py | 321 | test_claimed_review_reference_cannot_make_local_fixture_empirical | def test_claimed_review_reference_cannot_make_local_fixture_empirical(scenario): |
| review | tests/test_evaluation/test_support_calibration_adversarial.py | 337 | test_declared_reviewed_scope_still_does_not_authenticate_scientific_approval | def test_declared_reviewed_scope_still_does_not_authenticate_scientific_approval(scenario): |
| review | tests/test_evidence_anonymous_removals.py | 282 | reviewed | def reviewed(raw, *, artifact="original_full", chunks=None, rejected=()): |
| review | tests/test_evidence_phase_contract.py | 17 | test_complete_source_review_output_room_preserves_historical_limits | def test_complete_source_review_output_room_preserves_historical_limits(tmp_path, version, phase): |
| review | tests/test_evidence_phase_contract.py | 24 | test_complete_source_review_output_room_respects_route_limit | def test_complete_source_review_output_room_respects_route_limit(tmp_path, monkeypatch): |
| review | tests/test_generation_recovery_review.py | 20 | test_review_and_backfill_reproduce_the_recorded_instruction | def test_review_and_backfill_reproduce_the_recorded_instruction(external, monkeypatch, version, explicit): |
| review | tests/test_historical_eval_audit.py | 73 | test_committed_historical_package_reaches_condition_review_without_scientific_acceptance | def test_committed_historical_package_reaches_condition_review_without_scientific_acceptance( |
| review | tests/test_latch_journal.py | 226 | test_manual_pending_to_accepted_cannot_bypass_source_review | def test_manual_pending_to_accepted_cannot_bypass_source_review(tmp_path): |
| review | tests/test_manifest_corpus_review_r10.py | 13 | test_review_pack_keeps_its_recorded_bundle_and_chunk_map | def test_review_pack_keeps_its_recorded_bundle_and_chunk_map(tmp_path, monkeypatch, caller_location, caller_copies): |
| review | tests/test_manifest_corpus_review_r11.py | 55 | test_fresh_flat_records_keep_bundle_and_chunks_for_later_review | def test_fresh_flat_records_keep_bundle_and_chunks_for_later_review(tmp_path, monkeypatch, has_manifest, destination_kind): |
| review | tests/test_native_execution_round5_v2.py | 57 | test_review_src_alias_refused | def test_review_src_alias_refused(target, deferred): |
| review | tests/test_native_launch_review.py | 31 | test_two_reviews_and_exact_statement | def test_two_reviews_and_exact_statement(evidence): |
| review | tests/test_native_u3b_reuse.py | 409 | test_review_probe_ordinary_event_native_refusal_parity | def test_review_probe_ordinary_event_native_refusal_parity(raw): |
| review | tests/test_native_u3b_reuse.py | 418 | test_review_probe_bom_and_input_size_parity | def test_review_probe_bom_and_input_size_parity(): |
| review | tests/test_native_u3l_review_fixtures.py | 164 | test_retained_review_outcome | def test_retained_review_outcome(tmp_path, monkeypatch, case): |
| review | tests/test_native_u4b_a4_cross_word.py | 22 | test_capture_process_trap_leaves_real_review_git_reads_intact | def test_capture_process_trap_leaves_real_review_git_reads_intact(tmp_path, monkeypatch): |
| review | tests/test_native_u4b_a4_review.py | 46 | test_exact_two_distinct_review_kinds | def test_exact_two_distinct_review_kinds(evidence, kind): |
| review | tests/test_native_u4b_a4_review.py | 89 | test_reviewed_at_uses_strict_utc_grammar | def test_reviewed_at_uses_strict_utc_grammar(evidence, stamp): |
| review | tests/test_native_u4b_a4_review.py | 95 | test_reviewed_at_fraction_and_order | def test_reviewed_at_fraction_and_order(evidence): |
| review | tests/test_native_u4b_addendum_authority.py | 60 | test_real_v2_reader_consumes_two_review_bundle_and_replays_exact_bytes | def test_real_v2_reader_consumes_two_review_bundle_and_replays_exact_bytes(bundle_reader_case): |
| review | tests/test_native_u4b_addendum_authority.py | 79 | test_real_v2_reader_refuses_rehashed_bad_review_or_post_word_edit | def test_real_v2_reader_refuses_rehashed_bad_review_or_post_word_edit( |
| review | tests/test_q19_rationale_lint.py | 1699 | test_every_review_regression_reads_as_on_main | def test_every_review_regression_reads_as_on_main(issue, field, text, basis, verdict, concerns): |
| review | tests/test_reference_rescore_cborg_batch.py | 76 | test_review_must_approve_the_exact_registration | def test_review_must_approve_the_exact_registration(tmp_path, monkeypatch): |
| review | tests/test_reference_rescore_cborg_batch.py | 179 | reviewed_failure | def reviewed_failure(tmp_path, monkeypatch, *, status="incomplete", terminal=True): |
| review | tests/test_reference_rescore_cborg_batch.py | 193 | test_reviewed_retry_is_invalidated_by_any_new_attempt | def test_reviewed_retry_is_invalidated_by_any_new_attempt(tmp_path, monkeypatch): |
| review | tests/test_reference_rescore_cborg_batch.py | 201 | test_reviewed_retry_refuses_changed_failed_evidence | def test_reviewed_retry_refuses_changed_failed_evidence(tmp_path, monkeypatch): |
| review | tests/test_reference_rescore_cborg_batch.py | 210 | test_reviewed_retry_requires_exclusion_and_complete_cost_evidence | def test_reviewed_retry_requires_exclusion_and_complete_cost_evidence(tmp_path, monkeypatch, status, terminal, message): |
| review | tests/test_reference_rescore_cborg_batch.py | 253 | test_exact_reviewed_prelaunch_failure_allows_one_retry | def test_exact_reviewed_prelaunch_failure_allows_one_retry(prelaunch_case): |
| review | tests/test_reference_rescore_cborg_deadline.py | 131 | reviewed_timeout | def reviewed_timeout(tmp_path): |
| review | tests/test_registered_eval_runner.py | 423 | test_scientific_text_containing_run_identity_requires_review | def test_scientific_text_containing_run_identity_requires_review(): |
| review | tests/test_removal_repair.py | 100 | test_supported_review_needs_a_linked_finding_even_in_runtime_reading | def test_supported_review_needs_a_linked_finding_even_in_runtime_reading(): |
| review | tests/test_removals.py | 2315 | _review | def _review(original, judgments, sha=None): |
| review | tests/test_rereceipt_completion.py | 56 | test_status_reversal_is_preserved_counted_and_does_not_add_reviewed_chunks | def test_status_reversal_is_preserved_counted_and_does_not_add_reviewed_chunks(status, predicate): |
| review | tests/test_rereceipt_completion.py | 114 | test_completion_cannot_manufacture_chunk_review_coverage | def test_completion_cannot_manufacture_chunk_review_coverage(status): |
| review | tests/test_review_pack_schema_refresh.py | 9 | test_imported_identifier_change_refreshes_a_warm_review_pack | def test_imported_identifier_change_refreshes_a_warm_review_pack(tmp_path, monkeypatch): |
| review | tests/test_reviewer_basis.py | 38 | _reviews | def _reviews(): |
| review | tests/test_rocrate/test_legacy_root_narrative_descriptions.py | 135 | test_explicit_objects_detach_without_synthesized_review_or_access_fields | def test_explicit_objects_detach_without_synthesized_review_or_access_fields(implementation, tmp_path): |
| review | tests/test_shared_line_join_replay.py | 59 | test_exact_baseline_and_reviewed_candidate_compare_without_measurement | def test_exact_baseline_and_reviewed_candidate_compare_without_measurement(replay): |
| review | tests/test_shared_line_join_replay.py | 104 | test_changed_current_script_cannot_redefine_the_reviewed_candidate | def test_changed_current_script_cannot_redefine_the_reviewed_candidate(replay): |
| review | tests/test_source_attribution_preflight.py | 96 | test_no_authority_is_discovered_for_document_only_review | def test_no_authority_is_discovered_for_document_only_review(inputs, protocol, monkeypatch): |
| review | tests/test_source_attribution_preflight.py | 157 | test_vocabulary_pass_does_not_waive_other_source_review_failures | def test_vocabulary_pass_does_not_waive_other_source_review_failures(inputs, mutation): |
| review | tests/test_source_attribution_preflight.py | 164 | test_malformed_review_is_a_failed_preflight_not_a_crash | def test_malformed_review_is_a_failed_preflight_not_a_crash(inputs, payload): |
| review | tests/test_source_metadata_evidence.py | 41 | review | def review(raw=RAW, *, artifact="original_full", assertions=None): |
| review | tests/test_source_metadata_evidence.py | 212 | test_legacy_review_does_not_enable_provenance_or_change_instrument | def test_legacy_review_does_not_enable_provenance_or_change_instrument(version): |
| review | tests/test_source_metadata_renderer.py | 39 | review | def review(assertion, artifact='original_full'): |
| review | tests/test_source_metadata_renderer.py | 96 | test_explicit_no_manifest_keeps_neutral_v5_document_review_available | def test_explicit_no_manifest_keeps_neutral_v5_document_review_available(tmp_path): |
| review | tests/test_source_review.py | 27 | review_for | def review_for(raw, artifact='original_full', *, chunks=CHUNKS): |
| review | tests/test_source_review.py | 78 | test_mixed_status_prose_requires_separate_complete_reviews | def test_mixed_status_prose_requires_separate_complete_reviews(): |
| review | tests/test_source_review.py | 109 | test_audit_revisions_need_actionable_findings_and_cannot_survive_final_review | def test_audit_revisions_need_actionable_findings_and_cannot_survive_final_review(): |
| review | tests/test_source_review.py | 133 | test_nontext_scalars_cannot_be_reviewed_as_separate_fragments | def test_nontext_scalars_cannot_be_reviewed_as_separate_fragments(value,fragments): |
| review | tests/test_source_review.py | 237 | test_source_review_precedes_shape_repair_and_fresh_report | def test_source_review_precedes_shape_repair_and_fresh_report(tmp_path,monkeypatch,rejected): |
| review | tests/test_source_review.py | 263 | test_unusable_reviews_never_retry_or_resume | def test_unusable_reviews_never_retry_or_resume(tmp_path,monkeypatch,phase,kind,calls): |
| review | tests/test_source_review.py | 350 | test_interruption_between_accounting_and_review_blocks_resume_and_direct_calls | def test_interruption_between_accounting_and_review_blocks_resume_and_direct_calls(tmp_path,monkeypatch,phase,calls): |
| review | tests/test_source_review.py | 422 | test_real_native_final_checker_and_cli_require_final_source_review | def test_real_native_final_checker_and_cli_require_final_source_review(tmp_path,monkeypatch,unsupported): |
| review | tests/test_status_context.py | 1156 | _review | def _review(*rows): |
| review | tests/test_status_context.py | 1274 | test_a_review_naming_no_artifact_cannot_be_bound_to_a_record | def test_a_review_naming_no_artifact_cannot_be_bound_to_a_record(): |
| review | tests/test_status_context.py | 1375 | test_source_review_check_is_byte_identical_beside_the_diagnostic | def test_source_review_check_is_byte_identical_beside_the_diagnostic(): |
| review | tests/test_status_context.py | 1486 | test_the_review_cli_reads_an_audit_and_writes_nothing | def test_the_review_cli_reads_an_audit_and_writes_nothing(tmp_path): |
| review | tests/test_subprocess_deadline.py | 20 | test_default_route_has_no_review_adapter | def test_default_route_has_no_review_adapter(monkeypatch, tmp_path): |
| review | tests/test_subprocess_deadline.py | 26 | test_review_adapter_must_bind_source_and_bytes | def test_review_adapter_must_bind_source_and_bytes(monkeypatch, tmp_path, broken): |
| review | tests/test_subprocess_deadline.py | 62 | test_ordinary_child_strips_ambient_review_plugins_and_credentials | def test_ordinary_child_strips_ambient_review_plugins_and_credentials(monkeypatch): |
| review | tests/test_subprocess_deadline.py | 99 | test_ordinary_utility_and_sg2_wrapper_do_not_import_review_scripts | def test_ordinary_utility_and_sg2_wrapper_do_not_import_review_scripts(): |
| review | tests/test_transformation_measure.py | 103 | assert_review_oracle | def assert_review_oracle(result, full, pair_schema): |
| review | tests/test_transformation_measure.py | 115 | test_independent_review_oracle_matches_synthetic_nested_case | def test_independent_review_oracle_matches_synthetic_nested_case(pair_schema): |
| review | tests/test_transformation_measure.py | 281 | test_review_c2_c3_reordered_objects_claim_only_their_own_entity | def test_review_c2_c3_reordered_objects_claim_only_their_own_entity(pair_schema, kind): |
| review | tests/utils/isolated_pytest.py | 81 | review_adapter | def review_adapter(root): |
| bundle | tests/test_arm_comparison.py | 27 | _bundle_record | def _bundle_record(tmp_path, project="AI_READI", *, old=b"original", current=None): |
| bundle | tests/test_arm_comparison.py | 48 | test_bundle_drift_checks_every_arm_project_and_replicate | def test_bundle_drift_checks_every_arm_project_and_replicate(tmp_path): |
| bundle | tests/test_arm_comparison.py | 77 | test_bundle_drift_recovers_pinned_manifest_not_current_replacement | def test_bundle_drift_recovers_pinned_manifest_not_current_replacement(tmp_path): |
| bundle | tests/test_arm_comparison.py | 97 | test_bundle_drift_unavailable_history_never_uses_changed_manifest | def test_bundle_drift_unavailable_history_never_uses_changed_manifest(tmp_path, recovery): |
| bundle | tests/test_arm_comparison.py | 114 | test_bundle_drift_requires_every_manifest_hash | def test_bundle_drift_requires_every_manifest_hash(tmp_path): |
| bundle | tests/test_arm_comparison.py | 123 | test_bundle_drift_rejects_hash_pinned_duplicate_manifest_keys | def test_bundle_drift_rejects_hash_pinned_duplicate_manifest_keys(tmp_path): |
| bundle | tests/test_arm_comparison.py | 135 | test_bundle_drift_history_lookup_uses_recorded_name_after_symlink_change | def test_bundle_drift_history_lookup_uses_recorded_name_after_symlink_change(tmp_path): |
| bundle | tests/test_arm_comparison.py | 154 | test_bundle_drift_missing_pins_are_unknown_not_zero | def test_bundle_drift_missing_pins_are_unknown_not_zero(tmp_path, inputs): |
| bundle | tests/test_arm_comparison.py | 162 | test_bundle_drift_does_not_cache_current_disk_identity | def test_bundle_drift_does_not_cache_current_disk_identity(tmp_path): |
| bundle | tests/test_arm_comparison.py | 173 | test_bundle_drift_rejects_manifest_for_another_bundle | def test_bundle_drift_rejects_manifest_for_another_bundle(tmp_path): |
| bundle | tests/test_arm_comparison.py | 183 | test_bundle_drift_does_not_read_paths_outside_selected_checkout | def test_bundle_drift_does_not_read_paths_outside_selected_checkout(tmp_path): |
| bundle | tests/test_arm_comparison.py | 198 | test_bundle_drift_rejects_external_manifest_link_back_into_checkout | def test_bundle_drift_rejects_external_manifest_link_back_into_checkout(tmp_path): |
| bundle | tests/test_arm_comparison.py | 213 | test_bundle_drift_report_retains_denominators_unknowns_and_record_labels | def test_bundle_drift_report_retains_denominators_unknowns_and_record_labels(tmp_path): |
| bundle | tests/test_arm_comparison.py | 228 | test_bundle_drift_cli_reads_explicit_cohort_without_writing | def test_bundle_drift_cli_reads_explicit_cohort_without_writing(tmp_path, capsys): |
| bundle | tests/test_arm_comparison.py | 265 | test_cross_arm_different_recorded_bundles_can_each_match_their_manifest | def test_cross_arm_different_recorded_bundles_can_each_match_their_manifest(tmp_path): |
| bundle | tests/test_arm_comparison.py | 626 | test_report_bundle_drift_uses_selected_cohort_in_stable_order | def test_report_bundle_drift_uses_selected_cohort_in_stable_order(tmp_path, monkeypatch): |
| bundle | tests/test_arm_comparison.py | 644 | test_bundle_drift_survives_real_metrics_collection | def test_bundle_drift_survives_real_metrics_collection(tmp_path, monkeypatch): |
| bundle | tests/test_arm_comparison.py | 671 | _assert_selected_bundle_invariants | def _assert_selected_bundle_invariants(m, data, comparisons): |
| bundle | tests/test_arm_comparison.py | 696 | test_bundle_invariants_survive_legitimate_revision_and_replicate_reordering | def test_bundle_invariants_survive_legitimate_revision_and_replicate_reordering(tmp_path, monkeypatch): |
| bundle | tests/test_arm_comparison.py | 718 | test_bundle_history_unavailable_remains_unknown | def test_bundle_history_unavailable_remains_unknown(tmp_path): |
| bundle | tests/test_attainability.py | 147 | test_a_tampered_bundle_hash_is_refused | def test_a_tampered_bundle_hash_is_refused(field): |
| bundle | tests/test_attainability.py | 159 | test_a_tampered_bundle_hash_is_refused_where_git_cannot_answer | def test_a_tampered_bundle_hash_is_refused_where_git_cannot_answer(field): |
| bundle | tests/test_attainability.py | 370 | test_a_drifted_bundle_resolves_from_its_git_blob | def test_a_drifted_bundle_resolves_from_its_git_blob(): |
| bundle | tests/test_attainability.py | 630 | test_the_bundle_version_comes_from_the_records_provenance | def test_the_bundle_version_comes_from_the_records_provenance(tmp_path): |
| bundle | tests/test_attainability.py | 794 | test_a_bundle_path_carrying_a_nul_byte_is_a_problem_not_a_traceback | def test_a_bundle_path_carrying_a_nul_byte_is_a_problem_not_a_traceback(): |
| bundle | tests/test_attainability.py | 838 | test_a_bundle_path_no_file_system_can_hold_is_reported_and_the_next_file_still_checked | def test_a_bundle_path_no_file_system_can_hold_is_reported_and_the_next_file_still_checked(tmp_path, capsys): |
| bundle | tests/test_attainability.py | 971 | test_a_record_that_names_no_bundle_is_not_unreadable | def test_a_record_that_names_no_bundle_is_not_unreadable(tmp_path, body): |
| bundle | tests/test_attainability.py | 1175 | _gated_bundle | def _gated_bundle(tmp_path, text): |
| bundle | tests/test_attainability_check_gate.py | 165 | test_gate_keeps_validated_document_and_bundle_identity_if_inputs_change | def test_gate_keeps_validated_document_and_bundle_identity_if_inputs_change(tmp_path, monkeypatch, capsys, changed): |
| bundle | tests/test_chunking.py | 19 | _bundle | def _bundle(a_lines=5, b_lines=5): |
| bundle | tests/test_context_evidence_verbatim.py | 162 | test_every_evidence_string_occurs_verbatim_in_its_bundle | def test_every_evidence_string_occurs_verbatim_in_its_bundle(path, predicate): |
| bundle | tests/test_evaluation/test_nested_support_results.py | 186 | test_schema_and_bundle_changes_cannot_hide_behind_rehashed_pins | def test_schema_and_bundle_changes_cannot_hide_behind_rehashed_pins(plan, tmp_path): |
| bundle | tests/test_evaluation/test_support_judge.py | 510 | test_an_empty_value_or_missing_bundle_is_refused | def test_an_empty_value_or_missing_bundle_is_refused(): |
| bundle | tests/test_evaluation/test_support_plan.py | 224 | test_recovers_original_record_and_bundle_without_rewriting | def test_recovers_original_record_and_bundle_without_rewriting(fixture): |
| bundle | tests/test_evaluation/test_support_plan.py | 240 | test_unrecoverable_bundle_and_second_hash_disagreement_refuse | def test_unrecoverable_bundle_and_second_hash_disagreement_refuse(fixture): |
| bundle | tests/test_evaluation/test_support_plan.py | 440 | test_supplied_provenance_pin_controls_identity_and_bundle | def test_supplied_provenance_pin_controls_identity_and_bundle(fixture, drift): |
| bundle | tests/test_evaluation/test_verifiable_recorded_basis.py | 142 | test_changed_bundle_recovers_pinned_bytes_not_current_support | def test_changed_bundle_recovers_pinned_bytes_not_current_support(tmp_path): |
| bundle | tests/test_final_input_routing_review.py | 127 | test_recorded_name_reconstructs_a_recovered_git_blob_with_no_live_bundle | def test_recorded_name_reconstructs_a_recovered_git_blob_with_no_live_bundle(tmp_path, monkeypatch): |
| bundle | tests/test_g2_round2.py | 146 | test_declared_historical_bundle_is_verified | def test_declared_historical_bundle_is_verified(sizing_fixture, tmp_path, monkeypatch, project): |
| bundle | tests/test_generation_recovery_review.py | 196 | test_registry_bundle_audit_checks_external_destinations | def test_registry_bundle_audit_checks_external_destinations(tmp_path, damage): |
| bundle | tests/test_github_assistant_generation.py | 150 | test_changed_bundle_cannot_reach_api_plan | def test_changed_bundle_cannot_reach_api_plan(prepared_inputs): |
| bundle | tests/test_grounding_instrument.py | 66 | test_api_wrapper_keeps_instrument_and_bundle_attestation | def test_api_wrapper_keeps_instrument_and_bundle_attestation(run_files): |
| bundle | tests/test_manifest_corpus_review.py | 82 | test_programmatic_record_uses_manifest_outputs_and_preserves_explicit_bundle | def test_programmatic_record_uses_manifest_outputs_and_preserves_explicit_bundle(project_tree): |
| bundle | tests/test_manifest_corpus_review_r10.py | 13 | test_review_pack_keeps_its_recorded_bundle_and_chunk_map | def test_review_pack_keeps_its_recorded_bundle_and_chunk_map(tmp_path, monkeypatch, caller_location, caller_copies): |
| bundle | tests/test_manifest_corpus_review_r11.py | 55 | test_fresh_flat_records_keep_bundle_and_chunks_for_later_review | def test_fresh_flat_records_keep_bundle_and_chunks_for_later_review(tmp_path, monkeypatch, has_manifest, destination_kind): |
| bundle | tests/test_manifest_corpus_review_r12.py | 14 | test_auto_external_bundle_uses_the_same_output_owner_as_its_spec | def test_auto_external_bundle_uses_the_same_output_owner_as_its_spec(project_tree, monkeypatch, declares_unused): |
| bundle | tests/test_manifest_corpus_review_r16.py | 17 | test_bundle_drift_reads_only_the_selected_corpus | def test_bundle_drift_reads_only_the_selected_corpus(project_tree, monkeypatch, caller_kind, changed): |
| bundle | tests/test_manifest_corpus_review_r16.py | 50 | test_flat_record_does_not_borrow_the_callers_bundle | def test_flat_record_does_not_borrow_the_callers_bundle(tmp_path, monkeypatch): |
| bundle | tests/test_manifest_corpus_root.py | 28 | test_conventional_bundle_follows_the_explicit_manifest | def test_conventional_bundle_follows_the_explicit_manifest(project_tree): |
| bundle | tests/test_manifest_corpus_root.py | 46 | test_ancestor_discovery_keeps_context_bundles_and_chunks_in_one_tree | def test_ancestor_discovery_keeps_context_bundles_and_chunks_in_one_tree(project_tree, monkeypatch): |
| bundle | tests/test_measure_unhyphenated_line_splits.py | 54 | test_a_word_is_a_line_interior_token_of_the_bundle_or_an_entry_of_the_list | def test_a_word_is_a_line_interior_token_of_the_bundle_or_an_entry_of_the_list(m): |
| bundle | tests/test_measure_unhyphenated_line_splits.py | 90 | test_bundle_versions_count_records_and_list_the_unreadable | def test_bundle_versions_count_records_and_list_the_unreadable(m, tmp_path): |
| bundle | tests/test_native_u4b_a4_review.py | 20 | changed_bundle | def changed_bundle(evidence, mutate): |
| bundle | tests/test_native_u4b_addendum_authority.py | 30 | bundle_reader_case | def bundle_reader_case(tmp_path, fabricated_authorizations): |
| bundle | tests/test_native_u4b_addendum_authority.py | 54 | read_bundle | def read_bundle(case): |
| bundle | tests/test_native_u4b_addendum_authority.py | 60 | test_real_v2_reader_consumes_two_review_bundle_and_replays_exact_bytes | def test_real_v2_reader_consumes_two_review_bundle_and_replays_exact_bytes(bundle_reader_case): |
| bundle | tests/test_profile_review_r9.py | 128 | test_real_null_bundle_identity_is_self_comparable | def test_real_null_bundle_identity_is_self_comparable(generation): |
| bundle | tests/test_recall_target_baseline.py | 927 | test_every_parenthesised_version_citation_in_the_bundles_is_a_fact_or_named_as_not_software | def test_every_parenthesised_version_citation_in_the_bundles_is_a_fact_or_named_as_not_software(): |
| bundle | tests/test_receipt_sources.py | 544 | test_run_chunks_recovers_a_drifted_bundle_from_the_committed_version | def test_run_chunks_recovers_a_drifted_bundle_from_the_committed_version(tmp_path): |
| bundle | tests/test_receipts_v5_upgrade.py | 29 | _sample_bundle | def _sample_bundle() -> tuple[dict, dict[str, str], str]: |
| bundle | tests/test_release_inventory.py | 95 | test_no_document_bundle_contains_rocrate_content | def test_no_document_bundle_contains_rocrate_content(project): |
| bundle | tests/test_release_inventory.py | 400 | test_in_bundle_matches_sources_exactly_as_check_manifest_does | def test_in_bundle_matches_sources_exactly_as_check_manifest_does(tmp_path): |
| bundle | tests/test_release_inventory.py | 551 | test_an_in_bundle_value_that_is_not_an_id_is_listed | def test_an_in_bundle_value_that_is_not_an_id_is_listed(entries, not_ids, unmatched, tmp_path): |
| bundle | tests/test_replicate_structure.py | 329 | _bundle_inputs | def _bundle_inputs(root, text): |
| bundle | tests/test_rereceipt_completion.py | 216 | test_forged_chunk_manifest_is_refused_even_with_matching_bundle_hash | def test_forged_chunk_manifest_is_refused_even_with_matching_bundle_hash(): |
| bundle | tests/test_rocrate/test_legacy_route_disposition_publication.py | 56 | check_bundle | def check_bundle(path, expected_raw=RAW): |
| bundle | tests/test_shared_generation_condition_compatibility.py | 27 | test_registered_instruction_owns_its_project_bundle_and_receipt | def test_registered_instruction_owns_its_project_bundle_and_receipt(external, project): |
| bundle | tests/test_source_attribution_preflight.py | 119 | test_registered_id_outside_bundle_does_not_suggest_eligible_replacement | def test_registered_id_outside_bundle_does_not_suggest_eligible_replacement(inputs): |
| bundle | tests/test_source_metadata_evidence.py | 200 | test_missing_authority_rejects_provenance_but_permits_bundle_only_v5 | def test_missing_authority_rejects_provenance_but_permits_bundle_only_v5(): |
| bundle | tests/test_status_context.py | 33 | _bundle | def _bundle(*docs): |
| bundle | tests/test_status_context.py | 1227 | test_evidence_naming_no_chunk_of_the_bundle_is_counted_not_raised | def test_evidence_naming_no_chunk_of_the_bundle_is_counted_not_raised(chunk): |
| bundle | tests/test_status_context.py | 1349 | test_evidence_under_a_status_heading_is_read_with_the_bundle | def test_evidence_under_a_status_heading_is_read_with_the_bundle(): |
| bundle | tests/test_status_context.py | 1753 | test_run_mode_recovers_and_chunks_a_shared_drifted_bundle_once_per_process | def test_run_mode_recovers_and_chunks_a_shared_drifted_bundle_once_per_process(tmp_path, monkeypatch): |
| bundle | tests/test_v8_standards_explorer_publication.py | 46 | test_published_bundle_matches_historical_sources_and_all_scalar_values | def test_published_bundle_matches_historical_sources_and_all_scalar_values(): |
| bundle | tests/test_wave3_a23_review.py | 61 | test_all_pinned_bundles_chunks_and_citations_are_byte_verified | def test_all_pinned_bundles_chunks_and_citations_are_byte_verified(project): |
| bundle | tests/test_wave4_5095_review.py | 106 | test_input_pin_verifier_still_refuses_changed_bundle | def test_input_pin_verifier_still_refuses_changed_bundle(tmp_path): |
| bundle | tests/test_wave7_5213_d76_arm_paths.py | 39 | test_bundle_traversal_cannot_select_hash_matching_decoy | def test_bundle_traversal_cannot_select_hash_matching_decoy( |
| bundle | tests/test_wave7_5213_d76_recorder.py | 133 | test_backfill_non_string_bundle_is_a_controlled_no_match | def test_backfill_non_string_bundle_is_a_controlled_no_match(tmp_path, monkeypatch, bundle): |
| bundle | tests/test_wave7_5213_d76_round4_boundaries.py | 49 | test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction | def test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction(external): |
| bundle | tests/test_wave7_5213_d76_round4_recorder.py | 55 | test_in_place_bundle_edit_is_asserted_despite_absolute_bound_paths | def test_in_place_bundle_edit_is_asserted_despite_absolute_bound_paths( |
| bundle | tests/test_wave7_5213_d76_round4_recorder.py | 106 | test_matching_bound_manifest_verifies_only_the_evidenced_bundle | def test_matching_bound_manifest_verifies_only_the_evidenced_bundle( |
| bundle | tests/utils/native_u4b_fixtures.py | 48 | bundle_for | def bundle_for(registration_raw, directory, now='2026-11-08T00:00:00Z'): |
| launch_word | none | none | none | none |
| word | tests/test_attainability.py | 518 | test_every_claimed_compound_split_at_its_hyphen_and_inside_a_word_still_matches | def test_every_claimed_compound_split_at_its_hyphen_and_inside_a_word_still_matches(): |
| word | tests/test_audit_batches_split.py | 125 | test_chorus_v10_saved_run_differs_only_by_the_reworded_worker_sentence | def test_chorus_v10_saved_run_differs_only_by_the_reworded_worker_sentence(): |
| word | tests/test_blind_review_pack.py | 616 | test_short_arm_minimum_length_and_word_boundary_leakage | def test_short_arm_minimum_length_and_word_boundary_leakage(tmp_path): |
| word | tests/test_blind_review_pack.py | 638 | test_short_arm_inside_unicode_word_preserves_scientific_text | def test_short_arm_inside_unicode_word_preserves_scientific_text(tmp_path, arm, token, position): |
| word | tests/test_derive_core_selected_schemas.py | 129 | test_identity_keyword_reaches_all_library_outputs | def test_identity_keyword_reaches_all_library_outputs(tmp_path, selected_schemas): |
| word | tests/test_evaluation/test_support_judge.py | 202 | test_a_word_match_only_value_is_sent_and_unsupported_is_accepted | def test_a_word_match_only_value_is_sent_and_unsupported_is_accepted(): |
| word | tests/test_figure_set_2303_updates.py | 20 | test_fig02_caveat_mentions_slot_word_boundary_and_identifier_context | def test_fig02_caveat_mentions_slot_word_boundary_and_identifier_context(): |
| word | tests/test_manifest_gate_and_header_review.py | 82 | test_a_positive_manifest_path_containing_unused_words_is_still_selected | def test_a_positive_manifest_path_containing_unused_words_is_still_selected(prior, monkeypatch, relative): |
| word | tests/test_measure_unhyphenated_line_splits.py | 39 | test_the_split_word_and_the_joining_wrap_are_told_apart | def test_the_split_word_and_the_joining_wrap_are_told_apart(m): |
| word | tests/test_measure_unhyphenated_line_splits.py | 54 | test_a_word_is_a_line_interior_token_of_the_bundle_or_an_entry_of_the_list | def test_a_word_is_a_line_interior_token_of_the_bundle_or_an_entry_of_the_list(m): |
| word | tests/test_measure_unhyphenated_line_splits.py | 138 | test_the_command_refuses_a_missing_word_list | def test_the_command_refuses_a_missing_word_list(m, tmp_path, capsys): |
| word | tests/test_native_launch_review.py | 59 | test_independence_and_word_refusals | def test_independence_and_word_refusals(evidence, mutation): |
| word | tests/test_native_launch_review.py | 94 | test_coded_word_requires_strict_parsed_utc | def test_coded_word_requires_strict_parsed_utc(evidence, stamp): |
| word | tests/test_native_launch_review.py | 103 | test_coded_word_accepts_declared_utc_grammar | def test_coded_word_accepts_declared_utc_grammar(evidence, stamp): |
| word | tests/test_native_subscription_capture.py | 120 | word_directory | def word_directory(arguments): |
| word | tests/test_native_subscription_guard_v2.py | 147 | test_word_capture_and_actual_dispatch_chronology | def test_word_capture_and_actual_dispatch_chronology(case, captured_delta, dispatch_delta, passes): |
| word | tests/test_native_subscription_guard_v2.py | 158 | test_guard_independently_parses_word_timestamp_even_when_hash_rebound | def test_guard_independently_parses_word_timestamp_even_when_hash_rebound(case, value): |
| word | tests/test_native_subscription_guard_v2.py | 174 | test_duplicate_word_timestamp_cannot_choose_an_earlier_authorization | def test_duplicate_word_timestamp_cannot_choose_an_earlier_authorization(case): |
| word | tests/test_native_subscription_guard_v2.py | 204 | test_rehashed_word_cannot_relax_closed_protocol_or_owner_binding | def test_rehashed_word_cannot_relax_closed_protocol_or_owner_binding(case, key, value): |
| word | tests/test_native_synthetic_evidence.py | 15 | test_capture_chronology_does_not_borrow_an_older_word_time | def test_capture_chronology_does_not_borrow_an_older_word_time(tmp_path, monkeypatch): |
| word | tests/test_native_u3k_freshness_order.py | 80 | test_late_acceptance_rechecks_newer_current_word | def test_late_acceptance_rechecks_newer_current_word(tmp_path, monkeypatch): |
| word | tests/test_native_u4b_a3_captures.py | 50 | test_any_limits_mismatch_permanently_refuses_registration_across_words | def test_any_limits_mismatch_permanently_refuses_registration_across_words(tmp_path, monkeypatch, mode, index): |
| word | tests/test_native_u4b_a3_captures.py | 194 | test_new_word_restores_three_capture_slots_without_consuming_attempt | def test_new_word_restores_three_capture_slots_without_consuming_attempt(tmp_path, monkeypatch): |
| word | tests/test_native_u4b_a3_captures.py | 217 | test_word_supersession_blocks_old_current_admission_but_preserves_history | def test_word_supersession_blocks_old_current_admission_but_preserves_history(tmp_path, monkeypatch): |
| word | tests/test_native_u4b_a3_captures.py | 263 | test_admission_lease_excludes_word_renewal_during_reservation | def test_admission_lease_excludes_word_renewal_during_reservation(tmp_path, monkeypatch): |
| word | tests/test_native_u4b_a4_cross_word.py | 39 | test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch | def test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch(tmp_path, monkeypatch): |
| word | tests/test_native_u4b_a4_review.py | 57 | test_pinned_document_mutations_fail_even_with_rehashed_word | def test_pinned_document_mutations_fail_even_with_rehashed_word(evidence, field, value): |
| word | tests/test_native_u4b_addendum_authority.py | 79 | test_real_v2_reader_refuses_rehashed_bad_review_or_post_word_edit | def test_real_v2_reader_refuses_rehashed_bad_review_or_post_word_edit( |
| word | tests/test_native_u4b_capture_retries.py | 25 | test_three_captures_share_one_word_and_fourth_never_spawns | def test_three_captures_share_one_word_and_fourth_never_spawns(tmp_path, monkeypatch, mode): |
| word | tests/test_native_u4b_capture_retries.py | 71 | test_expired_capture_is_retained_while_same_word_recaptures | def test_expired_capture_is_retained_while_same_word_recaptures(tmp_path, monkeypatch): |
| word | tests/test_q19_rationale_lint.py | 378 | test_a_label_contrast_naming_nothing_is_about_the_words_before_it | def test_a_label_contrast_naming_nothing_is_about_the_words_before_it(label): |
| word | tests/test_q19_rationale_lint.py | 550 | test_a_cue_is_disclaimed_only_by_a_negation_within_three_words | def test_a_cue_is_disclaimed_only_by_a_negation_within_three_words(note, verdict, concerns): |
| word | tests/test_q19_rationale_lint.py | 569 | test_a_negation_within_three_words_always_disclaims | def test_a_negation_within_three_words_always_disclaims(): |
| word | tests/test_q19_rationale_lint.py | 685 | test_a_label_absence_clause_naming_one_kind_or_opening_with_its_word_is_read | def test_a_label_absence_clause_naming_one_kind_or_opening_with_its_word_is_read(): |
| word | tests/test_q19_rationale_lint.py | 865 | test_an_absence_word_list_the_acceptance_does_not_share_is_still_recovered | def test_an_absence_word_list_the_acceptance_does_not_share_is_still_recovered(): |
| word | tests/test_q19_rationale_lint.py | 1388 | test_an_absence_word_before_a_contrast_is_not_called_ambiguous_when_its_part_is_clear | def test_an_absence_word_before_a_contrast_is_not_called_ambiguous_when_its_part_is_clear(label): |
| word | tests/test_removals.py | 2689 | test_a_reworded_or_moved_value_is_counted_deleted_though_its_content_survives | def test_a_reworded_or_moved_value_is_counted_deleted_though_its_content_survives( |
| word | tests/test_review_receipts_v5_20261026.py | 120 | test_number_words_include_million | def test_number_words_include_million(): |
| word | tests/test_self_disclaimed.py | 89 | test_role_or_presence_wording_about_something_else_is_not_flagged | def test_role_or_presence_wording_about_something_else_is_not_flagged(container, text): |
| word | tests/test_self_disclaimed.py | 929 | test_a_qualifier_counts_only_within_the_declared_words_before_the_presence_term | def test_a_qualifier_counts_only_within_the_declared_words_before_the_presence_term(): |
| word | tests/test_status_context.py | 354 | test_a_counter_word_in_a_sentence_is_not_a_counter_heading | def test_a_counter_word_in_a_sentence_is_not_a_counter_heading(): |
| word | tests/test_status_context.py | 372 | test_a_counter_word_closes_a_scope_only_on_a_heading_like_line | def test_a_counter_word_closes_a_scope_only_on_a_heading_like_line(line, closes): |
| word | tests/test_status_context.py | 480 | test_a_one_word_colon_lead_in_governs_where_a_one_word_line_does_not | def test_a_one_word_colon_lead_in_governs_where_a_one_word_line_does_not(): |
| word | tests/test_status_context.py | 488 | test_a_one_word_status_line_is_a_table_cell_not_a_heading | def test_a_one_word_status_line_is_a_table_cell_not_a_heading(): |
| word | tests/test_status_context.py | 511 | test_a_one_word_counter_cell_does_not_close_a_status_headings_scope | def test_a_one_word_counter_cell_does_not_close_a_status_headings_scope(cell, layout): |
| word | tests/test_status_context.py | 523 | test_a_two_word_counter_heading_or_a_counter_lead_in_still_closes_the_scope | def test_a_two_word_counter_heading_or_a_counter_lead_in_still_closes_the_scope(cell): |
| word | tests/test_wave3_receipts_core.py | 164 | test_number_word_grammar_preserves_complete_counts | def test_number_word_grammar_preserves_complete_counts(value, words): |
| word | tests/test_wave3_receipts_core.py | 171 | test_unsupported_number_word_phrases_do_not_invent_counts | def test_unsupported_number_word_phrases_do_not_invent_counts(value, words): |
| account_choice | tests/test_native_generation_frontdoor.py | 137 | test_rehashed_account_choice_cannot_change_selected_intent | def test_rehashed_account_choice_cannot_change_selected_intent(saved_case, tmp_path, monkeypatch, field, value): |
| account_choice | tests/test_native_generation_frontdoor.py | 147 | test_missing_account_choice_field_refuses | def test_missing_account_choice_field_refuses(saved_case, tmp_path, monkeypatch): |
| statement | tests/test_attainability.py | 477 | test_a_statement_a_line_break_splits_is_not_an_absence | def test_a_statement_a_line_break_splits_is_not_an_absence(check, text, hit_lines): |
| statement | tests/test_attainability.py | 512 | test_a_statement_whose_hyphenated_breaks_need_different_readings_matches | def test_a_statement_whose_hyphenated_breaks_need_different_readings_matches(check, text): |
| statement | tests/test_generation_specificity_delegated.py | 116 | test_bc1_enabled_non_docstring_statements_are_refused | def test_bc1_enabled_non_docstring_statements_are_refused(tmp_path, mutation): |
| statement | tests/test_native_launch_review.py | 31 | test_two_reviews_and_exact_statement | def test_two_reviews_and_exact_statement(evidence): |
| statement | tests/test_self_disclaimed.py | 717 | test_a_subject_cue_counts_a_statement_self_or_presence_subject | def test_a_subject_cue_counts_a_statement_self_or_presence_subject(container, text, scope): |
| statement | tests/test_self_disclaimed.py | 868 | test_the_subject_scope_needs_a_statement_subject_block | def test_the_subject_scope_needs_a_statement_subject_block(): |
| statement | tests/test_wave3_a23_review.py | 80 | test_pediatric_free_speech_statement_keeps_the_release_qualification | def test_pediatric_free_speech_statement_keeps_the_release_qualification(): |
| statement | tests/test_wave4_5094_review.py | 163 | test_conflicting_counts_within_one_statement_are_not_overwritten | def test_conflicting_counts_within_one_statement_are_not_overwritten(counts): |
| runtime | tests/test_attainability.py | 687 | test_no_cborg_runtime_rubric10_record_is_credited_on_a_chorus_absence | def test_no_cborg_runtime_rubric10_record_is_credited_on_a_chorus_absence(): |
| runtime | tests/test_attainability.py | 712 | test_the_cborg_runtime_rubric20_chorus_records_are_reported_unchecked | def test_the_cborg_runtime_rubric20_chorus_records_are_reported_unchecked(): |
| runtime | tests/test_audit_evaluation_comparability.py | 43 | no_unmocked_runtime | def no_unmocked_runtime(monkeypatch): |
| runtime | tests/test_audit_evaluation_comparability.py | 734 | test_repeat_condition_groups_do_not_mix_legacy_blinded_adapter_or_runtime | def test_repeat_condition_groups_do_not_mix_legacy_blinded_adapter_or_runtime(registered_case): |
| runtime | tests/test_audit_recall_leak_rendered.py | 502 | test_an_observation_in_a_runtime_input_reaches_the_rendered_scan | def test_an_observation_in_a_runtime_input_reaches_the_rendered_scan(request, tmp_path, builder): |
| runtime | tests/test_claudecode_direct_arm.py | 368 | test_the_renderer_3_receipt_section_renders_for_both_claude_code_runtimes | def test_the_renderer_3_receipt_section_renders_for_both_claude_code_runtimes(external):  # noqa: F811 |
| runtime | tests/test_claudecode_direct_arm.py | 393 | test_backfill_spec_recovers_a_direct_runtime_record | def test_backfill_spec_recovers_a_direct_runtime_record(external, monkeypatch, version):  # noqa: F811 |
| runtime | tests/test_evaluation/test_semantic_comparison.py | 101 | test_unexposed_runtime_temperature_can_be_recorded_honestly | def test_unexposed_runtime_temperature_can_be_recorded_honestly(number, make): |
| runtime | tests/test_historical_digest.py | 188 | test_runtime_boundary_is_explicit | def test_runtime_boundary_is_explicit(monkeypatch): |
| runtime | tests/test_historical_digest_cache.py | 142 | test_warm_runtime_is_checked_again | def test_warm_runtime_is_checked_again(monkeypatch, missing): |
| runtime | tests/test_historical_eval_audit.py | 334 | test_checkout_runtime_locations_and_panel_size_are_not_one_rating_condition | def test_checkout_runtime_locations_and_panel_size_are_not_one_rating_condition(identity_plan): |
| runtime | tests/test_historical_profile_inventory_cache.py | 196 | test_runtime_view_method_replacement_is_fresh_with_identical_source_file | def test_runtime_view_method_replacement_is_fresh_with_identical_source_file(case, monkeypatch): |
| runtime | tests/test_historical_profile_inventory_cache.py | 237 | test_warm_inventory_does_not_attest_schema_or_runtime | def test_warm_inventory_does_not_attest_schema_or_runtime(case, monkeypatch, failure): |
| runtime | tests/test_native_attribution_controller.py | 408 | test_runtime_inadmissible_quoted_recording_identity_refuses_before_output | def test_runtime_inadmissible_quoted_recording_identity_refuses_before_output(case,tmp_path): |
| runtime | tests/test_native_execution.py | 188 | test_missing_runtime_choice_has_no_default | def test_missing_runtime_choice_has_no_default(case,key): |
| runtime | tests/test_native_execution.py | 196 | test_runtime_contract_rejects_ambiguous_or_unpinned_choices | def test_runtime_contract_rejects_ambiguous_or_unpinned_choices(case,change,tmp_path): |
| runtime | tests/test_native_execution.py | 457 | test_runtime_observation_capture_and_saved_consistency | def test_runtime_observation_capture_and_saved_consistency(case,monkeypatch,drift): |
| runtime | tests/test_native_execution_gates.py | 70 | test_runtime_gate_binds_exact_captured_observation | def test_runtime_gate_binds_exact_captured_observation(change): |
| runtime | tests/test_native_execution_gates.py | 93 | test_runtime_gate_rejects_selected_identity_contradictions_even_when_bytes_agree | def test_runtime_gate_rejects_selected_identity_contradictions_even_when_bytes_agree(change): |
| runtime | tests/test_native_execution_observation.py | 20 | test_runtime_probe_uses_exact_env_and_filters_secrets_without_calling_native | def test_runtime_probe_uses_exact_env_and_filters_secrets_without_calling_native(tmp_path,monkeypatch): |
| runtime | tests/test_native_execution_registration_v2.py | 410 | test_runtime_changed_after_preparer_verification_refuses_before_consumer | def test_runtime_changed_after_preparer_verification_refuses_before_consumer(prepared, monkeypatch): |
| runtime | tests/test_native_execution_round3_v2.py | 145 | test_dependency_runtime_import_is_source_loaded_or_v1_refused | def test_dependency_runtime_import_is_source_loaded_or_v1_refused(tmp_path, monkeypatch, target): |
| runtime | tests/test_native_execution_round5_v2.py | 69 | test_runtime_alias_refusal_and_source_only_loading | def test_runtime_alias_refusal_and_source_only_loading(): |
| runtime | tests/test_native_execution_round5_v2.py | 123 | test_runtime_dependency_enters_verified_set | def test_runtime_dependency_enters_verified_set(tmp_path, monkeypatch): |
| runtime | tests/test_native_execution_round6_v2.py | 15 | test_verify_preparer_uses_current_runtime_capture | def test_verify_preparer_uses_current_runtime_capture(inputs, monkeypatch, replace_contract): |
| runtime | tests/test_native_full_schema_profile_operations.py | 328 | test_collection_does_not_reopen_original_source_dependency_or_runtime_paths | def test_collection_does_not_reopen_original_source_dependency_or_runtime_paths(profile, collection_case, monkeypatch): |
| runtime | tests/test_native_full_schema_profile_runtime.py | 347 | test_completed_child_must_match_selected_report_and_runtime | def test_completed_child_must_match_selected_report_and_runtime(profile, parent_case, fault): |
| runtime | tests/test_native_full_schema_profile_runtime.py | 379 | test_preparation_cannot_cross_driver_runtime_or_recovered_source | def test_preparation_cannot_cross_driver_runtime_or_recovered_source(profile, parent_case, fault): |
| runtime | tests/test_native_model_aliases.py | 29 | runtime | def runtime(): |
| runtime | tests/test_native_permission_probe.py | 508 | test_owner_runtime_choice_refuses_conflicting_declarations | def test_owner_runtime_choice_refuses_conflicting_declarations(saved_case, monkeypatch, tmp_path, fault): |
| runtime | tests/test_native_shared_contract.py | 258 | test_whole_contract_is_python39_syntax_and_imports_no_repo_runtime | def test_whole_contract_is_python39_syntax_and_imports_no_repo_runtime(): |
| runtime | tests/test_native_shared_execution_failure.py | 185 | test_v2_saved_failure_rechecks_runtime_and_cleanup_after_successful_read | def test_v2_saved_failure_rechecks_runtime_and_cleanup_after_successful_read(execution_case, monkeypatch, filename): |
| runtime | tests/test_native_shared_gate_primitives.py | 124 | test_captured_runtime_observation_parity | def test_captured_runtime_observation_parity(change): |
| runtime | tests/test_native_shared_observations.py | 159 | test_tool_observation_requires_the_real_parent_runtime_before_join | def test_tool_observation_requires_the_real_parent_runtime_before_join(change): |
| runtime | tests/test_native_shared_permissions.py | 443 | test_expected_runtime_is_the_closed_typed_runtime_contract | def test_expected_runtime_is_the_closed_typed_runtime_contract(fixture,field,value): |
| runtime | tests/test_native_shared_record_contract.py | 26 | test_record_allows_exact_native_declaration_without_runtime_acceptance | def test_record_allows_exact_native_declaration_without_runtime_acceptance(): |
| runtime | tests/test_native_shared_render.py | 48 | test_native_instruction_roundtrip_uses_only_sole_runtime | def test_native_instruction_roundtrip_uses_only_sole_runtime(native_spec, monkeypatch): |
| runtime | tests/test_native_shared_render.py | 144 | test_no_runtime_or_draft_allowance_means_no_instruction | def test_no_runtime_or_draft_allowance_means_no_instruction(native_spec): |
| runtime | tests/test_native_shared_runtime_constants.py | 13 | _runtime | def _runtime(): |
| runtime | tests/test_native_shared_runtime_constants.py | 20 | test_neutral_runtime_constants_equal_frozen_v1_values | def test_neutral_runtime_constants_equal_frozen_v1_values(): |
| runtime | tests/test_native_shared_runtime_constants.py | 28 | test_render_runtime_uses_neutral_values_without_v1_import | def test_render_runtime_uses_neutral_values_without_v1_import(): |
| runtime | tests/test_native_shared_runtime_constants.py | 41 | test_neutral_extraction_keeps_render_runtime_refusals | def test_neutral_extraction_keeps_render_runtime_refusals(change): |
| runtime | tests/test_native_shared_runtime_values.py | 32 | runtime | def runtime(tmp_path): |
| runtime | tests/test_native_shared_runtime_values.py | 56 | test_neutral_runtime_constants_retain_types_values_and_argv_order | def test_neutral_runtime_constants_retain_types_values_and_argv_order(): |
| runtime | tests/test_native_shared_runtime_values.py | 82 | test_accepted_runtime_edges_preserve_legacy_value_and_json_copy | def test_accepted_runtime_edges_preserve_legacy_value_and_json_copy(runtime, change): |
| runtime | tests/test_native_shared_runtime_values.py | 105 | test_missing_runtime_choice_has_identical_refusal | def test_missing_runtime_choice_has_identical_refusal(runtime, key): |
| runtime | tests/test_native_shared_runtime_values.py | 155 | test_malformed_runtime_has_identical_refusal | def test_malformed_runtime_has_identical_refusal(runtime, path, replacement): |
| runtime | tests/test_native_subscription_guard_v2.py | 220 | test_rehashed_runtime_must_still_equal_the_owner_terms | def test_rehashed_runtime_must_still_equal_the_owner_terms(case, change): |
| runtime | tests/test_native_synthetic_profiles.py | 28 | runtime | def runtime(tmp_path): |
| runtime | tests/test_native_trace_comparison_adversarial.py | 330 | test_parent_rechecks_inputs_and_runtime_after_child_before_publication | def test_parent_rechecks_inputs_and_runtime_after_child_before_publication(driver, parent_case, monkeypatch, mutation): |
| runtime | tests/test_native_trace_profile_runtime.py | 89 | test_foreign_child_runtime_or_startup_identity_refuses_before_output | def test_foreign_child_runtime_or_startup_identity_refuses_before_output(profile, parent_case, monkeypatch, field): |
| runtime | tests/test_native_u1_scanner_contracts.py | 431 | test_model_nested_command_tables_preserve_approaches_without_runtime_argv_reseeding | def test_model_nested_command_tables_preserve_approaches_without_runtime_argv_reseeding(tmp_path, table): |
| runtime | tests/test_native_u3d_prompt_cli.py | 38 | test_v2_cli_conflicting_runtime_option_refuses_before_write | def test_v2_cli_conflicting_runtime_option_refuses_before_write(inputs, option): |
| runtime | tests/test_native_u3l_scanner.py | 204 | test_integrated_producer_cannot_borrow_legacy_runtime_validator | def test_integrated_producer_cannot_borrow_legacy_runtime_validator(route_root): |
| runtime | tests/test_native_u4b_a3_policy.py | 121 | test_guard_runtime_is_exactly_the_runtime_in_registration_bytes | def test_guard_runtime_is_exactly_the_runtime_in_registration_bytes(case): |
| runtime | tests/test_native_u4b_a4_producer.py | 104 | test_exact_u4b_basis_binds_once_after_runtime_and_before_first_instruction | def test_exact_u4b_basis_binds_once_after_runtime_and_before_first_instruction(basis): |
| runtime | tests/test_native_u4b_a5_producer_integration.py | 40 | select_runtime | def select_runtime(inputs, u4b): |
| runtime | tests/test_native_u4b_a5_producer_integration.py | 58 | test_prepare_captures_and_rechecks_runtime_with_current_source_owned_reader | def test_prepare_captures_and_rechecks_runtime_with_current_source_owned_reader(inputs): |
| runtime | tests/test_native_u4b_a5_producer_integration.py | 400 | test_default_producer_d76_binding_refuses_mutation_before_runtime_or_hook | def test_default_producer_d76_binding_refuses_mutation_before_runtime_or_hook(inputs, u4b): |
| runtime | tests/test_native_u4b_a5_scanner.py | 55 | test_d114_binding_before_runtime_is_not_an_allowed_alternative | def test_d114_binding_before_runtime_is_not_an_allowed_alternative(tmp_path, producer): |
| runtime | tests/test_native_u4b_admission.py | 78 | test_current_launch_refuses_historical_runtime_before_effects | def test_current_launch_refuses_historical_runtime_before_effects(monkeypatch): |
| runtime | tests/test_native_u4b_probe_sequence.py | 63 | test_final_runtime_cannot_change_other_provisional_fields | def test_final_runtime_cannot_change_other_provisional_fields(prepared, field): |
| runtime | tests/test_native_u4b_probe_sequence.py | 88 | test_runtime_cannot_use_bound_probe_as_its_own_observation | def test_runtime_cannot_use_bound_probe_as_its_own_observation(prepared, role): |
| runtime | tests/test_native_u4b_runtime.py | 26 | runtime_inputs | def runtime_inputs(tmp_path, *, binary_bytes=b'Inert fingerprint fixture; never execute.\n'): |
| runtime | tests/test_native_u4b_runtime.py | 108 | test_real_evidence_binding_preserves_closed_runtime_and_original | def test_real_evidence_binding_preserves_closed_runtime_and_original(inputs): |
| runtime | tests/test_receipt_completion_policy.py | 66 | test_selection_authority_and_runtime_identity | def test_selection_authority_and_runtime_identity(): |
| runtime | tests/test_receipt_completion_policy.py | 150 | test_runtime_ineligible_condition_cannot_certify_a_rehashed_policy | def test_runtime_ineligible_condition_cannot_certify_a_rehashed_policy(condition): |
| runtime | tests/test_receipt_completion_policy.py | 168 | test_runtime_receipt_conditions_remain_eligible | def test_runtime_receipt_conditions_remain_eligible(condition): |
| runtime | tests/test_receipt_completion_runtime.py | 654 | test_selected_runtime_uses_existing_exclusive_output_lock | def test_selected_runtime_uses_existing_exclusive_output_lock(selected): |
| runtime | tests/test_record_required_values.py | 50 | test_null_required_values_fail_both_export_and_runtime | def test_null_required_values_fail_both_export_and_runtime(mode, exported): |
| runtime | tests/test_record_required_values.py | 146 | test_cli_exports_the_same_contract_used_by_the_runtime | def test_cli_exports_the_same_contract_used_by_the_runtime(): |
| runtime | tests/test_reference_rescore.py | 221 | test_symlinked_temporary_root_grants_the_runtime_canonical_validator_path | def test_symlinked_temporary_root_grants_the_runtime_canonical_validator_path(environment, monkeypatch): |
| runtime | tests/test_reference_rescore.py | 541 | test_cli_attested_context_selector_preserves_reported_and_runtime_identity | def test_cli_attested_context_selector_preserves_reported_and_runtime_identity(environment): |
| runtime | tests/test_reference_rescore.py | 595 | test_model_alias_requires_matching_runtime_usage_evidence | def test_model_alias_requires_matching_runtime_usage_evidence(environment, defect): |
| runtime | tests/test_registered_eval_runner.py | 428 | test_dry_run_has_no_runtime_credential_or_output_side_effect | def test_dry_run_has_no_runtime_credential_or_output_side_effect(prepared, tmp_path): |
| runtime | tests/test_registered_eval_runner.py | 480 | test_unpinned_runtime_is_draft_only | def test_unpinned_runtime_is_draft_only(registration, tmp_path, field): |
| runtime | tests/test_registered_eval_runner.py | 568 | test_runtime_attestation_mutations_reject | def test_runtime_attestation_mutations_reject(prepared, mutation, match): |
| runtime | tests/test_registered_eval_runner.py | 715 | test_changed_runtime_refuses_before_delivery | def test_changed_runtime_refuses_before_delivery(registration, tmp_path): |
| runtime | tests/test_removal_repair.py | 100 | test_supported_review_needs_a_linked_finding_even_in_runtime_reading | def test_supported_review_needs_a_linked_finding_even_in_runtime_reading(): |
| runtime | tests/test_removal_repair.py | 130 | test_policy_refuses_unregistered_runtime_combinations | def test_policy_refuses_unregistered_runtime_combinations(external, renderer, runtime): |
| runtime | tests/test_removal_repair.py | 202 | test_runtime_accepts_actual_restoration_and_records_exact_work_order | def test_runtime_accepts_actual_restoration_and_records_exact_work_order(active): |
| runtime | tests/test_runtime_library_identity.py | 10 | test_checkout_local_runtime_keeps_third_party_identity | def test_checkout_local_runtime_keeps_third_party_identity(tmp_path, monkeypatch, relative): |
| runtime | tests/test_shared_generation_cli.py | 334 | test_a_shared_registration_names_its_own_method_without_the_runtime_default | def test_a_shared_registration_names_its_own_method_without_the_runtime_default(registered, monkeypatch): |
| runtime | tests/test_wave6_a14_a17_sizing.py | 7 | test_current_runtime_sizing_matches_every_typed_call | def test_current_runtime_sizing_matches_every_typed_call(tmp_path, monkeypatch): |
| runtime | tests/test_wave7_5213_d76_round4_inventory.py | 340 | test_a_guard_declaration_cannot_replace_the_runtime_refusal | def test_a_guard_declaration_cannot_replace_the_runtime_refusal(external, monkeypatch): |
| runtime | tests/utils/native_synthetic_evidence.py | 15 | runtime_for | def runtime_for(data, root): |
| capture | tests/test_attainability_aggregation.py | 119 | test_actual_capture_positive_private_returns_and_relocated_pure_recheck | def test_actual_capture_positive_private_returns_and_relocated_pure_recheck(tmp_path, monkeypatch): |
| capture | tests/test_attainability_aggregation.py | 499 | test_external_schema_references_refuse_in_actual_capture_and_pure_recheck | def test_external_schema_references_refuse_in_actual_capture_and_pure_recheck(tmp_path, monkeypatch, keyword, dialect): |
| capture | tests/test_attainability_aggregation.py | 537 | test_local_dynamic_anchor_and_real_local_fragment_capture_keep_validator_semantics | def test_local_dynamic_anchor_and_real_local_fragment_capture_keep_validator_semantics(tmp_path, monkeypatch): |
| capture | tests/test_attainability_figure.py | 188 | test_tampered_report_or_capture_cannot_supply_a_verdict | def test_tampered_report_or_capture_cannot_supply_a_verdict(tmp_path, mutation): |
| capture | tests/test_attainability_figure.py | 210 | test_captured_recheck_and_projection_with_original_paths_unavailable | def test_captured_recheck_and_projection_with_original_paths_unavailable(tmp_path, monkeypatch): |
| capture | tests/test_attainability_figure.py | 240 | test_absent_captured_inputs_and_ancestors_cannot_become_outputs | def test_absent_captured_inputs_and_ancestors_cannot_become_outputs(tmp_path, destination): |
| capture | tests/test_attainability_join_context.py | 44 | test_default_helpers_derivations_and_measurement_match_complete_parent_capture | def test_default_helpers_derivations_and_measurement_match_complete_parent_capture(): |
| capture | tests/test_audit_evaluation_comparability.py | 761 | test_declared_blinding_requires_both_captured_implementation_pins | def test_declared_blinding_requires_both_captured_implementation_pins(registered_case, module): |
| capture | tests/test_audit_evaluation_comparability.py | 836 | test_registered_capture_bounds_and_current_bytes | def test_registered_capture_bounds_and_current_bytes(registered_case, tmp_path, monkeypatch, fault): |
| capture | tests/test_audit_evaluation_comparability.py | 867 | test_registered_alias_retarget_refuses_without_mutating_captured_target | def test_registered_alias_retarget_refuses_without_mutating_captured_target( |
| capture | tests/test_audit_evaluation_comparability.py | 917 | test_registered_capture_rechecks_absolute_authority_alias_on_repeated_take | def test_registered_capture_rechecks_absolute_authority_alias_on_repeated_take(tmp_path): |
| capture | tests/test_audit_omissions.py | 175 | test_capture_is_independent_of_later_schema_edits | def test_capture_is_independent_of_later_schema_edits(inputs): |
| capture | tests/test_audit_typed_grammar.py | 22 | test_v1_outputs_equal_pre_edit_captured_baseline | def test_v1_outputs_equal_pre_edit_captured_baseline(baseline): |
| capture | tests/test_bc1_audit.py | 235 | test_neutral_policy_and_selection_are_captured_not_ambient | def test_neutral_policy_and_selection_are_captured_not_ambient(packet): |
| capture | tests/test_bc1_context.py | 238 | test_source_labels_with_spaces_in_captured_schema | def test_source_labels_with_spaces_in_captured_schema(fixture, annotation): |
| capture | tests/test_bc1_context.py | 259 | test_core_context_uses_captured_bytes_and_requires_core_root | def test_core_context_uses_captured_bytes_and_requires_core_root(fixture, tmp_path): |
| capture | tests/test_bc1_derivation_cache.py | 114 | test_exact_captured_inputs_invalidate_or_refuse | def test_exact_captured_inputs_invalidate_or_refuse(supplied, change): |
| capture | tests/test_d4d_to_synapse_table.py | 271 | test_sdk_pagination_keeps_all_captured_rows_for_deletion | def test_sdk_pagination_keeps_all_captured_rows_for_deletion(publication_files): |
| capture | tests/test_evaluation/test_cross_family_judge_analysis.py | 130 | test_actual_analysis_cli_complete_capture_relocates_without_originals | def test_actual_analysis_cli_complete_capture_relocates_without_originals(fixture, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_cross_family_judge_panel.py | 336 | test_reordering_and_returned_object_mutation_do_not_change_captured_identity | def test_reordering_and_returned_object_mutation_do_not_change_captured_identity(fixture, tmp_path): |
| capture | tests/test_evaluation/test_cross_family_judge_panel.py | 443 | test_registered_execution_cannot_downgrade_to_saved_capture | def test_registered_execution_cannot_downgrade_to_saved_capture(fixture, tmp_path): |
| capture | tests/test_evaluation/test_cross_family_judge_panel.py | 655 | test_execution_source_change_after_valid_capture_still_refuses_publication | def test_execution_source_change_after_valid_capture_still_refuses_publication(fixture, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_cross_family_judge_panel.py | 680 | test_required_execution_artifact_change_after_capture_refuses_publication | def test_required_execution_artifact_change_after_capture_refuses_publication(fixture, tmp_path, monkeypatch, artifact, change): |
| capture | tests/test_evaluation/test_cross_family_panel_adversarial.py | 135 | test_relocated_recheck_uses_captured_sources_only | def test_relocated_recheck_uses_captured_sources_only(case): |
| capture | tests/test_evaluation/test_cross_family_panel_adversarial.py | 170 | test_changed_captured_authority_refused_without_reopening_original | def test_changed_captured_authority_refused_without_reopening_original(case, artifact): |
| capture | tests/test_evaluation/test_cross_family_panel_adversarial.py | 227 | test_provenance_is_captured_unverified_and_does_not_infer_a_generator | def test_provenance_is_captured_unverified_and_does_not_infer_a_generator(case): |
| capture | tests/test_evaluation/test_cross_family_panel_analysis.py | 223 | test_percentages_come_from_exact_captured_maxima_not_accepted_rounded_payload | def test_percentages_come_from_exact_captured_maxima_not_accepted_rounded_payload(tmp_path, scale): |
| capture | tests/test_evaluation/test_cross_family_panel_analysis.py | 510 | test_real_captured_rubric_preserves_numeric_score_keys_and_runs_complete_analysis | def test_real_captured_rubric_preserves_numeric_score_keys_and_runs_complete_analysis(tmp_path): |
| capture | tests/test_evaluation/test_cross_family_panel_results.py | 113 | test_captured_schema_never_resolves_external_references | def test_captured_schema_never_resolves_external_references(monkeypatch, reference): |
| capture | tests/test_evaluation/test_cross_family_panel_results_adversarial.py | 237 | test_relocated_recheck_uses_only_captured_bytes | def test_relocated_recheck_uses_only_captured_bytes(case, monkeypatch): |
| capture | tests/test_evaluation/test_cross_family_panel_results_adversarial.py | 278 | test_changed_captured_bytes_refuse_without_running_captured_code | def test_changed_captured_bytes_refuse_without_running_captured_code(case, asset): |
| capture | tests/test_evaluation/test_cross_family_panel_results_adversarial.py | 357 | test_self_consistent_captured_foreign_validator_is_unsupported_and_never_executed | def test_self_consistent_captured_foreign_validator_is_unsupported_and_never_executed(case): |
| capture | tests/test_evaluation/test_fitness_execution.py | 83 | test_actual_fitness_cli_binding_and_relocated_captured_recheck | def test_actual_fitness_cli_binding_and_relocated_captured_recheck(make_fitness, fitness_peer, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_fitness_execution.py | 189 | test_captured_ledger_and_admission_cannot_switch_instruments | def test_captured_ledger_and_admission_cannot_switch_instruments(make_fitness): |
| capture | tests/test_evaluation/test_nested_support_execution.py | 232 | test_captured_ledger_relocates_and_rechecks_without_originals_or_network | def test_captured_ledger_relocates_and_rechecks_without_originals_or_network(make, peer, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_nested_support_results.py | 388 | test_existing_planner_requests_match_pre_edit_captures | def test_existing_planner_requests_match_pre_edit_captures(fixture): |
| capture | tests/test_evaluation/test_nested_support_results.py | 447 | test_default_model_selection_comes_only_from_captured_config | def test_default_model_selection_comes_only_from_captured_config(fixture, tmp_path, monkeypatch, model): |
| capture | tests/test_evaluation/test_nested_support_results.py | 468 | test_missing_captured_schema_import_cannot_resolve_from_ambient_package | def test_missing_captured_schema_import_cannot_resolve_from_ambient_package(plan, tmp_path): |
| capture | tests/test_evaluation/test_rubric10_model_disclosure.py | 286 | test_changed_rating_between_captures_refuses | def test_changed_rating_between_captures_refuses(sample, monkeypatch, change): |
| capture | tests/test_evaluation/test_rubric20_model_disclosure.py | 169 | test_changed_evaluation_between_captures_refuses | def test_changed_evaluation_between_captures_refuses(sample, monkeypatch, change): |
| capture | tests/test_evaluation/test_rubric_association_adversarial.py | 110 | test_roster_output_pin_is_reconciled_with_actual_planner_capture_and_portable_replay | def test_roster_output_pin_is_reconciled_with_actual_planner_capture_and_portable_replay( |
| capture | tests/test_evaluation/test_rubric_association_index.py | 75 | test_actual_cli_captured_only_relocation_without_rating_acceptance | def test_actual_cli_captured_only_relocation_without_rating_acceptance(fixture, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_rubric_association_index.py | 242 | test_v2_remains_unchanged_and_v3_can_include_captured_support_execution | def test_v2_remains_unchanged_and_v3_can_include_captured_support_execution(support_case, tmp_path): |
| capture | tests/test_evaluation/test_support_ancestor_context_pipeline.py | 150 | test_rehashed_context_artifacts_are_reconstructed_from_captured_record | def test_rehashed_context_artifacts_are_reconstructed_from_captured_record(context_case, tmp_path, change): |
| capture | tests/test_evaluation/test_support_ancestor_context_pipeline.py | 279 | test_scalar_legacy_bytes_match_genuine_precontext_capture | def test_scalar_legacy_bytes_match_genuine_precontext_capture(case_name, explicit): |
| capture | tests/test_evaluation/test_support_calibration.py | 137 | test_report_refuses_cached_execution_success_not_supported_by_captured_bytes | def test_report_refuses_cached_execution_success_not_supported_by_captured_bytes(controls): |
| capture | tests/test_evaluation/test_support_calibration_adversarial.py | 208 | test_changed_captured_raw_response_cannot_keep_a_cached_score | def test_changed_captured_raw_response_cannot_keep_a_cached_score(scenario): |
| capture | tests/test_evaluation/test_support_calibration_cli.py | 14 | test_cli_registers_missing_observations_then_captures_and_rechecks | def test_cli_registers_missing_observations_then_captures_and_rechecks(scenario): |
| capture | tests/test_evaluation/test_support_execution_index.py | 67 | test_cli_captures_both_axes_and_rechecks_after_originals_move | def test_cli_captures_both_axes_and_rechecks_after_originals_move(case, peer, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_support_execution_index_adversarial.py | 256 | test_rehashed_ledger_or_derived_claims_cannot_override_captured_dispatch | def test_rehashed_ledger_or_derived_claims_cannot_override_captured_dispatch(case, prepared, mutation): |
| capture | tests/test_evaluation/test_support_execution_index_adversarial.py | 293 | test_relocated_index_reads_only_its_captured_artifacts | def test_relocated_index_reads_only_its_captured_artifacts(case, prepared, tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_support_plan.py | 472 | test_old_roster_labels_captured_unpinned_provenance | def test_old_roster_labels_captured_unpinned_provenance(fixture): |
| capture | tests/test_evaluation/test_support_scalar_reference_pipeline.py | 198 | test_rehashed_plan_artifacts_cannot_replace_captured_semantics | def test_rehashed_plan_artifacts_cannot_replace_captured_semantics(scalar_plan, tmp_path, change): |
| capture | tests/test_evaluation/test_support_scalar_references.py | 219 | test_strict_bytes_match_actual_prechange_capture | def test_strict_bytes_match_actual_prechange_capture(case_name, explicit): |
| capture | tests/test_evaluation/test_support_targets.py | 327 | test_inherited_class_rules_are_blocked_from_captured_schema | def test_inherited_class_rules_are_blocked_from_captured_schema(schema_path, inheritance): |
| capture | tests/test_evaluation/test_support_targets.py | 385 | test_schema_and_request_identity_do_not_depend_on_prior_fitness_capture | def test_schema_and_request_identity_do_not_depend_on_prior_fitness_capture(schema_path): |
| capture | tests/test_evaluation/test_support_targets.py | 402 | test_independent_view_uses_captured_transitive_import_bytes_without_reopening | def test_independent_view_uses_captured_transitive_import_bytes_without_reopening(tmp_path, monkeypatch): |
| capture | tests/test_evaluation/test_top_level_fitness_results.py | 105 | test_missing_captured_request_is_not_regenerated_on_read | def test_missing_captured_request_is_not_regenerated_on_read(prepared, tmp_path): |
| capture | tests/test_evaluation/test_verifiable_recorded_basis.py | 97 | test_core_uses_its_own_captured_schema | def test_core_uses_its_own_captured_schema(tmp_path): |
| capture | tests/test_evaluation/test_verifiable_recorded_basis.py | 129 | test_schema_capture_survives_path_mutation | def test_schema_capture_survives_path_mutation(tmp_path): |
| capture | tests/test_evaluation/test_verifiable_recorded_basis.py | 189 | test_source_capture_is_used_for_hash_decode_and_measurement | def test_source_capture_is_used_for_hash_decode_and_measurement(tmp_path): |
| capture | tests/test_fitness_instrument_snapshot.py | 77 | test_change_between_context_and_prompt_uses_the_captured_instrument | def test_change_between_context_and_prompt_uses_the_captured_instrument(scorer, monkeypatch, part): |
| capture | tests/test_fitness_nested_vocabulary.py | 150 | test_deep_edit_during_call_uses_one_captured_schema | def test_deep_edit_during_call_uses_one_captured_schema(nested_schema, tmp_path, monkeypatch, calls): |
| capture | tests/test_fitness_schema.py | 41 | captured | def captured(schema, **kwargs): |
| capture | tests/test_fitness_schema.py | 93 | test_capture_is_immutable_and_prompt_does_not_recapture | def test_capture_is_immutable_and_prompt_does_not_recapture(schema, monkeypatch, tmp_path): |
| capture | tests/test_fitness_schema.py | 254 | test_profile_object_identity_agrees_without_rereading_captured_pin | def test_profile_object_identity_agrees_without_rereading_captured_pin(schema, tmp_path): |
| capture | tests/test_fitness_schema.py | 368 | test_subtype_cache_hit_still_checks_captured_profile_object | def test_subtype_cache_hit_still_checks_captured_profile_object(schema, monkeypatch, tmp_path): |
| capture | tests/test_form_instrument_snapshot.py | 140 | test_prompt_uses_the_same_capture_as_its_recorded_instrument | def test_prompt_uses_the_same_capture_as_its_recorded_instrument(instrument, monkeypatch): |
| capture | tests/test_g2_comparator.py | 22 | captures | def captures(tmp_path): |
| capture | tests/test_g2_comparator.py | 71 | test_named_captures_preserve_prior_evidence_and_bind_selected_registration | def test_named_captures_preserve_prior_evidence_and_bind_selected_registration(captures): |
| capture | tests/test_g2_comparator.py | 117 | test_captured_host_objects_are_rehashed | def test_captured_host_objects_are_rehashed(captures, damage, omission): |
| capture | tests/test_g2_round2.py | 300 | test_capture_refuses_registered_profile_pin_mismatch | def test_capture_refuses_registered_profile_pin_mismatch(registered, simulated_hooks, monkeypatch): |
| capture | tests/test_generality_profiles.py | 32 | test_identity_capture_preserves_the_record_date | def test_identity_capture_preserves_the_record_date(when, profile, basis): |
| capture | tests/test_generality_profiles.py | 46 | test_identity_capture_reports_an_undated_profile_refusal | def test_identity_capture_reports_an_undated_profile_refusal(): |
| capture | tests/test_historical_eval_pack.py | 177 | test_captured_authority_change_before_publication_refuses | def test_captured_authority_change_before_publication_refuses(historical_inputs, component, monkeypatch): |
| capture | tests/test_historical_profile_identity.py | 141 | test_record_schema_and_vocab_captured_once_and_view_released | def test_record_schema_and_vocab_captured_once_and_view_released(historical, monkeypatch): |
| capture | tests/test_model_disclosure.py | 169 | test_repeated_ratings_preserved_and_capture_once_under_change | def test_repeated_ratings_preserved_and_capture_once_under_change(bound,monkeypatch): |
| capture | tests/test_name_grounding_schema_scope.py | 208 | test_capture_hashes_and_slots_cannot_race_later_path_rewrite | def test_capture_hashes_and_slots_cannot_race_later_path_rewrite(disk, historical, monkeypatch): |
| capture | tests/test_native_attempt_supervisor.py | 186 | test_captured_receipts_refuse_same_real_wrapper_failures | def test_captured_receipts_refuse_same_real_wrapper_failures(completed, tmp_path, mutation): |
| capture | tests/test_native_attempt_supervisor.py | 219 | test_captured_receipts_equal_actual_current_canary | def test_captured_receipts_equal_actual_current_canary(completed): |
| capture | tests/test_native_attempt_supervisor.py | 232 | test_readback_binds_generated_report_and_captured_metadata | def test_readback_binds_generated_report_and_captured_metadata(completed, tmp_path, change): |
| capture | tests/test_native_attempt_supervisor.py | 417 | test_capture_from_another_consumed_attempt_cannot_complete | def test_capture_from_another_consumed_attempt_cannot_complete(case, completed, monkeypatch, binding): |
| capture | tests/test_native_attribution_results.py | 206 | test_raw_artifact_change_invalidates_trace_but_not_already_captured_bytes | def test_raw_artifact_change_invalidates_trace_but_not_already_captured_bytes(trace,tmp_path,role): |
| capture | tests/test_native_attribution_results.py | 336 | test_persisted_output_cannot_make_capture_read_arbitrary_config_files | def test_persisted_output_cannot_make_capture_read_arbitrary_config_files(trace,tmp_path,monkeypatch): |
| capture | tests/test_native_attribution_results.py | 354 | test_current_captured_file_policy_matches_frozen_structured_outcomes | def test_current_captured_file_policy_matches_frozen_structured_outcomes(trace,tmp_path): |
| capture | tests/test_native_attribution_results.py | 403 | test_persisted_output_validates_from_captured_bytes_with_legacy_parity | def test_persisted_output_validates_from_captured_bytes_with_legacy_parity(trace,tmp_path,monkeypatch): |
| capture | tests/test_native_ci_evidence.py | 30 | capture | def capture(tmp_path, output, **kwargs): |
| capture | tests/test_native_ci_evidence.py | 78 | test_output_collision_preserves_original_capture | def test_output_collision_preserves_original_capture(tmp_path): |
| capture | tests/test_native_ci_evidence.py | 146 | test_capture_bounds_are_explicit_failure_and_preserve_case | def test_capture_bounds_are_explicit_failure_and_preserve_case(tmp_path, monkeypatch, limit): |
| capture | tests/test_native_ci_evidence.py | 196 | test_distinct_worker_node_paths_and_capture_only_after_teardown | def test_distinct_worker_node_paths_and_capture_only_after_teardown(tmp_path, monkeypatch): |
| capture | tests/test_native_ci_evidence.py | 224 | test_capture_exception_cannot_replace_failed_test_or_pytest_exit | def test_capture_exception_cannot_replace_failed_test_or_pytest_exit(tmp_path, monkeypatch): |
| capture | tests/test_native_ci_evidence_adversarial.py | 87 | test_other_node_never_captures_even_with_matching_case_directory | def test_other_node_never_captures_even_with_matching_case_directory(tmp_path, monkeypatch): |
| capture | tests/test_native_execution.py | 457 | test_runtime_observation_capture_and_saved_consistency | def test_runtime_observation_capture_and_saved_consistency(case,monkeypatch,drift): |
| capture | tests/test_native_execution.py | 505 | test_cleanup_capture_and_saved_consistency | def test_cleanup_capture_and_saved_consistency(case,monkeypatch,drift): |
| capture | tests/test_native_execution_gates.py | 70 | test_runtime_gate_binds_exact_captured_observation | def test_runtime_gate_binds_exact_captured_observation(change): |
| capture | tests/test_native_execution_registration_v2.py | 189 | test_bad_authority_envelope_refuses_before_input_capture | def test_bad_authority_envelope_refuses_before_input_capture(isolated_modules, monkeypatch, mutation): |
| capture | tests/test_native_execution_registration_v2.py | 550 | test_approval_parser_captures_exact_fabricated_bytes_without_writes | def test_approval_parser_captures_exact_fabricated_bytes_without_writes(fabricated_authorizations): |
| capture | tests/test_native_execution_round6_v2.py | 15 | test_verify_preparer_uses_current_runtime_capture | def test_verify_preparer_uses_current_runtime_capture(inputs, monkeypatch, replace_contract): |
| capture | tests/test_native_execution_verified_loader_v2.py | 101 | test_source_context_uses_captured_bytes_not_later_file_or_preloaded_module | def test_source_context_uses_captured_bytes_not_later_file_or_preloaded_module(tmp_path): |
| capture | tests/test_native_incomplete_evidence.py | 14 | captured | def captured(tmp_path, monkeypatch): |
| capture | tests/test_native_incomplete_evidence.py | 52 | test_actual_incomplete_capture_reports_unavailable_without_losing_other_gates | def test_actual_incomplete_capture_reports_unavailable_without_losing_other_gates(captured, consumer, monkeypatch): |
| capture | tests/test_native_launch_review.py | 82 | test_only_exactly_registered_capture | def test_only_exactly_registered_capture(evidence, key, value): |
| capture | tests/test_native_launch_review.py | 110 | test_legacy_capture_terms_are_readable_but_not_silently_upgraded | def test_legacy_capture_terms_are_readable_but_not_silently_upgraded(evidence): |
| capture | tests/test_native_launch_schema_metadata.py | 233 | test_changed_imported_capture_alias_disables_local_reuse | def test_changed_imported_capture_alias_disables_local_reuse(declaration, monkeypatch): |
| capture | tests/test_native_permission_probe.py | 376 | test_shared_producer_actual_capture_paths_with_mocked_native_events | def test_shared_producer_actual_capture_paths_with_mocked_native_events(saved_case, tmp_path, monkeypatch): |
| capture | tests/test_native_permission_probe.py | 533 | test_capture_requires_main_thread_before_loading | def test_capture_requires_main_thread_before_loading(saved_case, monkeypatch): |
| capture | tests/test_native_receipt_origin_reporting.py | 91 | _captured | def _captured(root, family='neutral_supervisor', mutate_run=None): |
| capture | tests/test_native_receipt_origin_reporting.py | 173 | test_incomplete_or_inconsistent_capture_is_unknown_without_counts | def test_incomplete_or_inconsistent_capture_is_unknown_without_counts(tmp_path, damage): |
| capture | tests/test_native_receipt_origin_reporting.py | 216 | test_recorded_alias_with_different_basename_uses_captured_physical_bytes | def test_recorded_alias_with_different_basename_uses_captured_physical_bytes(tmp_path): |
| capture | tests/test_native_receipt_origin_reporting.py | 233 | test_failed_attempt_without_any_capture_has_reconstructible_unknown | def test_failed_attempt_without_any_capture_has_reconstructible_unknown(tmp_path): |
| capture | tests/test_native_receipt_origin_reporting.py | 247 | test_unsealed_or_malformed_capture_never_produces_counts | def test_unsealed_or_malformed_capture_never_produces_counts(tmp_path, monkeypatch, seal): |
| capture | tests/test_native_receipt_origin_reporting.py | 402 | test_saved_capture_drift_is_refused_before_classification | def test_saved_capture_drift_is_refused_before_classification(completed_origin_case, tmp_path, damage): |
| capture | tests/test_native_receipt_unopened.py | 34 | test_native_gate_passes_both_captured_receipt_and_manifest | def test_native_gate_passes_both_captured_receipt_and_manifest(): |
| capture | tests/test_native_schema_metadata_reuse.py | 406 | test_actual_full_core_sources_match_parent_and_remain_captured_only | def test_actual_full_core_sources_match_parent_and_remain_captured_only(parent, monkeypatch): |
| capture | tests/test_native_shared_attribution.py | 143 | test_live_uses_captured_sources_and_only_bounded_current_output_reads | def test_live_uses_captured_sources_and_only_bounded_current_output_reads(case, monkeypatch): |
| capture | tests/test_native_shared_attribution.py | 181 | test_saved_replay_uses_captured_bytes_and_defers_superseded_passes | def test_saved_replay_uses_captured_bytes_and_defers_superseded_passes(case, monkeypatch): |
| capture | tests/test_native_shared_attribution.py | 244 | test_mismatched_captured_selection_execution_or_policy_refuses | def test_mismatched_captured_selection_execution_or_policy_refuses(case, mutation): |
| capture | tests/test_native_shared_attribution.py | 310 | test_saved_rehashed_preparation_still_binds_captured_authority | def test_saved_rehashed_preparation_still_binds_captured_authority(case, monkeypatch, change): |
| capture | tests/test_native_shared_callback_preloading.py | 48 | test_source_loaded_capture_worker_refuses_unminted_interface_without_loading | def test_source_loaded_capture_worker_refuses_unminted_interface_without_loading(isolated_modules): |
| capture | tests/test_native_shared_callback_preloading.py | 110 | test_worker_late_package_import_is_refused_by_capture_guard | def test_worker_late_package_import_is_refused_by_capture_guard(isolated_modules): |
| capture | tests/test_native_shared_callback_preloading.py | 141 | test_captured_input_pin_is_rechecked_before_reconstruction | def test_captured_input_pin_is_rechecked_before_reconstruction(tmp_path): |
| capture | tests/test_native_shared_callback_preloading.py | 225 | test_worker_load_refused_before_dependency_or_capture_effects | def test_worker_load_refused_before_dependency_or_capture_effects(kind, operation, monkeypatch, isolated_modules): |
| capture | tests/test_native_shared_capture_split.py | 14 | test_live_capture_forwards_projection_and_refuses_before_effects | def test_live_capture_forwards_projection_and_refuses_before_effects(monkeypatch, entry): |
| capture | tests/test_native_shared_contract.py | 68 | test_capture_accessors_are_offline_and_retain_exact_raw_bytes | def test_capture_accessors_are_offline_and_retain_exact_raw_bytes(monkeypatch): |
| capture | tests/test_native_shared_contract.py | 186 | test_mutable_or_mismatched_artifact_bytes_cannot_be_captured | def test_mutable_or_mismatched_artifact_bytes_cannot_be_captured(): |
| capture | tests/test_native_shared_contract.py | 250 | test_schema_capture_keeps_complete_unique_import_roles | def test_schema_capture_keeps_complete_unique_import_roles(): |
| capture | tests/test_native_shared_controller.py | 201 | test_captured_parsers_are_pure_and_do_not_grant_verification | def test_captured_parsers_are_pure_and_do_not_grant_verification(bound, monkeypatch): |
| capture | tests/test_native_shared_controller.py | 218 | test_captured_execution_parser_refuses_foreign_wire | def test_captured_execution_parser_refuses_foreign_wire(change): |
| capture | tests/test_native_shared_controller.py | 235 | test_captured_execution_allows_only_named_optional_origin_field_without_io | def test_captured_execution_allows_only_named_optional_origin_field_without_io(monkeypatch): |
| capture | tests/test_native_shared_controller.py | 369 | test_verified_handoff_refuses_changed_capture_and_restores_spec | def test_verified_handoff_refuses_changed_capture_and_restores_spec(bound, monkeypatch, failure): |
| capture | tests/test_native_shared_controller.py | 423 | test_neutral_captured_wire_vocabulary_equals_unchanged_a_contract | def test_neutral_captured_wire_vocabulary_equals_unchanged_a_contract(): |
| capture | tests/test_native_shared_current.py | 21 | test_expanded_final_and_same_captured_only_bytes | def test_expanded_final_and_same_captured_only_bytes(tmp_path, monkeypatch, role, key): |
| capture | tests/test_native_shared_evidence.py | 80 | test_regular_file_capture_and_exact_bound | def test_regular_file_capture_and_exact_bound(tmp_path): |
| capture | tests/test_native_shared_evidence.py | 91 | test_nonregular_or_multiple_link_capture_refuses_without_mutation | def test_nonregular_or_multiple_link_capture_refuses_without_mutation(tmp_path,alias): |
| capture | tests/test_native_shared_gate_primitives.py | 124 | test_captured_runtime_observation_parity | def test_captured_runtime_observation_parity(change): |
| capture | tests/test_native_shared_gate_primitives.py | 158 | test_cleanup_gate_preserves_policy_and_captured_byte_obligations | def test_cleanup_gate_preserves_policy_and_captured_byte_obligations(policy, change): |
| capture | tests/test_native_shared_gates.py | 77 | captured_run | def captured_run(declaration, inputs, tmp_path, request): |
| capture | tests/test_native_shared_gates.py | 229 | test_all_fifteen_gates_remain_present_on_incomplete_capture | def test_all_fifteen_gates_remain_present_on_incomplete_capture(pure_gate_members): |
| capture | tests/test_native_shared_initial_receipts.py | 19 | test_initial_success_uses_only_captured_authority_and_has_no_final_claim | def test_initial_success_uses_only_captured_authority_and_has_no_final_claim(case, monkeypatch): |
| capture | tests/test_native_shared_live_capture.py | 57 | stream_capture | def stream_capture(value): |
| capture | tests/test_native_shared_permissions.py | 540 | test_recipe_source_capture_preserves_raw_newline_bytes | def test_recipe_source_capture_preserves_raw_newline_bytes(monkeypatch): |
| capture | tests/test_native_shared_render.py | 90 | test_native_captured_restore_does_not_discover_or_normalize_paths | def test_native_captured_restore_does_not_discover_or_normalize_paths(native_spec, monkeypatch): |
| capture | tests/test_native_shared_render.py | 100 | test_native_captured_inputs_refuse_relative_paths_without_ambient_lookup | def test_native_captured_inputs_refuse_relative_paths_without_ambient_lookup(native_spec, monkeypatch, field): |
| capture | tests/test_native_shared_results.py | 29 | test_saved_initial_capture_rebuild_has_no_filesystem_fallback | def test_saved_initial_capture_rebuild_has_no_filesystem_fallback(started, monkeypatch): |
| capture | tests/test_native_shared_results.py | 66 | test_saved_snapshot_never_reads_uncaptured_target | def test_saved_snapshot_never_reads_uncaptured_target(tmp_path, monkeypatch): |
| capture | tests/test_native_shared_saved_advance.py | 83 | captured_run | def captured_run(advance, change=None, *, saved=True): |
| capture | tests/test_native_shared_schema_derivation_once.py | 38 | test_live_and_saved_capture_each_build_two_real_views | def test_live_and_saved_capture_each_build_two_real_views(declaration, monkeypatch): |
| capture | tests/test_native_shared_schema_derivation_once.py | 109 | test_live_capture_still_rereads_authority_after_a_success | def test_live_capture_still_rereads_authority_after_a_success(declaration, tmp_path): |
| capture | tests/test_native_shared_schema_gates.py | 17 | captured | def captured(declaration): |
| capture | tests/test_native_shared_schema_gates.py | 61 | test_real_schema_and_pair_use_captured_imports_after_live_files_change | def test_real_schema_and_pair_use_captured_imports_after_live_files_change(captured, monkeypatch): |
| capture | tests/test_native_shared_schema_gates.py | 112 | test_incomplete_captured_import_cannot_fall_back_to_live_file | def test_incomplete_captured_import_cannot_fall_back_to_live_file(captured, reader): |
| capture | tests/test_native_shared_selection.py | 81 | test_actual_capture_and_pure_rebuild_retain_every_original_byte | def test_actual_capture_and_pure_rebuild_retain_every_original_byte(declaration, monkeypatch): |
| capture | tests/test_native_shared_selection.py | 267 | test_whole_capture_refuses_changes_after_a_file_was_read | def test_whole_capture_refuses_changes_after_a_file_was_read(declaration, monkeypatch): |
| capture | tests/test_native_shared_selection.py | 285 | test_actual_registered_schema_imports_are_captured_not_discovered_later | def test_actual_registered_schema_imports_are_captured_not_discovered_later(declaration): |
| capture | tests/test_native_shared_stages.py | 113 | captured | def captured(item): |
| capture | tests/test_native_shared_stages.py | 334 | test_native_policy_requires_exact_descriptor_role_not_any_captured_asset | def test_native_policy_requires_exact_descriptor_role_not_any_captured_asset(case): |
| capture | tests/test_native_shared_streams.py | 120 | test_identical_byte_replacement_between_captures_is_not_the_same_stream | def test_identical_byte_replacement_between_captures_is_not_the_same_stream(tmp_path): |
| capture | tests/test_native_shared_streams.py | 241 | test_complete_report_run_remains_strict_and_live_recapture_rechecks_prefixes | def test_complete_report_run_remains_strict_and_live_recapture_rechecks_prefixes(tmp_path, monkeypatch): |
| capture | tests/test_native_source_attribution.py | 382 | test_registration_will_not_add_itself_to_the_captured_checker_tree | def test_registration_will_not_add_itself_to_the_captured_checker_tree(case): |
| capture | tests/test_native_subscription_capture.py | 124 | test_one_fake_capture_persists_exact_observation_and_refuses_reuse | def test_one_fake_capture_persists_exact_observation_and_refuses_reuse(tmp_path, monkeypatch): |
| capture | tests/test_native_subscription_capture.py | 170 | test_failed_fake_capture_retains_claim_streams_and_cannot_retry | def test_failed_fake_capture_retains_claim_streams_and_cannot_retry(tmp_path, monkeypatch, mode, error): |
| capture | tests/test_native_subscription_capture.py | 227 | test_saved_capture_reconstructs_and_refuses_changed_evidence | def test_saved_capture_reconstructs_and_refuses_changed_evidence(tmp_path, monkeypatch, change): |
| capture | tests/test_native_subscription_capture.py | 269 | test_registration_reconstruction_refusal_prevents_capture | def test_registration_reconstruction_refusal_prevents_capture(tmp_path, monkeypatch): |
| capture | tests/test_native_subscription_capture.py | 280 | test_read_capture_for_event_rechecks_authority_after_slot_scan_without_repeating_full_verified | def test_read_capture_for_event_rechecks_authority_after_slot_scan_without_repeating_full_verified( |
| capture | tests/test_native_subscription_capture.py | 322 | test_read_capture_for_event_refuses_mutations_between_outer_authority_and_inner_slot_recheck | def test_read_capture_for_event_refuses_mutations_between_outer_authority_and_inner_slot_recheck( |
| capture | tests/test_native_subscription_capture.py | 375 | test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root | def test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root( |
| capture | tests/test_native_subscription_guard_v2.py | 147 | test_word_capture_and_actual_dispatch_chronology | def test_word_capture_and_actual_dispatch_chronology(case, captured_delta, dispatch_delta, passes): |
| capture | tests/test_native_subscription_guard_v2.py | 167 | test_each_window_reset_must_follow_capture_and_actual_dispatch | def test_each_window_reset_must_follow_capture_and_actual_dispatch(case, window, reset_delta, dispatch_delta): |
| capture | tests/test_native_synthetic_evidence.py | 15 | test_capture_chronology_does_not_borrow_an_older_word_time | def test_capture_chronology_does_not_borrow_an_older_word_time(tmp_path, monkeypatch): |
| capture | tests/test_native_synthetic_profiles.py | 283 | test_real_capture_refuses_before_authority_or_reservation | def test_real_capture_refuses_before_authority_or_reservation(runtime, tmp_path, monkeypatch): |
| capture | tests/test_native_trace_comparison.py | 212 | test_current_advance_uses_exact_captured_pending_command_and_retains_wrong_command_graph | def test_current_advance_uses_exact_captured_pending_command_and_retains_wrong_command_graph(tools, monkeypatch): |
| capture | tests/test_native_trace_comparison_adversarial.py | 157 | test_equal_rehashed_states_cannot_substitute_a_different_captured_input | def test_equal_rehashed_states_cannot_substitute_a_different_captured_input(driver, mutation): |
| capture | tests/test_native_trace_comparison_adversarial.py | 428 | test_stream_capture_itself_keeps_the_original_wall_deadline | def test_stream_capture_itself_keeps_the_original_wall_deadline(driver, monkeypatch): |
| capture | tests/test_native_u3b_reuse.py | 53 | captured | def captured(declaration): |
| capture | tests/test_native_u3b_reuse.py | 429 | test_native_typed_capture_and_receipt_reconstruction_smoke | def test_native_typed_capture_and_receipt_reconstruction_smoke(supplied, declaration, tmp_path): |
| capture | tests/test_native_u3k_freshness_order.py | 53 | test_static_inspection_does_not_make_expired_capture_fresh | def test_static_inspection_does_not_make_expired_capture_fresh(tmp_path, monkeypatch): |
| capture | tests/test_native_u3k_freshness_order.py | 148 | test_frontdoor_defers_capture_without_loading_a_guard | def test_frontdoor_defers_capture_without_loading_a_guard(tmp_path, monkeypatch): |
| capture | tests/test_native_u3k_freshness_order.py | 181 | test_frontdoor_refuses_expired_or_spent_capture_before_engine_without_loading_guard | def test_frontdoor_refuses_expired_or_spent_capture_before_engine_without_loading_guard( |
| capture | tests/test_native_u4b_a3_captures.py | 31 | test_capture_saves_terminal_model_usage_and_rechecks_saved_bytes | def test_capture_saves_terminal_model_usage_and_rechecks_saved_bytes(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a3_captures.py | 194 | test_new_word_restores_three_capture_slots_without_consuming_attempt | def test_new_word_restores_three_capture_slots_without_consuming_attempt(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a3_captures.py | 251 | test_generation_reservation_prevents_renewal_and_capture | def test_generation_reservation_prevents_renewal_and_capture(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a3_policy.py | 169 | test_new_capture_state_directory_is_registered_not_owner_selected | def test_new_capture_state_directory_is_registered_not_owner_selected(case): |
| capture | tests/test_native_u4b_a3_policy.py | 176 | test_prior_capture_request_version_is_preserved_for_readback | def test_prior_capture_request_version_is_preserved_for_readback(case): |
| capture | tests/test_native_u4b_a3_reservation.py | 363 | test_source_recapture_time_is_charged_before_measuring_reservation_margin | def test_source_recapture_time_is_charged_before_measuring_reservation_margin( |
| capture | tests/test_native_u4b_a3_reservation.py | 403 | test_deferred_capture_acceptance_exact_order_to_real_reservation | def test_deferred_capture_acceptance_exact_order_to_real_reservation(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a3_reservation.py | 433 | test_deferred_capture_late_load_refuses_admission_mutation | def test_deferred_capture_late_load_refuses_admission_mutation(tmp_path, monkeypatch, change, reason): |
| capture | tests/test_native_u4b_a4_cross_word.py | 22 | test_capture_process_trap_leaves_real_review_git_reads_intact | def test_capture_process_trap_leaves_real_review_git_reads_intact(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a4_paths.py | 141 | test_capture_alias_overlap_refuses_with_authority_prerequisites_isolated | def test_capture_alias_overlap_refuses_with_authority_prerequisites_isolated(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_a4_review.py | 192 | test_capture_cannot_alias_attempt_directory_case | def test_capture_cannot_alias_attempt_directory_case(evidence): |
| capture | tests/test_native_u4b_a5_producer_integration.py | 58 | test_prepare_captures_and_rechecks_runtime_with_current_source_owned_reader | def test_prepare_captures_and_rechecks_runtime_with_current_source_owned_reader(inputs): |
| capture | tests/test_native_u4b_addendum_authority.py | 107 | test_expired_capture_stays_spent_and_refuses_before_generation_reservation | def test_expired_capture_stays_spent_and_refuses_before_generation_reservation(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_admission.py | 36 | test_actual_capture_owner_guard_join_and_saved_replay | def test_actual_capture_owner_guard_join_and_saved_replay(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_admission.py | 58 | test_rehashed_guard_cannot_substitute_owner_or_capture | def test_rehashed_guard_cannot_substitute_owner_or_capture(tmp_path, monkeypatch, mutation): |
| capture | tests/test_native_u4b_admission.py | 86 | test_frontdoor_registers_explicit_capture_and_offline_guard_commands | def test_frontdoor_registers_explicit_capture_and_offline_guard_commands(): |
| capture | tests/test_native_u4b_audit_counts.py | 34 | _captured | def _captured(prepared, items): |
| capture | tests/test_native_u4b_audit_counts.py | 72 | test_actual_derived_audit_and_captured_report_emit_equality | def test_actual_derived_audit_and_captured_report_emit_equality(prepared_counts, monkeypatch): |
| capture | tests/test_native_u4b_capture_retries.py | 25 | test_three_captures_share_one_word_and_fourth_never_spawns | def test_three_captures_share_one_word_and_fourth_never_spawns(tmp_path, monkeypatch, mode): |
| capture | tests/test_native_u4b_capture_retries.py | 71 | test_expired_capture_is_retained_while_same_word_recaptures | def test_expired_capture_is_retained_while_same_word_recaptures(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_capture_retries.py | 94 | test_interrupted_claim_consumes_slot_without_inventing_completed_capture | def test_interrupted_claim_consumes_slot_without_inventing_completed_capture(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_capture_retries.py | 117 | test_concurrent_capture_refuses_without_allocating_another_slot | def test_concurrent_capture_refuses_without_allocating_another_slot(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_capture_retries.py | 160 | test_unknown_guard_event_cannot_select_an_arbitrary_retained_capture | def test_unknown_guard_event_cannot_select_an_arbitrary_retained_capture(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_capture_retries.py | 171 | test_legacy_request_cannot_authorize_a_new_capture | def test_legacy_request_cannot_authorize_a_new_capture(tmp_path, monkeypatch): |
| capture | tests/test_native_u4b_probe_sequence.py | 334 | test_real_http_handler_captures_raw_body_and_no_tool_response_in_memory | def test_real_http_handler_captures_raw_body_and_no_tool_response_in_memory(tmp_path): |
| capture | tests/test_native_u4b_readback.py | 190 | test_transcript_absence_never_opens_an_uncaptured_file | def test_transcript_absence_never_opens_an_uncaptured_file(tmp_path, monkeypatch, complete): |
| capture | tests/test_native_u4b_readback.py | 213 | test_empty_captured_transcript_remains_bytes_not_absence | def test_empty_captured_transcript_remains_bytes_not_absence(tmp_path): |
| capture | tests/test_native_u4b_windows_v2.py | 85 | test_reset_must_follow_both_capture_and_dispatch_in_every_route | def test_reset_must_follow_both_capture_and_dispatch_in_every_route(case, window, reset_offset): |
| capture | tests/test_native_u5_external_schema.py | 39 | test_external_320_capture_rebuild_and_cold_warm_catalog | def test_external_320_capture_rebuild_and_cold_warm_catalog(declaration, monkeypatch, tmp_path, shape): |
| capture | tests/test_native_wp1_capture_recheck.py | 146 | test_contract_binds_capture_test_bytes | def test_contract_binds_capture_test_bytes(adapter, monkeypatch, tmp_path, mutation): |
| capture | tests/test_pair_cli_historical_core.py | 202 | test_recovery_and_digest_use_one_captured_provenance | def test_recovery_and_digest_use_one_captured_provenance(selected, monkeypatch): |
| capture | tests/test_pair_cli_recorded_digest.py | 116 | test_comparison_and_ledger_receive_the_same_captured_provenance | def test_comparison_and_ledger_receive_the_same_captured_provenance(tmp_path,known_digest,monkeypatch): |
| capture | tests/test_receipt_origin_captured.py | 96 | test_captured_unknowns_retain_existing_diagnostics_and_do_not_classify | def test_captured_unknowns_retain_existing_diagnostics_and_do_not_classify(tmp_path, mutation): |
| capture | tests/test_receipt_origin_captured.py | 165 | test_captured_route_is_independent_of_filesystem_cwd_process_and_network | def test_captured_route_is_independent_of_filesystem_cwd_process_and_network(tmp_path, monkeypatch): |
| capture | tests/test_receipt_origin_captured.py | 188 | test_captured_input_contract_rejects_mutable_or_ambient_identity | def test_captured_input_contract_rejects_mutable_or_ambient_identity(tmp_path, field, value): |
| capture | tests/test_receipt_readdress_input_snapshots.py | 26 | test_same_receipt_full_path_preserves_each_captured_snapshot | def test_same_receipt_full_path_preserves_each_captured_snapshot(tmp_path, monkeypatch, |
| capture | tests/test_record_required_values.py | 117 | test_annotation_and_compilation_use_the_same_captured_bytes | def test_annotation_and_compilation_use_the_same_captured_bytes(tmp_path, monkeypatch): |
| capture | tests/test_registered_eval_runner.py | 322 | test_blinding_implementation_is_captured_before_gate_and_rechecked_during_prepare | def test_blinding_implementation_is_captured_before_gate_and_rechecked_during_prepare(registration, monkeypatch, module): |
| capture | tests/test_related_dataset_diagnostics.py | 80 | test_legacy_defaults_and_explicit_cli_policy_match_captured_baseline | def test_legacy_defaults_and_explicit_cli_policy_match_captured_baseline(tmp_path): |
| capture | tests/test_related_dataset_diagnostics.py | 217 | test_capture_does_not_reopen_schema_or_current_vocabulary | def test_capture_does_not_reopen_schema_or_current_vocabulary(inputs): |
| capture | tests/test_removals_identifier_basis.py | 271 | test_current_capture_disagreement_cannot_certify_a_historical_join | def test_current_capture_disagreement_cannot_certify_a_historical_join(tmp_path, monkeypatch): |
| capture | tests/test_removals_person_schema.py | 160 | test_independent_selector_drift_is_not_reported_as_one_shared_capture | def test_independent_selector_drift_is_not_reported_as_one_shared_capture(tmp_path): |
| capture | tests/test_renderer_contract_captures.py | 99 | captures | def captures(root: Path) -> dict: |
| capture | tests/test_renderer_contract_captures.py | 381 | test_every_accepted_renderer_is_captured | def test_every_accepted_renderer_is_captured(tmp_path): |
| capture | tests/test_renderer_contract_captures.py | 409 | test_captures_match_the_rendered_bytes | def test_captures_match_the_rendered_bytes(tmp_path, stable): |
| capture | tests/test_renderer_contract_captures.py | 413 | test_assembly_captures_agree_with_the_existing_historical_pins | def test_assembly_captures_agree_with_the_existing_historical_pins(): |
| capture | tests/test_renderer_contract_captures.py | 427 | test_receipt_instruction_mutation_moves_new_captures_without_rewriting_history | def test_receipt_instruction_mutation_moves_new_captures_without_rewriting_history(tmp_path, stable, monkeypatch): |
| capture | tests/test_review_pack_identifier_basis.py | 300 | test_current_capture_disagreement_is_a_named_cli_refusal | def test_current_capture_disagreement_is_a_named_cli_refusal(tmp_path, monkeypatch): |
| capture | tests/test_schema_event_replay.py | 136 | test_real_schema_catalog_and_typed_capture_equal_original | def test_real_schema_catalog_and_typed_capture_equal_original(supplied, monkeypatch): |
| capture | tests/test_schema_semantics.py | 573 | test_imported_namespace_binding_is_captured_and_frozen | def test_imported_namespace_binding_is_captured_and_frozen(schema): |
| capture | tests/test_schema_snapshot_compatibility.py | 96 | test_namespace_initialization_order_selects_the_same_captured_file | def test_namespace_initialization_order_selects_the_same_captured_file(tmp_path, early): |
| capture | tests/test_schema_snapshot_compatibility.py | 147 | test_flow_yaml_without_final_newline_is_parsed_as_captured_content | def test_flow_yaml_without_final_newline_is_parsed_as_captured_content(tmp_path, location): |
| capture | tests/test_semantic_taxonomy_figure.py | 225 | test_changed_captured_bytes_refuse_before_publication | def test_changed_captured_bytes_refuse_before_publication(tmp_path, monkeypatch, which): |
| capture | tests/test_semantic_taxonomy_figure.py | 282 | test_captured_yaml_refuses_ambiguity_and_unbounded_graphs | def test_captured_yaml_refuses_ambiguity_and_unbounded_graphs(raw): |
| capture | tests/test_shared_generation_capture.py | 38 | test_captured_wire_does_not_use_legacy_live_readers | def test_captured_wire_does_not_use_legacy_live_readers(selected, monkeypatch): |
| capture | tests/test_shared_generation_scope_context.py | 48 | test_different_captured_scopes_change_every_selected_phase_without_manifest | def test_different_captured_scopes_change_every_selected_phase_without_manifest(external): |
| capture | tests/test_shared_generation_selection.py | 126 | test_authority_drift_stops_without_recapture | def test_authority_drift_stops_without_recapture(selected, key): |
| capture | tests/test_shared_write_footprint.py | 83 | test_registered_asset_copy_is_protected_even_outside_capture_files | def test_registered_asset_copy_is_protected_even_outside_capture_files(registered, tmp_path, monkeypatch): |
| capture | tests/test_snapshot_attestation.py | 11 | captured | def captured(spec): |
| capture | tests/test_source_heading_authority.py | 17 | test_captured_real_authority_preserves_ordinary_compiler_bytes | def test_captured_real_authority_preserves_ordinary_compiler_bytes(): |
| capture | tests/test_source_heading_authority.py | 31 | test_captured_compiler_requires_explicit_typed_inputs | def test_captured_compiler_requires_explicit_typed_inputs(which, bad): |
| capture | tests/test_source_heading_completed.py | 13 | test_actual_linkml_cli_and_captured_validator_parity | def test_actual_linkml_cli_and_captured_validator_parity(tmp_path, order): |
| capture | tests/test_source_heading_completed.py | 171 | test_captured_form_newlines_match_actual_measurement_and_keep_raw_pins | def test_captured_form_newlines_match_actual_measurement_and_keep_raw_pins(tmp_path, monkeypatch, newline): |
| capture | tests/test_source_heading_routing.py | 179 | test_replay_only_reads_captured_schema_and_never_original_sources | def test_replay_only_reads_captured_schema_and_never_original_sources(inputs, tmp_path): |
| capture | tests/test_source_heading_routing.py | 202 | test_changed_captured_authority_or_input_cannot_keep_old_derived_artifacts | def test_changed_captured_authority_or_input_cannot_keep_old_derived_artifacts(inputs, part): |
| capture | tests/test_source_heading_runtime.py | 219 | test_captured_schema_replay_never_resolves_original_aliases | def test_captured_schema_replay_never_resolves_original_aliases(selected, monkeypatch): |
| capture | tests/test_source_heading_runtime_api.py | 258 | test_actual_completed_capture_is_portable_and_refuses_changed_bytes | def test_actual_completed_capture_is_portable_and_refuses_changed_bytes(tmp_path, draft_files, monkeypatch): |
| capture | tests/test_source_heading_runtime_api.py | 393 | test_actual_regated_report_captured_lineage | def test_actual_regated_report_captured_lineage(tmp_path, draft_files): |
| capture | tests/test_source_heading_runtime_api.py | 426 | test_nonempty_captured_vocabulary_does_not_resolve_original_path | def test_nonempty_captured_vocabulary_does_not_resolve_original_path(tmp_path, draft_files, monkeypatch): |
| capture | tests/test_source_heading_runtime_api.py | 465 | test_selected_form_captures_actual_default_instrument_per_invocation | def test_selected_form_captures_actual_default_instrument_per_invocation(tmp_path, draft_files, monkeypatch): |
| capture | tests/test_source_heading_runtime_api.py | 534 | test_actual_default_layout_completed_capture | def test_actual_default_layout_completed_capture(tmp_path, draft_files, monkeypatch): |
| capture | tests/test_source_metadata_evidence.py | 145 | test_capture_dates_are_structured_and_exactly_projected | def test_capture_dates_are_structured_and_exactly_projected(date_value, projected): |
| capture | tests/test_source_snapshot.py | 97 | test_relative_import_outside_source_directory_is_captured | def test_relative_import_outside_source_directory_is_captured(tmp_path, monkeypatch): |
| capture | tests/test_source_snapshot.py | 170 | test_generator_uses_captured_package_bytes | def test_generator_uses_captured_package_bytes(tmp_path, monkeypatch, spelling): |
| capture | tests/test_transformation_measure.py | 403 | test_stale_pair_schema_is_recaptured_before_projection_and_basis_pinning | def test_stale_pair_schema_is_recaptured_before_projection_and_basis_pinning(tmp_path, monkeypatch): |
| capture | tests/test_typed_audit.py | 144 | test_worker_omission_requires_refs_and_captured_membership_even_if_later_dropped | def test_worker_omission_requires_refs_and_captured_membership_even_if_later_dropped(packet, reference): |
| capture | tests/test_typed_audit.py | 245 | test_explicit_captured_core_is_available_and_bound | def test_explicit_captured_core_is_available_and_bound(supplied): |
| capture | tests/test_typed_audit.py | 258 | test_registered_provenance_uses_only_captured_exact_authority | def test_registered_provenance_uses_only_captured_exact_authority(supplied, change): |
| capture | tests/test_typed_audit.py | 287 | test_numeric_priority_tiers_are_captured_without_record_key_coercion | def test_numeric_priority_tiers_are_captured_without_record_key_coercion(supplied): |
| capture | tests/test_typed_audit.py | 372 | test_malformed_schema_refused_before_capture | def test_malformed_schema_refused_before_capture(supplied, raw): |
| capture | tests/test_typed_audit.py | 379 | test_each_capture_identity_mutation_refused | def test_each_capture_identity_mutation_refused(packet, field): |
| capture | tests/test_typed_audit_captured_assets.py | 22 | test_captured_roundtrip_is_byte_identical_without_live_assets | def test_captured_roundtrip_is_byte_identical_without_live_assets(supplied, monkeypatch): |
| capture | tests/test_typed_audit_captured_assets.py | 52 | test_capture_refuses_inexact_roster_even_after_cache_hit | def test_capture_refuses_inexact_roster_even_after_cache_hit(supplied, monkeypatch, change): |
| capture | tests/test_typed_audit_captured_assets.py | 75 | test_changed_saved_response_is_rechecked_with_captured_assets | def test_changed_saved_response_is_rechecked_with_captured_assets(supplied): |
| capture | tests/test_typed_audit_derivations.py | 64 | test_rebuild_keys_cover_captured_schema_inputs_project_and_limits | def test_rebuild_keys_cover_captured_schema_inputs_project_and_limits(supplied, monkeypatch): |
| capture | tests/test_typed_audit_figure.py | 190 | test_post_capture_file_drift_refuses_before_reservation | def test_post_capture_file_drift_refuses_before_reservation(selected,tmp_path,replacement): |
| capture | tests/test_typed_audit_figure.py | 199 | test_render_uses_captured_values_then_refuses_input_drift | def test_render_uses_captured_values_then_refuses_input_drift(selected,tmp_path,monkeypatch): |
| capture | tests/test_typed_audit_figure.py | 263 | test_absent_captured_schema_directory_is_not_a_fresh_output | def test_absent_captured_schema_directory_is_not_a_fresh_output(tmp_path): |
| capture | tests/test_typed_audit_report.py | 216 | test_captured_authority_name_protected_even_when_absent | def test_captured_authority_name_protected_even_when_absent(selected, supplied): |
| capture | tests/test_wave5_5095_review.py | 69 | test_check_requires_same_registration_bytes_at_roster_capture | def test_check_requires_same_registration_bytes_at_roster_capture(checked_batch, monkeypatch): |
| capture | tests/test_wave7_5213_d76_integration_ordering.py | 156 | _capture_batch_fixture | def _capture_batch_fixture(route, spec, sibling, arguments, monkeypatch): |
| capture | tests/test_wave7_5213_d76_round3_binding.py | 224 | test_library_prompt_render_checks_binding_before_shared_capture | def test_library_prompt_render_checks_binding_before_shared_capture(external, monkeypatch): |
| capture | tests/test_wave7_5213_d76_round3_copy_origin.py | 216 | test_native_saved_capture_keeps_prepared_state_deepcopy_compatible | def test_native_saved_capture_keeps_prepared_state_deepcopy_compatible(trace): |
| guard | tests/test_audit_recall_leak.py | 354 | test_a_committed_file_that_does_not_load_or_is_not_ground_truth_fails_the_guard | def test_a_committed_file_that_does_not_load_or_is_not_ground_truth_fails_the_guard(tmp_path): |
| guard | tests/test_build_api_registrations.py | 622 | test_overwrite_guard_requires_replace_on_changed_content | def test_overwrite_guard_requires_replace_on_changed_content(tmp_path: Path) -> None: |
| guard | tests/test_cache_dependencies_dataclass_repr.py | 69 | test_new_origin_exception_keeps_later_state_guards | def test_new_origin_exception_keeps_later_state_guards(change, monkeypatch): |
| guard | tests/test_ci_sharding.py | 408 | test_dedicated_guard_preserves_an_earlier_nonzero_session_finish | def test_dedicated_guard_preserves_an_earlier_nonzero_session_finish(tmp_path): |
| guard | tests/test_d69_fail_closed.py | 43 | test_foreign_guarded_record_never_hides_an_unrelated_account | def test_foreign_guarded_record_never_hides_an_unrelated_account(tmp_path, archive, resume): |
| guard | tests/test_d69_fail_closed.py | 160 | test_guarded_shorter_prefix_does_not_own_an_unattributed_selected_artifact | def test_guarded_shorter_prefix_does_not_own_an_unattributed_selected_artifact(tmp_path, resume): |
| guard | tests/test_direct_keep_awake.py | 263 | test_real_legacy_launcher_keeps_guards_and_receipts | def test_real_legacy_launcher_keeps_guards_and_receipts(real_direct, monkeypatch, outcome): |
| guard | tests/test_fresh_orphan_partial_generation.py | 16 | test_guarded_predecessor_survives_interrupted_index_activation | def test_guarded_predecessor_survives_interrupted_index_activation(tmp_path, monkeypatch): |
| guard | tests/test_manifest_corpus_review_r9.py | 33 | test_guarded_nested_recheck_keeps_the_discovered_pair | def test_guarded_nested_recheck_keeps_the_discovered_pair(project_tree, monkeypatch): |
| guard | tests/test_manifest_corpus_review_r9.py | 77 | test_guarded_recheck_compares_replacement_hashes_with_prior_pins | def test_guarded_recheck_compares_replacement_hashes_with_prior_pins(project_tree, monkeypatch): |
| guard | tests/test_manifest_corpus_review_r9.py | 96 | test_guarded_recheck_holds_unavailable_prior_pins | def test_guarded_recheck_holds_unavailable_prior_pins(project_tree, monkeypatch): |
| guard | tests/test_merge_selection_provenance.py | 131 | test_exact_base_label_and_guard_are_disclosed_independently | def test_exact_base_label_and_guard_are_disclosed_independently(tmp_path, guarded): |
| guard | tests/test_merge_selection_provenance.py | 297 | test_referent_guard_and_actual_source_refusals_still_apply | def test_referent_guard_and_actual_source_refusals_still_apply(tmp_path): |
| guard | tests/test_native_execution_registration_v2.py | 114 | test_preparation_factory_guards_constructed_spec_before_instruction | def test_preparation_factory_guards_constructed_spec_before_instruction(inputs, monkeypatch): |
| guard | tests/test_native_execution_round3_v2.py | 41 | test_package_guard_census_admits_shared_and_u2_dependencies | def test_package_guard_census_admits_shared_and_u2_dependencies(record_property): |
| guard | tests/test_native_generation_frontdoor.py | 205 | guard_paths | def guard_paths(tmp_path, saved_case, monkeypatch): |
| guard | tests/test_native_generation_frontdoor.py | 229 | test_prepare_guard_preserves_exact_join_and_never_dispatches | def test_prepare_guard_preserves_exact_join_and_never_dispatches(saved_case, tmp_path, monkeypatch, capsys): |
| guard | tests/test_native_generation_frontdoor.py | 272 | test_guard_refusal_does_not_create_output | def test_guard_refusal_does_not_create_output(saved_case, tmp_path, monkeypatch, mutation): |
| guard | tests/test_native_generation_frontdoor.py | 295 | test_bad_registration_refuses_without_guard_or_native_side_effects | def test_bad_registration_refuses_without_guard_or_native_side_effects(tmp_path, monkeypatch): |
| guard | tests/test_native_import_facts.py | 266 | test_small_sources_use_original_graph_without_guard_or_extraction | def test_small_sources_use_original_graph_without_guard_or_extraction(tmp_path, monkeypatch, bad, message): |
| guard | tests/test_native_launch_schema_metadata.py | 310 | test_unscoped_source_load_does_not_initialize_new_guard | def test_unscoped_source_load_does_not_initialize_new_guard(): |
| guard | tests/test_native_launch_schema_metadata.py | 347 | test_unready_guard_is_cold_and_cannot_satisfy_hit_canary | def test_unready_guard_is_cold_and_cannot_satisfy_hit_canary(declaration, monkeypatch): |
| guard | tests/test_native_shared_callback_preloading.py | 110 | test_worker_late_package_import_is_refused_by_capture_guard | def test_worker_late_package_import_is_refused_by_capture_guard(isolated_modules): |
| guard | tests/test_native_shared_consumer_census.py | 99 | test_actual_a_guard_accepts_every_current_d_graph | def test_actual_a_guard_accepts_every_current_d_graph(isolated_modules, record_property): |
| guard | tests/test_native_shared_execution.py | 89 | _use_guarded_monitoring_observer | def _use_guarded_monitoring_observer(): |
| guard | tests/test_native_shared_execution.py | 167 | test_launch_case_routes_guarded_monitoring_on_cpython313_and_legacy_elsewhere | def test_launch_case_routes_guarded_monitoring_on_cpython313_and_legacy_elsewhere(tmp_path, monkeypatch): |
| guard | tests/test_native_shared_gate_primitives.py | 26 | test_neutral_gate_primitive_is_accepted_by_the_unchanged_guard | def test_neutral_gate_primitive_is_accepted_by_the_unchanged_guard(): |
| guard | tests/test_native_shared_render.py | 240 | test_native_assembly_has_separate_identity_and_reciprocal_axis_guards | def test_native_assembly_has_separate_identity_and_reciprocal_axis_guards(native_spec): |
| guard | tests/test_native_shared_results.py | 79 | test_actual_snapshot_publication_guard_catches_drift | def test_actual_snapshot_publication_guard_catches_drift(tmp_path, change): |
| guard | tests/test_native_shared_stream_diagnostics.py | 128 | test_other_sample_guards_retain_original_refusal_and_exact_metadata | def test_other_sample_guards_retain_original_refusal_and_exact_metadata(tmp_path, monkeypatch, change, message): |
| guard | tests/test_native_shared_stream_diagnostics.py | 153 | test_reader_guard_before_sample_has_no_invented_diagnostic | def test_reader_guard_before_sample_has_no_invented_diagnostic(tmp_path): |
| guard | tests/test_native_subscription_guard_v2.py | 158 | test_guard_independently_parses_word_timestamp_even_when_hash_rebound | def test_guard_independently_parses_word_timestamp_even_when_hash_rebound(case, value): |
| guard | tests/test_native_subscription_guard_v2.py | 214 | test_rehashed_guard_cannot_choose_weaker_terms_or_other_version | def test_rehashed_guard_cannot_choose_weaker_terms_or_other_version(case, key, value): |
| guard | tests/test_native_subscription_guard_v2.py | 247 | test_guard_file_rechecked_at_dispatch_and_saved_binding | def test_guard_file_rechecked_at_dispatch_and_saved_binding(case, tmp_path): |
| guard | tests/test_native_synthetic_profiles.py | 107 | test_pinned_peer_never_imports_test_code_and_guards_before_fixture_selection | def test_pinned_peer_never_imports_test_code_and_guards_before_fixture_selection(): |
| guard | tests/test_native_synthetic_profiles.py | 271 | test_real_launch_refuses_before_loading_guard | def test_real_launch_refuses_before_loading_guard(runtime, monkeypatch): |
| guard | tests/test_native_trace_profile_runtime.py | 209 | test_effect_guard_refuses_process_network_and_write_events | def test_effect_guard_refuses_process_network_and_write_events(profile, event): |
| guard | tests/test_native_trace_profile_runtime.py | 214 | test_effect_guard_distinguishes_read_only_open_from_write_flags | def test_effect_guard_distinguishes_read_only_open_from_write_flags(profile): |
| guard | tests/test_native_u3b_reuse.py | 100 | test_target_parser_guard_refuses_warm_catalog | def test_target_parser_guard_refuses_warm_catalog(captured, monkeypatch, mutation): |
| guard | tests/test_native_u3d_round9_boundaries.py | 22 | test_all_29_actual_merged_consumers_pass_the_unmodified_guard | def test_all_29_actual_merged_consumers_pass_the_unmodified_guard(isolated_modules, record_property): |
| guard | tests/test_native_u3k_freshness_order.py | 148 | test_frontdoor_defers_capture_without_loading_a_guard | def test_frontdoor_defers_capture_without_loading_a_guard(tmp_path, monkeypatch): |
| guard | tests/test_native_u3k_freshness_order.py | 181 | test_frontdoor_refuses_expired_or_spent_capture_before_engine_without_loading_guard | def test_frontdoor_refuses_expired_or_spent_capture_before_engine_without_loading_guard( |
| guard | tests/test_native_u3l_scanner.py | 90 | test_profile_entry_guards_and_dispatch_refuse_changes | def test_profile_entry_guards_and_dispatch_refuse_changes(route_root, function, before, after): |
| guard | tests/test_native_u4b_a3_policy.py | 99 | test_rehashed_guard_terms_cannot_choose_registered_admission_policy | def test_rehashed_guard_terms_cannot_choose_registered_admission_policy(case, key, mutation): |
| guard | tests/test_native_u4b_a3_policy.py | 121 | test_guard_runtime_is_exactly_the_runtime_in_registration_bytes | def test_guard_runtime_is_exactly_the_runtime_in_registration_bytes(case): |
| guard | tests/test_native_u4b_a3_policy.py | 159 | test_prepare_guard_explicit_terms_must_equal_registered_values | def test_prepare_guard_explicit_terms_must_equal_registered_values(case, field, value): |
| guard | tests/test_native_u4b_a4_cross_word.py | 39 | test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch | def test_saved_word_a_guard_refuses_recorded_word_b_before_dispatch(tmp_path, monkeypatch): |
| guard | tests/test_native_u4b_addendum_authority.py | 146 | test_saved_guard_readback_rechecks_context_even_after_hashes_are_rebound | def test_saved_guard_readback_rechecks_context_even_after_hashes_are_rebound(guard_case, mutation): |
| guard | tests/test_native_u4b_admission.py | 36 | test_actual_capture_owner_guard_join_and_saved_replay | def test_actual_capture_owner_guard_join_and_saved_replay(tmp_path, monkeypatch): |
| guard | tests/test_native_u4b_admission.py | 58 | test_rehashed_guard_cannot_substitute_owner_or_capture | def test_rehashed_guard_cannot_substitute_owner_or_capture(tmp_path, monkeypatch, mutation): |
| guard | tests/test_native_u4b_admission.py | 86 | test_frontdoor_registers_explicit_capture_and_offline_guard_commands | def test_frontdoor_registers_explicit_capture_and_offline_guard_commands(): |
| guard | tests/test_native_u4b_admission.py | 96 | test_historical_guard_readback_keeps_v1_dispatch | def test_historical_guard_readback_keeps_v1_dispatch(): |
| guard | tests/test_native_u4b_capture_retries.py | 160 | test_unknown_guard_event_cannot_select_an_arbitrary_retained_capture | def test_unknown_guard_event_cannot_select_an_arbitrary_retained_capture(tmp_path, monkeypatch): |
| guard | tests/test_native_u4b_windows_v2.py | 23 | test_real_guard_replays_numeric_and_record_only_unknown_windows | def test_real_guard_replays_numeric_and_record_only_unknown_windows(case): |
| guard | tests/test_notes_write_guard.py | 172 | test_the_guard_fails_a_real_run_that_leaks | def test_the_guard_fails_a_real_run_that_leaks(tmp_path, workers): |
| guard | tests/test_pr5212_d55_fixes.py | 78 | test_guard_owns_fields_across_a_stale_writer | def test_guard_owns_fields_across_a_stale_writer(tmp_path, stale_fields): |
| guard | tests/test_pr5212_d55_fixes.py | 100 | test_guard_owned_conflicting_value_is_refused | def test_guard_owned_conflicting_value_is_refused(tmp_path, key): |
| guard | tests/test_receipt_read_identity.py | 47 | test_recorded_manifest_hash_guards_the_mapping_actually_parsed | def test_recorded_manifest_hash_guards_the_mapping_actually_parsed(files, monkeypatch): |
| guard | tests/test_self_disclaimed.py | 115 | test_attribute_and_subrole_caveats_are_guarded_not_flagged | def test_attribute_and_subrole_caveats_are_guarded_not_flagged(): |
| guard | tests/test_self_disclaimed.py | 131 | test_a_narrower_subrole_after_a_verb_cue_is_guarded | def test_a_narrower_subrole_after_a_verb_cue_is_guarded(text): |
| guard | tests/test_self_disclaimed.py | 186 | test_a_passive_cue_is_guarded_by_a_subrole_in_its_clause | def test_a_passive_cue_is_guarded_by_a_subrole_in_its_clause(): |
| guard | tests/test_self_disclaimed.py | 242 | test_a_date_heading_a_passive_subject_is_still_guarded | def test_a_date_heading_a_passive_subject_is_still_guarded(text): |
| guard | tests/test_self_disclaimed.py | 278 | test_a_date_or_attribute_in_the_object_is_still_guarded | def test_a_date_or_attribute_in_the_object_is_still_guarded(text, guard, term): |
| guard | tests/test_self_disclaimed.py | 545 | test_a_date_on_the_cited_source_does_not_guard_the_reported_item | def test_a_date_on_the_cited_source_does_not_guard_the_reported_item(text): |
| guard | tests/test_self_disclaimed.py | 557 | test_a_date_or_amount_in_the_reported_item_is_still_guarded | def test_a_date_or_amount_in_the_reported_item_is_still_guarded(text, term): |
| guard | tests/test_self_disclaimed.py | 785 | test_a_subject_cue_on_a_date_is_guarded | def test_a_subject_cue_on_a_date_is_guarded(text): |
| guard | tests/test_self_disclaimed.py | 839 | test_a_date_in_the_cues_own_conjunct_is_still_guarded | def test_a_date_in_the_cues_own_conjunct_is_still_guarded(): |
| guard | tests/test_self_disclaimed.py | 1714 | test_a_guard_reading_the_object_needs_the_pattern_to_declare_one | def test_a_guard_reading_the_object_needs_the_pattern_to_declare_one(): |
| guard | tests/test_shared_generation_completed_replay.py | 173 | test_explicit_completed_guard_cannot_override_active_or_malformed_progress | def test_explicit_completed_guard_cannot_override_active_or_malformed_progress(prepared, completed): |
| guard | tests/test_shared_generation_condition_compatibility.py | 62 | test_installed_guard_identity_does_not_invent_a_predecessor | def test_installed_guard_identity_does_not_invent_a_predecessor(tmp_path, monkeypatch): |
| guard | tests/test_shared_schema_sync_resources.py | 267 | test_guard_discovery_does_not_cache_success_across_boundaries | def test_guard_discovery_does_not_cache_success_across_boundaries(tmp_path, monkeypatch): |
| guard | tests/test_usage_ledger.py | 631 | test_legacy_shaped_artifacts_cannot_erase_a_guarded_generation | def test_legacy_shaped_artifacts_cannot_erase_a_guarded_generation(tmp_path): |
| guard | tests/test_usage_ledger.py | 919 | short_guard | def short_guard(monkeypatch): |
| guard | tests/test_wave7_5213_d76_relative_registration.py | 21 | test_sg2_binding_relative_base_passes_actual_completed_path_guard | def test_sg2_binding_relative_base_passes_actual_completed_path_guard(tmp_path, draft_files, monkeypatch): |
| guard | tests/test_wave7_5213_d76_round4_inventory.py | 101 | test_declared_entry_guard_precedes_input_model_and_authority | def test_declared_entry_guard_precedes_input_model_and_authority(candidate, external, monkeypatch): |
| guard | tests/test_wave7_5213_d76_round4_inventory.py | 340 | test_a_guard_declaration_cannot_replace_the_runtime_refusal | def test_a_guard_declaration_cannot_replace_the_runtime_refusal(external, monkeypatch): |
| guard | tests/utils/isolated_pytest.py | 135 | install_offline_guard | def install_offline_guard(output, denials): |
| guard | tests/utils/native_consumer_observer_checks.py | 412 | check_profile_stability_guards | def check_profile_stability_guards(): |
| ci_evidence | tests/test_native_execution_ci_v2.py | 138 | ci_evidence | def ci_evidence(fabricated_authorizations, local_ci_git, monkeypatch): |
| probe | tests/test_bc1_g2_round2.py | 15 | entry_probe | def entry_probe(tmp_path, monkeypatch): |
| probe | tests/test_native_execution_observation.py | 20 | test_runtime_probe_uses_exact_env_and_filters_secrets_without_calling_native | def test_runtime_probe_uses_exact_env_and_filters_secrets_without_calling_native(tmp_path,monkeypatch): |
| probe | tests/test_native_execution_permissions.py | 306 | test_exact_positive_decimal_budget_is_preserved_in_probe_argv | def test_exact_positive_decimal_budget_is_preserved_in_probe_argv(fixture,tmp_path,budget): |
| probe | tests/test_native_full_schema_profile_runtime.py | 453 | test_environment_disclosure_uses_local_values_without_processor_probe | def test_environment_disclosure_uses_local_values_without_processor_probe(profile, monkeypatch): |
| probe | tests/test_native_generation_frontdoor.py | 92 | test_validate_probe_uses_saved_bytes_and_never_runs_a_producer | def test_validate_probe_uses_saved_bytes_and_never_runs_a_producer(saved_case, tmp_path, monkeypatch, capsys): |
| probe | tests/test_native_generation_frontdoor.py | 116 | test_unknown_expectation_kind_refuses_before_probe_read_or_producer | def test_unknown_expectation_kind_refuses_before_probe_read_or_producer(saved_case, tmp_path, monkeypatch, kind): |
| probe | tests/test_native_model_aliases.py | 215 | test_probe_adapter_keeps_cli_requested_and_http_returned_without_transport | def test_probe_adapter_keeps_cli_requested_and_http_returned_without_transport(fixture, tmp_path, monkeypatch): |
| probe | tests/test_native_shared_execution_failure.py | 22 | test_missing_external_gate_refuses_before_reservation_or_probe | def test_missing_external_gate_refuses_before_reservation_or_probe(tmp_path, monkeypatch, missing): |
| probe | tests/test_native_shared_execution_failure.py | 79 | test_v2_partial_reservation_stays_spent_without_probe | def test_v2_partial_reservation_stays_spent_without_probe(execution_case, monkeypatch, boundary): |
| probe | tests/test_native_synthetic_profiles.py | 296 | test_real_probe_producers_refuse_synthetic | def test_real_probe_producers_refuse_synthetic(runtime, entry): |
| probe | tests/test_native_u3b_reuse.py | 409 | test_review_probe_ordinary_event_native_refusal_parity | def test_review_probe_ordinary_event_native_refusal_parity(raw): |
| probe | tests/test_native_u3b_reuse.py | 418 | test_review_probe_bom_and_input_size_parity | def test_review_probe_bom_and_input_size_parity(): |
| probe | tests/test_native_u4b_a3_frontdoor.py | 85 | test_current_model_cannot_use_unbound_legacy_probe_cli | def test_current_model_cannot_use_unbound_legacy_probe_cli(tmp_path, monkeypatch): |
| probe | tests/test_native_u4b_probe_sequence.py | 88 | test_runtime_cannot_use_bound_probe_as_its_own_observation | def test_runtime_cannot_use_bound_probe_as_its_own_observation(prepared, role): |
| probe | tests/test_native_u4b_runtime.py | 73 | probe_rows | def probe_rows(inputs): |
| probe | tests/test_native_u4b_runtime.py | 77 | write_probe | def write_probe(inputs, rows): |
| probe | tests/test_native_u4b_runtime.py | 128 | test_saved_probe_accepts_declared_returned_assistant_label | def test_saved_probe_accepts_declared_returned_assistant_label(inputs): |
| probe | tests/test_native_u4b_runtime.py | 140 | test_saved_probe_refuses_contradictory_or_missing_frame_model | def test_saved_probe_refuses_contradictory_or_missing_frame_model(inputs, mutation): |
| probe | tests/test_native_u4b_runtime.py | 253 | test_registered_not_emitted_state_cannot_replace_observed_probe_thinking | def test_registered_not_emitted_state_cannot_replace_observed_probe_thinking(inputs): |
| probe | tests/test_native_u4b_runtime.py | 283 | test_saved_probe_refuses_missing_ambiguous_or_conflicting_evidence | def test_saved_probe_refuses_missing_ambiguous_or_conflicting_evidence(inputs, change): |
| probe | tests/test_native_u4b_runtime.py | 410 | test_saved_probe_changes_are_not_allowed | def test_saved_probe_changes_are_not_allowed(inputs): |
| probe | tests/test_receipts_v5_merge_n3.py | 18 | probe | def probe(pattern, text, mode): |
| probe | tests/test_renderer_contract_captures.py | 437 | test_probe_shared_contracts_occur_three_times_in_the_joined_section | def test_probe_shared_contracts_occur_three_times_in_the_joined_section(tmp_path, stable): |
| probe | tests/test_renderer_contract_captures.py | 450 | test_probe_each_api_phase_suffix_carries_one_more_copy | def test_probe_each_api_phase_suffix_carries_one_more_copy(): |
| probe | tests/test_renderer_contract_captures.py | 459 | test_probe_measures_the_duplicated_bytes_at_renderer_17 | def test_probe_measures_the_duplicated_bytes_at_renderer_17(tmp_path, stable): |
| probe | tests/test_shared_generation_scope_context.py | 442 | test_a14_r2_f1_probes_move_descriptor_or_refuse | def test_a14_r2_f1_probes_move_descriptor_or_refuse(selected, monkeypatch, tmp_path): |
| probe | tests/test_wave7_5213_d76_registration.py | 123 | test_native_execution_registration_from_corpus_root_verifies_saved_probe | def test_native_execution_registration_from_corpus_root_verifies_saved_probe(tmp_path, monkeypatch): |

## 4. Fixture Builders in tests/utils/

| Word | File | Line | Function Name | Stripped Definition Line |
|---|---|---:|---|---|
| registration | tests/utils/native_u4b_fixtures.py | 19 | registration_commit_for | def registration_commit_for(raw, directory, *, author_date): |
| review | tests/utils/isolated_pytest.py | 81 | review_adapter | def review_adapter(root): |
| bundle | tests/utils/native_u4b_fixtures.py | 48 | bundle_for | def bundle_for(registration_raw, directory, now='2026-11-08T00:00:00Z'): |
| launch_word | none | none | none | none |
| word | none | none | none | none |
| account_choice | none | none | none | none |
| statement | none | none | none | none |
| runtime | tests/utils/native_synthetic_evidence.py | 15 | runtime_for | def runtime_for(data, root): |
| capture | none | none | none | none |
| guard | tests/utils/isolated_pytest.py | 135 | install_offline_guard | def install_offline_guard(output, denials): |
| guard | tests/utils/native_consumer_observer_checks.py | 412 | check_profile_stability_guards | def check_profile_stability_guards(): |
| ci_evidence | none | none | none | none |
| probe | none | none | none | none |
