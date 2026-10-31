# E3x × #5096 bounded relocation repair

Offline evaluation repair, begun 2026-10-29 and completed 2026-10-30 after a reboot.
All requested invocations completed. E3x/D52 and #5213 composition pass. Full CI
execution retained harness/process failures and one timing failure; all 33 affected
cases subsequently passed individually. Bare whole-tree collection still has the
three out-of-scope errors documented below. This is not an all-green CI claim.

## Inputs and merge record

- Starting branch: `codex/wave7-e3x-fixes-20261029`, `709099dbc2c621b47b0e9d0f401a6a386da5d400`.
- Main merged with `git merge --no-ff origin/main`: `50bc50af678ae5216b3985c340fe1344da26c05e`.
- Merge commit: `28f13294a006eacd5ae3f769b0d74b643cf9d2c0`. No textual conflicts.
  Git automatically composed `notes/arm_comparison.md`, the evaluation resolver,
  and its tests. Other incoming files are inherited from the authorized main merge.
- Repair commit: `3ea09cac3`; generated report refresh: `c0840e780`.
- The complete provisional analysis was read before editing. Its retained Git
  source is `codex/wave7-suite-tools-20261029:notes/reviews/wave7_arm_relocation_provisional_2026-10-29.md`.

The semantic conflict was E3x's universal external-path refusal versus #5096's
supported preprocessed-tail relocation. The composed control reproduced `match`
where the E3x assertion expected `unknown`. A cold focused invocation also exposed
a provenance-import metadata read caught by the trap; warming the #5096 positive
first isolated the semantic assertion. Those pre-reboot logs were lost, so they
are historical observations, not the retained acceptance evidence below.

## Implemented contract and review

`arm_comparison._lexical_relative` preserves already-owned paths before considering
foreign relocation. A foreign absolute path must contain exactly one adjacent
`data/preprocessed` pair; counting precedes normalization so traversal cannot hide
repeated pairs. Its tail maps under the selected root. Both lexical and realpath
containment remain mandatory. Live disk checks and pinned historical-manifest
recovery use the same lexical policy, including the entire prefix of owned paths.

The shared provenance helper is unchanged by the repair. Recorded pins, recovered
bytes, disk identity, and cross-arm identity remain separate evidence. The E3x test
now asserts the supported positive and explicit unknowns for unsupported/ambiguous
inputs. Both ambiguous candidate files deliberately exist with matching bytes;
neither existence nor matching bytes may choose a tail. Separate tests refuse an
ambiguous manifest without historical lookup and preserve owned repeated pairs
through exact Git recovery. The bounded-read traps and #5096 positive are retained.

The renderer and per-record refusal suffix distinguish supported relocation from
unsupported or ambiguous cases. `scripts/arm_comparison.py --no-figures` refreshed
the committed report. The reviewed diff changes only that explanatory paragraph;
all measurements and tables are unchanged. No figures or ratings were produced.
Separate read-only diff review found no additional resolver defect.

## #5213 scratch composition

Temporary merge input: `b6fba59465051230f8082c7c3cdb5c1a05ce3fbf` onto `c0840e780`.
Every textual conflict and its resolution:

| Path | Conflict | Resolution |
|---|---|---|
| `src/data_sheets_schema/evaluation/arm_comparison.py` | Helper documentation, foreign-tail fallback, recovery comment | Retain repaired blob `9fc613b4c14c1fc6d0c7faae8d4179f1dfc6c1a7`. It already includes #5139's shared lexical policy and NUL refusal, plus explicit ambiguity refusal. |
| `scripts/adhoc/preserve_wave5_validation_20261028.py` | Add/add; retained-evidence explanation | Use the packet's reviewed blob `09c84644d1a372e36a2dacaf3b001117cb220e06`. |

Resolved scratch tree: `d70d4926b044489427af70879da670d6affcc952`.
The incoming tests merged automatically; none were dropped.
The post-reboot run of complete `test_arm_comparison.py`,
`test_5139_relative_paths.py`, `test_wave3_5139_review.py`, and
`test_wave3_5139_paths.py` passed **92 tests**, exit **0**, in **171.68 seconds**.
The temporary merge was then aborted. The source, tests, global provenance helper,
API runner, and launcher were verified restored to the repair head. #5213 is not
part of this branch's ancestry.

## Retained validation evidence

Evidence directory: `tmp/e3x-relocation-validation-20261029/` in this worktree,
ignored by Git and persistent across reboot. Pytest basetemp and bytecode remain
under `/private/tmp/d4d-e3x-relocation-20261029/`. The check launcher records HEAD,
interpreter, source/test/helper/workflow/timing hashes, host load, log, JUnit, and
exit status. Provider credentials and proxy variables are unset. The macOS test
sandbox allows loopback fixtures and denies external network connections.

Interpreter: project `.venv/bin/python`, Python **3.13.12**. This is a local serial
execution of CI's partition, not a Python 3.12 CI result. FAIRSCAPE was populated
offline from pinned local Git object `8c80311d7d8b0fadac07dca9567d632103691f48`.
Pre-existing `tests/__pycache__` files date to 2026-10-29 00:01 and were preserved.

The initial post-reboot composition attempt lacked the external basetemp parent:
15 passed and 40 setup errors before interruption. The launcher now creates the
parent. Its one-test canary passed and persisted non-empty log/JUnit plus exit 0
before the complete successful 92-test composition rerun. The failed evidence is
retained as `composition-5213.*`; acceptance evidence is `composition-5213-verified.*`.

Machine-readable evidence, including artifact sizes/hashes, interpreter and
dependency versions, individual outcomes, and every isolated rerun:
[validation JSON](e3x_5096_relocation_validation_2026-10-29.json).
It is generated by `scripts/adhoc/summarize_e3x_relocation_checks_20261029.py`.
The complete post-reboot runs used `219d96286e6e6e14f4c0df7cdffc19badbf84005`.
The final commit only updates validation helpers and evidence; the resolver,
tests, and report are unchanged from that tested head. Their SHA256 values are
recorded in each invocation's retained `.inputs` file.

### Collection and complete CI partition

The fresh bare `pytest --collect-only -q` invocation collected **24,753** tests
but exited **2** with three errors (24.63 seconds):

- `src/renderer/test_renderer.py` and `src/renderer/test_yaml_extraction.py`
  cannot import the uninstalled optional `weasyprint` dependency.
- `src/scripts_obsolete/download_module_test.py` attempts a Google Docs download
  during import. External networking was blocked, yielding a connection error.

Those renderer/obsolete scripts are outside this evaluation repair. No dependency
installation or network access was used to conceal the collection failures.
CI's `tests/` scope collected **20,760** tests successfully, exit **0** (18.93 seconds).

The complete PR layout from `.github/workflows/main.yaml` ran serially with
`utils.pytest_shard`, the unchanged `utils/ci_test_durations.json`, six ordinary
shards, and all four dedicated routing lanes. Shard 1 was the full-lane canary;
its non-empty log/XML and exit 0 were verified before starting the remaining jobs.

| Invocation | Passed | Skipped | Failed | Teardown errors | Exit | Seconds |
|---|---:|---:|---:|---:|---:|---:|
| Ordinary 1/6 | 2,304 | 2 | 0 | 0 | 0 | 2679.99 |
| Ordinary 2/6 | 3,804 | 28 | 2 | 0 | 1 | 2785.48 |
| Ordinary 3/6 | 3,083 | 2 | 0 | 0 | 0 | 2271.11 |
| Ordinary 4/6 | 4,137 | 14 | 0 | 0 | 0 | 5311.48 |
| Ordinary 5/6 | 3,240 | 0 | 0 | 0 | 0 | 1998.51 |
| Ordinary 6/6 | 4,140 | 0 | 0 | 3 | 1 | 2491.22 |
| Routing dispatch | 1 | 0 | 0 | 0 | 0 | 530.16 |
| Routing portable | 1 | 0 | 0 | 0 | 0 | 1260.10 |
| Routing regate | 1 | 0 | 0 | 0 | 0 | 424.81 |
| Routing default layout | 1 | 0 | 0 | 0 | 0 | 569.87 |

The table preserves pytest's original phase counts: the three teardown errors
follow passed test bodies. The summary compares **multisets of collected and
executed node IDs**: all 20,760 instances ran, with zero missing or unexpected
instances. The existing parametrized node
`test_native_execution_permissions.py::test_noncanonical_or_numeric_budget_never_becomes_a_native_argument[00]`
occurs twice in both collection and execution; 20,759 distinct strings therefore
represent 20,760 instances. It is not a missing test or an extra shard execution.

The host power log confirmed repeated idle/maintenance sleeps during shard 4.
Temporary `caffeinate` assertions were tied to the batch and rerun launcher PIDs;
they expired when those processes ended. Durations above are pytest's recorded
elapsed times, including the interruptions.

### E3x/D52 and the separate offline CI jobs

The exact 16-file E3x/D52 roster from `run_e3x_acceptance_20261029.sh` passed
**687 tests**, exit **0**, in **489.65 seconds**. The original 684 increased by
#5096's historical-worktree positive and the two new ambiguity/owned-prefix tests.
No original test or refusal assertion was removed or weakened to accept two statuses.

| Separate CI job | Passed | Skipped | Failed | Exit | Seconds |
|---|---:|---:|---:|---:|---:|
| Budget controls | 396 | 12 | 0 | 0 | 12.57 |
| Native controls | 974 | 0 | 27 | 1 | 684.51 |
| Audit/finalization controls | 2,167 | 0 | 1 | 1 | 511.78 |
| Evaluation controls | 295 | 0 | 0 | 0 | 413.48 |

All explicit workflow test files were included. Schema build jobs were not run:
the PR workflow skips them, and this task forbids generation-side edits.

### Failure isolation and harness correction

Every affected case ran **alone**, serially, using
`scripts/adhoc/rerun_e3x_environment_failures_20261030.py`:

- Both `TestAgainstARealProcess` failures in `tests/test_run_lock.py` passed
  individually (0.11 and 0.08 seconds). The added network sandbox prevents macOS
  from executing `ps`, which the zombie-state check needs. The retained diagnostic
  reproduces sandbox exit 71 versus direct exit 0.
- All 27 failures from `native_controls/test_native_launch.py` passed individually.
  Its independent child-state/parent checks also use `ps` on macOS. These reviewed
  tests launch only synthetic local processes. Their isolated reruns omit the
  optional network sandbox; provider keys and proxies remain unset.
- All three preflight-resource teardown cases passed individually. Their original
  tracebacks show exactly one changed path: the growing `ci-ordinary-6.log` in the
  ignored evidence directory. The test bodies had passed and all other paths were
  unchanged. The launcher now writes live log/XML outside the worktree, then copies
  completed artifacts into persistent storage. One real snapshot-test canary
  passed and persisted its log/XML/exit status before the other reruns.
- `test_execute_child_real_blocked_observer_stays_unclosed_and_cli_is_reaped`
  passed alone in 1.25 seconds with the same network sandbox. Its original failure
  was `entered.is_set()` after a 0.2-second child-start deadline on the loaded host.

All **33 isolated reruns exited 0**. Original failures remain in the evidence;
the full shard/job invocations are not relabeled successful. No production or
generation code was changed to accommodate these environmental outcomes.

### Local follow-ups and final scope review

Online issue filing is forbidden by this task. These are retained for lead triage:

1. Renderer collection dependency: decide whether bare collection should require
   WeasyPrint or isolate optional renderer tests. Two collection errors remain.
2. Obsolete downloader import: make collection independent of external downloads
   or exclude the obsolete script explicitly. Its collection error remains offline.
3. macOS process diagnostics: the optional test network sandbox conflicts with
   `ps`; synthetic process-only reruns require the normal local process environment.
4. Validation log placement: corrected locally in the retained launcher and
   verified by the three checkout-snapshot tests.
5. Audit lifecycle timing: the 0.2-second observer-start deadline failed in the
   loaded batch and passed unchanged alone; retain as a timing-flake report.
6. Parametrized node ID collision: two existing native-permission cases both use
   `[00]` under this interpreter/pytest environment. Both executed and passed;
   distinct IDs would improve reporting and isolated selection.

Separate read-only review of the final resolver/test/report diff found no additional
repair defect. `git diff --check` passes. Changes after the main merge are limited
to the evaluation resolver/tests/report and validation helpers/evidence. The shared
provenance helper and generation runner/launcher match the main-merge state.
Protected files, decision records, STATUS.md, run directories, and `data/ATTIC/`
have no repair delta. No merge is pending; #5213 remains outside the branch ancestry.
No push, GitHub operation, provider call, or rating campaign was performed.
