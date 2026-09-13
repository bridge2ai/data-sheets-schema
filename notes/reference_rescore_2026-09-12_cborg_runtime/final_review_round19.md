# Independent final review — round 19

Reviewed completed-measurement commit `5f14512b70c1be785781878dfd8bcdf854ea0231`.

# Codex Adversarial Review

Target: branch diff against 96baf775b998a44478618a3e5e00fcd090b7beaf
Verdict: needs-attention

Block on a reproducible reporting regression. Committed measurement and v9 evidence otherwise reconciled offline. HEAD remains unchanged; provider charges were not independently verified.

Findings:
- [medium] [P2] Preserve qualifications through the public report command (scripts/reference_rescore_cborg.py:161-163)
  The `report` action calls the raw reporter instead of the qualified completion renderer. An in-memory replay against committed inputs reproduced replacement of runtime `results.json` and `results.md`, removing all seven qualification banners and the corresponding metadata—including unknown costs, execution boundaries, narrative qualifications and timestamp bindings—while preserving the 56 scores. The command returns success, leaving apparently complete results without their required limitations and inconsistent with the other reports. This command remains documented in notes/cborg_canaries_2026-09-12/plan.md:42.
  Recommendation: Route this action through the qualified completion renderer, or refuse it with guidance to that renderer. Add an offline regression verifying that the public report command preserves all qualifications.

Next steps:
- Fix the report entrypoint and verify qualification preservation before shipping.


## Disposition

The supported P2 is tracked in [#1356](https://github.com/bridge2ai/data-sheets-schema/issues/1356). The public report command now calls the qualified completion renderer; missing or invalid qualifications fail without replacing existing reports. The original adapter and scheduler are archived under their measured hashes, with unchanged manifest, registrations, receipts, outputs and prior evaluations. The completed condition refuses new measurement launches. This was a post-measurement reporting repair, with no new model calls.

Round 19 remains a blocked verdict. A separate independent review must inspect the repaired commit before merge. See [the preservation record](report_dispatch_preservation_1356.json) and [validation](report_dispatch_validation_1356.md).
