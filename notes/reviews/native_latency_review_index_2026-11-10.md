# Native latency assessment and review trail

The owner requested a saved assessment of development latency, independent
research and an implementation plan, followed by lead review. This directory
preserves that sequence. Plan acceptance is not implementation acceptance.

- [Historical ETA evidence](generation_eta_2026-11-10/README.md): the
  timestamp audit (`timestamps.json`, `timestamps.tsv`) and runtime provenance
  summary (`../historical_generation_runtime_20261110.json`).
- [Saved assessment](native_development_latency_2026-11-10.md): the requested
  explanation of native adapter latency, synthetic tests, CI and CHORUS scope.
  Preserved byte-for-byte (`c0164a3d41ad85112adb1ecb3f6d918580a2eb91ad86ca0d00619be0b594bbbd`)
  as a workstation snapshot; its inline `/Users/marcin/...` evidence links point
  to local sibling `d4d-executions/` paths outside this repository (#5740).
- [Research assignment](agy4_native_latency_assignment_2026-11-10.md).
- [Plan v1](native_latency_implementation_plan_2026-11-10.md): rejected; consult
  the [lead review](native_latency_plan_lead_review_2026-11-10.md). Findings
  NL-1 through NL-8 are recorded as issues 5713 through 5720.
- [Plan v2](native_latency_implementation_plan_2026-11-10_v2.md): superseded;
  the [second lead review](native_latency_plan_v2_lead_review_2026-11-10.md)
  required NL-9 through NL-11 corrections, issues 5721 through 5723.
- [Plan v3](native_latency_implementation_plan_2026-11-10_v3.md): current
  planning direction. The [v3 lead review](native_latency_plan_v3_lead_review_2026-11-10.md)
  accepts the bounded corrections. Native Codex finishes and reports U3-M
  before the next diagnostic is assigned. Historical cohort counts must be
  reconciled with the final U3-M collection.
- [Prepared WP1 diagnostic handoff](codex_native_wp1_assignment_2026-11-10.md):
  prepared and undispatched until the lead reviews the final U3-M report.
- [Worker coordination](worker_dispatch_2026-11-10.md) and
  [read-only monitoring helper](../../scripts/adhoc/monitor_worker_terminals_20261110.applescript):
  terminal identities, dispatches, native scheduling amendment and active-turn
  monitoring limits.

Historical plans remain unchanged as review evidence. Their rejected claims
and proposed speedups are not current conclusions. No document in this review
trail grants merge, release, protected-packet or live generation approval.
