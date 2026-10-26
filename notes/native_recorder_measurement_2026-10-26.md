# Native recorder measurement preparation — 2026-10-26

Refs #4354; coordination contract: `notes/coordination/2026-10-25-codex-next.md`, section 2. This is a measurement plan and tooling description, **not a measurement result or acceptance claim**. Focused helper validation is complete; the three idle trials and paired diagnostic runs remain pending. The observer is prepared but has not been installed in either frozen comparison tree.

| Role | Exact frozen commit | Pristine comparison tree |
|---|---|---|
| Current unit-4 acceptance implementation | `01969cbed8eed93f420c640c1f1c306e5f58b033` | `/private/tmp/d4d-codex-recorder-current-20261026` |
| Original implementation for comparison | `d41282871394dd8abe74e11afb0e80c95d149305` | `/private/tmp/d4d-codex-recorder-original-20261026` |

“Current” identifies this frozen comparison, not repository main or later delivery/documentation commits. Tooling is separate in `/private/tmp/d4d-codex-recorder-tools-20261026`; it does not amend either baseline. All work is offline: no provider calls, GitHub actions, pushes, installations, or edits to the receipt implementation or protected files.

1. The two helper modules passed all **27 tests** after the gitlink correction: `tests/test_native_recorder_measure_helper.py` and `tests/test_native_recorder_observer_20261026.py`. Independent static review is complete. These are helper tests, not recorder acceptance trials.
2. Obtain a quiet window from Claude, then run three serial, **uninstrumented** current-head trials of `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`. No observer, bootstrap, or config belongs in those trials. An idle preflight refusal or later competing-process observation does not count as an idle replicate.
3. If the failure does not reproduce in those three qualified trials, perform the conditionally requested full-suite/load comparison under separately recorded orchestration. The driver's `load-diagnostic` option only labels a one-node run; it does not launch or define a full suite. Busy-host timings alone do not establish load dependence.
4. Create separately reviewed diagnostic heads derived from both exact commits. Apply the **same** bootstrap, observer helper, and config bytes in each. Record each derived head and its complete diff from its baseline, including source/test/asset differences between baselines. Instrumented observations cannot replace the uninstrumented trials or prove that both revisions used identical scientific fixtures.

The quiet-host requirement is **pending**. The coordination ledger records competing Python work and a request for Claude to arrange a quiet window. That prior observation is not a fresh host check; this note neither asserts present idleness nor launches a trial. Other sessions and processes remain untouched.

This concrete readiness command performs source verification and a 30-second host sample **without launching pytest**. Use a fresh trial name if the evidence directory already exists:

```bash
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -P -B \
  /private/tmp/d4d-codex-recorder-tools-20261026/scripts/adhoc/native_recorder_measure_20261026.py \
  --tree /private/tmp/d4d-codex-recorder-current-20261026 \
  --target current --output /private/tmp \
  --trial d4d-recorder-idle-readiness-20261026-01 \
  --mode idle --idle-only --idle-seconds 30 --plugin-autoload enabled
```

The declared default idle gate requires mean CPU ≤15%, peak ≤35%, one-minute load/logical CPU ≤0.5, and no unowned sampled process at ≥5% CPU. These are explicit sampling criteria, not proof of complete host exclusivity. Actual test runs also require an explicit outer driver watchdog of 900–7,200 seconds; reaching it censors the measurement. It does not change the recorder's **180-second helper deadline** or the test's **900-second registered runtime**.

`scripts/adhoc/native_recorder_measure_20261026.py` pins exact Git heads, tracked source/test/policy assets and hidden/ignored Python within its declared roots. It rejects source drift and foreign loaded project/test module or namespace roots, records interpreter/distribution metadata and explicit plugin-autoload policy, and retains pre/post source inventories, host samples, logs, JUnit and outcomes. Import-origin verification applies to the pytest process; nested helpers retain their existing registered environment and authority checks. Distribution metadata is not a verification of installed package bytes. Other data/docs are outside its stated source inventory. Credential removal and offline fixture selection do not constitute a network sandbox.

The first formal idle-only attempt stopped during source inventory, before host sampling or a test launch: the helper treated the root `aurelian` gitlink as a regular file. Its failed log remains at `/private/tmp/d4d-recorder-idle-check-1-20261026.log`; the partial output is retained. The corrected inventory records exact Git `160000 commit` entries separately by path and commit object. It accepts only absent or empty physical directories as uninitialized submodules, and refuses symlink, regular-file or populated replacements. Submodule contents are outside the byte inventory; initialized submodules require separate validation. This correction does not establish an idle window or change either frozen baseline. Its follow-up validation is pending.

`scripts/adhoc/native_recorder_observer_20261026.py` uses `sys.monitoring` without wrappers, monkeypatches or production imports solely for observation. It records inclusive boundaries around native capture, record writes/validation and inline duplicate-key, receipt, form, grounding, report and pair checks. It distinguishes current `_open` JSON/unblob decoding in the shared bounded cache from the original raw-tuple `_opened` cache, observes natural token returns, and distinguishes eviction-statement entries from confirmed removals. Missing/unreached targets remain unmeasured. Callback overhead is recorded but not subtracted; nested durations must not be summed as exclusive time. Bounded incremental JSONL survives an incomplete run; a missing end event cannot imply success.

Its proposed bootstrap runs only for `provenance record`. The closed child environment is unchanged: an identical committed config selects `/private/tmp/d4d-recorder-observer-20261026`, with exclusive PID/time output directories. The diagnostic runner must correlate the recorder PID and retain helper/bootstrap/config hashes. Source hashes and naturally loaded module/namespace origins accompany observations. The observer schedules a stack dump at approximately **170 seconds of process age**, accounting for imports before `cli/__main__.py`; it does not extend either deadline. The separately reviewed diagnostic-head execution path is still required—the pristine baseline driver intentionally refuses modified or derived heads.

## Retained helper verification

Python 3.13.12 from the primary checkout's `.venv`, explicit helper-tree imports,
bytecode and pytest plugin autoload disabled, serial execution. The first run
was **18 passed / 8 failed**: one output-containment alias defect, one synthetic
namespace fixture using a nonphysical path, and six failures from enabling
global-only `PY_UNWIND` as a local event. Corrections preserve strict origins,
source-output refusal, target frame checks and all real event/exception
assertions. The driver alone then passed **15 tests**; the final combined run
passed **26 tests**. Counts overlap and must not be summed.

Logs and JUnit are retained in `native_recorder_tool_validation_2026-10-26/`.
The observer registers unwind globally, ignores/counts unrelated unwinds, and
discloses that additional observation overhead; return/line events remain
local. No production source, acceptance deadline, recorded generation or
comparison-tree file was changed by these tests.

The first actual readiness invocation stopped before host sampling: the root
`aurelian` gitlink had been treated as regular-file input. The corrected helper
pins each exact Git gitlink path/commit separately and refuses populated,
symlink or regular-file replacements. An absent path is inventoried but still
fails the unchanged clean-tree gate when Git reports it deleted; an empty
uninitialized directory passes. The added fixture initially expected absence
to be clean (26 passed / 1 failed); correcting that expectation retained every
production guard. Final combined verification: **27 passed, 1.88 s**. Both
test iterations and the failed readiness log are retained alongside the prior
evidence. No baseline source or submodule was initialized or changed.
