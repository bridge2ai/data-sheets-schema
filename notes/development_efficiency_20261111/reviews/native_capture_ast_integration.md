# Independent native capture/AST integration review

**S ready for the approved sparse private-preparation path.** No source-review
blocker found at `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b` on
`codex/native-capture-ast-integration-20261111` in the assigned
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-u1u3`.
Final read-only HEAD/status check was clean at **2026-11-11 05:39:47 UTC**.
Baseline: `458887766effe38207a77fea2d8033f1f3e1c7f3`.

This is an integration/source review, not an execution result. No Python imports,
tests, compilation, private composition or worker edits were performed. Only
this lead-owned review report was written.

## Exact integration

Each integrated cherry-pick's complete `git show --format= --binary` patch has
the same SHA-256 as its reviewed donor:

| Change | Donor | Integrated commit | Patch SHA-256 |
|---|---|---|---|
| Capture A | `459e56bf896a29d854c5d250ce8632d7e2564427` | `3047be2d8a5f78663681b896e699434a7f42f51f` | `741e95668fd79ca316c8f8a064ea73202fe1c2f3c2cac2a0ba84d16bfed511fa` |
| Exact-source import facts | `89975411d65e42aae5baa2bb92276ad5f9fabf1a` | `033cd731f6d9a854143076a8bd13125d61101f92` | `ae6be799ffe238be3a5e86e9ad2be2881363d22b95a7a0f6558e343fc873c47c` |
| Fixed capture supervisor adapter | `f82e451743086fc4ec45cda044577e7b587c57c1` | `41135a507d8a00c4cbe83ad51b4fdde8c7c2671f` | `c36c8873c7b476a96ca4f2359c0db1dd85cc37b0d199d672b4088054aac68b41` |

These three commits account for the 19 donor files. The final commit adds only
`notes/reviews/native_capture_integration_branch_20261111.md` and changes the
one branch comparison in `scripts/adhoc/compose_native_u3m_20261109.py:92–95`
to admit the exact new branch alongside `base.BRANCH` (#5856). It adds no
arbitrary branch parameter. Exact HEAD, committed/clean helper, physical source
path, merge ancestry, packet and protected-preimage checks remain unchanged.

The original branch `codex/native-u1u3-combined-20261108` still resolves to the
baseline `458887766effe38207a77fea2d8033f1f3e1c7f3`.

## Protected preimages

There is no baseline-to-final diff in these four files; their current working
tree SHA-256 values match the retained composer preimages:

| File | SHA-256 |
|---|---|
| `src/data_sheets_schema/shared_generation.py` | `94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d` |
| `src/data_sheets_schema/api_runner.py` | `b109cb918a3079a384937ccfad7ab9b195a55713a355f11f848da98fab59596a` |
| `src/download/prompts/canonical_hashes.yaml` | `39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584` |
| `tests/utils/run_spec_boundary_contracts.json` | `a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72` |

## Branch and validation boundary

The approved sparse preparer
`codex-native-wp1-preparation-20261111/scripts/adhoc/prepare_native_wp1_canary_20261111.py`
loads the M composer and invokes its `require_source` at lines 86–93 and 249.
It builds its own private tree and takes the adapter's current `REQUIRED_FILES`
roster at lines 265–269. The historical base composer's `compose` branch gate
is not called by that sparse path. M's cleanup entry also uses the corrected
`require_source`.

**Do not generalize this clearance to generic M `setup`.** That separate route
still calls `base.compose` (`compose_native_u3m_20261109.py:273–275`), whose
historical gate still requires `base.BRANCH`. Retaining that historical behavior
is consistent with this narrow change and the approved sparse route.

The capture-specific source review and adapter review remain separately recorded
in `handoffs/capture-final-review-459e56bf.md` and
`reviews/capture_adapter_final_review.md`. The lead subsequently reported a
standalone genuine-node pass at 188.04 seconds, completed before the worker stop;
that artifact was not independently inspected in this integration pass. It does
not replace validation of the newly combined source, private composition and
supervisor contract.

The next evidence remains the owner's approved same-manifest comparison canary,
followed only if certified by the one fixed capture-recheck invocation and its
owned cleanup review. This source disposition is not a timing, freshness,
generation or native-acceptance claim and does not assign a runtime slot.

## Smallest next functional check after capture passes

Recommendation only, requiring a separate lead release after the capture result:
run **one existing `cpu-monitoring`** invocation through
`native_wp1_validation_20261110.py`, selecting its fixed
`tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic` node
and unchanged 900-second cap. Reuse the same frozen source, composition,
contract, interpreter and certified same-manifest equivalence canary, with a
fresh diagnostic output label. No legacy comparison arm, new profiler,
implementation change or repeated matched pair is needed for this question.

This diagnostic executes genuine `make_case` and `synthetic_launch`, then
interrupts at the exact attempt-directory `mkdir` before its effect
(`test_native_u3k_profile.py:208–254`). Therefore it can establish that the
**reservation boundary was reached within 210 seconds**, not that a reservation
or generation actually completed. The real guard's `before_reservation` check
runs just before that boundary, after the late authority checks
(`native_execution_orchestration.py:369–387`;
`native_subscription_guard_v2.py:439–447`).

For the resulting output directory
`scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-<label>`, inspect:

- `phase-metrics/<worker-pid>-diagnostic.json`: require
  `outcome: reached_reservation_without_effect`, non-null
  `reservation_boundary`, and a finite, nonnegative
  `capture_to_reservation_wall_seconds <= 210`. Check that subtraction directly
  against `capture_timestamp` and `reservation_boundary.utc`, and retain the
  unchanged `capture_age_limit_seconds: 300` and `capture_margin_seconds: 90`.
  Require `attempt_exists` and `evidence_exists` false; profile stability
  `stable`/`restored` true; `profile_hook_restored` true; no forbidden observer
  calls, open call rows or open thread stacks.
- `phase-metrics/<worker-pid>-measurement.json`: verify the exact node, worker,
  `control` mode, closed call rows and returned launch-phase
  `accept_saved_capture` / `freshness_before_reservation` checks. Inspect the
  full chronology, not an earlier preflight success. Its
  `observed_reservation_windows` may be empty by design: that list requires a
  successful return from the original `Path.mkdir`, which this diagnostic
  deliberately prevents (`u3k_metrics_plugin_20261109.py:279–305`).
- `pytest.xml`, `outcome.json`, `wp1-harness.json`, the sibling `.outer.json`
  and `.supervisor.json`, plus existing sandbox/origin witnesses: require the
  fixed single testcase and exact source/manifest/interpreter identities,
  normal return, certified cleanup and no timeout, interruption, forced cleanup,
  unresolved errors or observed survivors. Check the final private-config
  restoration witness separately after the permitted sequence finishes.

**A pytest pass alone is insufficient.** The test deliberately accepts a genuine
stale/margin refusal as a recorded diagnostic outcome
(`test_native_u3k_profile.py:255–260`). `genuine_refusal`, a missing boundary,
or a boundary later than 210 seconds leaves the functional target unmet.
Conversely, even an in-window boundary must retain
`measurement_class: unqualified_contended_cpu_diagnostic`,
`host_qualified: false`, `wall_time_freshness_qualified: false` and
`accepted_quiet_host_timing: false`. These are unconditional for this kind
(`native_wp1_validation_20261110.py:307–309`), not freshness-outcome flags.
`require_accepted_measurement` must still reject it. No quiet-host benchmark or
native-acceptance conclusion follows.

### Configuration sequencing

The existing capture plan says to restore private configuration immediately
after capture completion/failure and then stop. For the proposed follow-up,
the lead should explicitly amend that sequencing **before cleanup**, rather
than have the owner infer an extension: after a successful capture and certified
retirement of all owned processes, briefly retain only the manifest-pinned
configured private Git file while the lead reviews the result. If the lead
separately releases the diagnostic, run it against that same composition and
restore once afterward. A failed/uncertified capture, diagnostic failure or
decision not to release the next step ends with the existing restoration and stop.
Holding configuration does not retain a live worker or extend any invocation cap.

This avoids a restoration/reactivation cycle. M cleanup requires the exact
configured hash, refuses an existing restoration record, restores the original
bytes/mode and exclusively writes `config-restored.json`
(`compose_native_u3m_20261109.py:322–354`). The fresh preparation paths are also
exclusive. The existing separate `native_wp1_private_config_20261111.py` is
hard-pinned to historical source/composition `3cc113e2606c`; it is not a reusable
reactivation command for `382f0dfd1ce8`. No rearm machinery, overwritten evidence
or artificial source change is recommended. This review does not direct the
runtime owner to change the currently authorized sequence.
