# N2-R3: neutral acceptance stops inside the recorder helper

The fresh neutral public-path test failed on
`01969cbed8eed93f420c640c1f1c306e5f58b033` (tree
`d92f24c84aad9161457930a4b191564868ac0676`). The recorder helper exceeded
its unchanged **180-second subprocess limit**. This is an observed helper
timeout; the retained error is not an expiry of the enclosing **900-second
native child deadline**. The omission case was not run because neutral failed.
Default-profile runtime acceptance remains incomplete.

This addendum records a failed offline software fixture. It does not revise a
deadline, relax a guard, register a live canary, or authorize a retry.

## Reproduction and preservation

The runner selected exactly
`tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`.
Its console result is **1 failed, 12 warnings in 732.42 seconds**. JUnit records
one failure, zero errors/skips, suite time **732.349 seconds** and testcase time
**732.107 seconds**. These are different reported clocks; none is a measured
recorder duration beyond the timeout, and pytest includes preparation and
post-child evidence collection. The driver returned 1. Its `outcome.json`
explicitly records that omission was not run.

The finalizer returned 0: all four preservation booleans are true, the source
snapshots before the test, after neutral and at finalization are equal, and
tracked bytes match the selected head. The case inventory was unchanged during
archiving. Preservation success does not convert the failed test into a pass.

Original evidence: `/private/tmp/d4d-native-n2-acceptance-01969cbed/`.
The orchestrator copied the finalized `upload/` contents to
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-n2-2026-10-25/evidence/acceptance-01969cbed/`
and verified exact directory equality, including `cases.tar.gz`. The archive
manifest records **18,352,510 bytes**, SHA256
`5bf6f084b8dfd4c364907373f912129fd5705577a302407204877f9cd7e905ec`.
The compact [extracted summary](native_n2_validation_2026-10-25/acceptance-01969cbed-summary.json)
pins every input it reads, including the final result, replay report, transcript,
stderr, provenance, JUnit and source snapshots. It copies the archive's identity
from the finalized manifest rather than independently rehashing that archive.

Recreate the extraction from the retained original directory with the committed
[summary helper](../scripts/adhoc/summarize_native_n2_acceptance_20261025.py),
using a fresh output path:

```bash
python3 scripts/adhoc/summarize_native_n2_acceptance_20261025.py \
  --evidence /private/tmp/d4d-native-n2-acceptance-01969cbed \
  --out /private/tmp/native-n2-acceptance-recheck.json
```

This helper extracts saved fields; it does not rerun generation, acceptance
gates, source support checks or the provider.

## Observed completion boundary

Within `cases/neutral/test_actual_public_correction_0/native26/`:

- `fresh-attempt/stages/records/000022.json` is `assembly_checked`;
  observation `000044.json` records `assembly_complete`. The retained stage
  completion includes receipt, three workers, omission and integration.
- Transcript tools 40–47 complete final core derivation, full schema/terms,
  core schema, pair, receipt, scope and source inventory with exit 0.
- Tool 49 is the intentional failed report draft (exit 1). Tool 52 is the
  corrected draft (exit 0), verified against the current saved report bytes.
  Tool 53 completes final evidence checks with exit 0.
- Tool 54 is the admitted `provenance record` command. Its callback is retained,
  but there is no corresponding settled tool result or native terminal result.
  `native-attempt/stderr.txt` identifies `subprocess.TimeoutExpired` from the
  fake peer's `subprocess.run(..., timeout=180)`.
- `SYNTHETIC_provenance.yaml` was written, including the native stage-completion
  digest and `runtime_acceptance: pending independent saved readback`. Its
  top-level deterministic check blocks (`pair_consistency`, `report_claims`,
  `grounding`, `form`, `receipts`, `review`) are absent. The recorder writes this
  initial record before calling `_inline_checks`
  ([CLI source](../src/data_sheets_schema/cli/provenance.py)). The evidence
  therefore establishes a post-write recorder interruption, not successful
  inline-check or recorder completion. It does not locate the exact slow
  function within that remaining work.

## Final state and gates

The final result has `state: failed`, `runtime_gates_passed: false` and
`first_stop: native control session ended without complete evidence`.
Shutdown completed with zero unfinished control workers. The live attribution
report records two draft checks, `recorder_completed: false` and a controller
stop for unsettled tool calls, missing final obligations and missing terminal.
The saved reconstruction is checked but failed, with
`recorder_completed_in_trace: false` and pending tool `shared-test-54`.

| Final gate | Checked | Passed |
| --- | --- | --- |
| accounting | false | false |
| evidence | true | true |
| first_stop | true | false |
| keep_awake | true | true |
| live_attribution | true | false |
| observation | true | false |
| pair | true | true |
| phase_history | true | false |
| receipts | true | true |
| runtime_authority | true | true |
| saved_attribution | true | false |
| schema | true | true |
| shutdown | true | true |
| terminal | false | false |
| tool_history | true | false |

The corrected draft's individual success does not make the final draft/history
gate pass: the unresolved recorder and absent terminal invalidate completed
history. Similarly, the replay phase's `complete: true` indicates that it was
evaluated as a completed history, while its `passed: false` and problems remain
authoritative. The test fails at its first runtime-success assertion, so its
later successful `read_final` equality and spent-attempt refusal assertions
were not reached. A failed saved reconstruction was nevertheless produced by
the launcher and retained.

## Limits and next diagnostic

The fixture uses a permissive **registered coverage floor 0/1**, not the
pending floor used in the hypothetical render comparison. The receipt gate's
pass does not choose an empirical threshold or establish scientific coverage.
Runtime/auth/account/subscription/review declarations and the model peer are
explicitly synthetic. `keep_awake` is explicitly not applicable. Final
`scientific_acceptance` is `not_assessed`, `provider_billing` is `not_verified`,
and evidence authentication is `not_cryptographically_authenticated`.

A source-only performance review identified a candidate for measurement in
[native_shared_capture.py](../src/data_sheets_schema/native_shared_capture.py):
`live_provenance_block` calls `_load_live` without a catalog; `_base` can seed
its base cache only when an explicit catalog/token already exists, while
`_loaded` constructs the default catalog later. A later `_recorded_run` using
that catalog may repeat registration and permission/source validation. This is
an **unmeasured duplication hypothesis**. The retained evidence does not prove
that this attempt reached the inline receipt readback, nor that this path
caused the timeout; `check_record` or other inline work may dominate.

Next, measure recorder phase boundaries and catalog eligibility using an
isolated offline diagnostic, preserving the registration, freshness and source
checks. Apply and review a bounded correction only after identifying the cost.
Then rerun unchanged neutral acceptance with fresh identities; omission remains
gated on its success. Preserve this failed attempt. No deadline increase,
guard bypass or retry without a change is justified by this result.
