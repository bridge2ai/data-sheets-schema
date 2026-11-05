# W7-BC1-REPLAY-01: BC1 completed-replay fixture omits its launch monitor

2026-10-30. Local issue under the explicit offline/GitHub prohibition.
This is an intact-accounting fixture integration finding, not a request to alter
Claude's eight owner-held legacy missing/corrupt-ledger recovery cases.

Original packet `9c2fbad3c128a7601d4471e00d8eb973b60709bd` was tested in private
proposal-applied archive `b4932bfcb74a7deb2a9e9483a58f1903fd143f5e`.
The complete 30-module/four-shard selection recorded 713 passed, 1 failed,
2 optional historical-wire skips, and exact reconciliation of all 716 selected
occurrences. Source, hygiene, imported origins, mandatory OS network guard,
JUnit/exit agreement and occurrence accounting all passed. No evidence is
missing or overwritten.

Evidence beneath `d4d-executions/plans/reviews/wave7_resume_2026-10-30/`:

- `bc1-subset-repaired-01/outcome.json`: SHA-256
  `8507f6f23b2aaaa5dd0e0069dfa28ffb487d067e968ef1b4f5dd2fe124f29f1a`.
- `bc1-subset-repaired-01/shard-4/outcome.json`: SHA-256
  `24bd1ed38ff36bfb0d8cd6b2cfdfd9c5be4a6727ec799fcf265667f235f0cc8d`.
- `bc1-subset-repaired-01/shard-4/pytest.xml`: SHA-256
  `4d93e7c9caaa0cc0365d6c6f211cfd86b617f2cac14ea51765a02598eea8b127`.

The sole failure is
`tests/test_bc1_pipeline.py::test_public_bc1_pipeline_multiple_groups_final_and_completed_replay`
at line 117, its second `api.execute(replace(spec), ...)` call. The first full
execution and every preceding assertion passed: accepted BC1 state, all workers
and groups plus final integration, independently reconstructed assembly,
projected carry, expected phase/usage sequence, and provenance. The intact
completed replay then supplied no external checkpoint (`expected=None`).
`latch_journal.launch_record` correctly refused with “resume journal head:
expected=required from prior launch/monitor record”. This is not a failed
production replay with a valid caller checkpoint, or a missing/corrupt-ledger
counterfactual. There is no basis here to relax the production guard.

Original test-module SHA-256:
`ee9050f4e6bedcf860690704bbe815e7f9290cbfbb37ae4dd23e6df2c30e580e`.
The existing `tests/conftest.py` SHA-256 is
`7b1cc4f40c32277502bd3e9b9ad3024ae555e8027a05b94670087d14322d70c2`.
Its opt-in `journal_launch_monitor` fixture was introduced at
`4f20a300ddf33b7d7903bebe34ffd12b86f0b981`. It captures the checkpoint only
after a successful durable append, keys it by the exact journal path, and
supplies it to subsequent calls without learning trust from mutable ledger or
journal reads. Existing shared-generation and source-heading fixtures already
use it. The fixture implementation is not being changed.

Proposed bounded repair: opt this one BC1 test into `journal_launch_monitor`.
Preserve the completed replay's zero model/count-call, unchanged usage and
unchanged artifact assertions. Do not alter production source, protected
proposal, fixture implementation or any owner-held recovery policy. Independent
review and fresh-archive affected validation are pending. The failed suite
remains the original evidence at the original head.

Independent read-only review confirmed the failure's exact boundary and the
existing monitor's append-observation authority. It also independently checked
716 JUnit cases (713 pass, 1 fail, 2 optional skips), all four child exits and
proof flags, and all ten matching source snapshots. The implementation adds
only the fixture argument and its explanatory comment to this one test.
Fresh-archive canary, full collection and the complete affected pipeline module
will be checked on the descendant. The lead explicitly accepts this affected
replay plus the preserved earlier full-subset evidence; the old 716-case result
will not be relabeled as a full-green run at the new head.
