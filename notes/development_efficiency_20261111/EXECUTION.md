# Development-efficiency implementation, resumed 2026-11-11 UTC

User authorized completing the unfinished native optimization and addressing CI/development feedback time. Continue the existing reviewed native latency plan v3; this record tracks execution rather than proposing another framework.

Base main: 7233f193ad102a8488b31ec7333662c8fefaa996. Native source starts at 5f4a8e211826fe7f83ec51e6262d750687216aba in its existing owned branch. PR5808 is open and all CI checks passed; it stays a separate readiness slice.

| Unit | Owner | Deliverable / initial state |
| --- | --- | --- |
| E1 | Existing native Codex session | Close observer/cleanup correctness prerequisites, run genuine equivalence canary, then matched observer arms; proceed to measured redundant-work fixes and gated acceptance. First source preparation; runtime serialized by lead. |
| E2 | agy1 | Refresh complete ordinary-shard weights from run42916359440, preserving coverage, counts and dedicated lanes; validate assignment and produce measured provenance. |
| E3 | agy2 | Read-only source assessment of one smallest redundant-work fix on native source, preserving fresh validation/refusal semantics; hand exact candidate to native owner. |
| Review | agy3/agy4 and independent Codex reviewers | Read-only adversarial reviews of concrete changes; every finding gets an issue or existing issue association before fixes. |
| Lead | Codex lead | Coordinate worker/runtime ownership, inspect saved side effects, integrate compatible main-line work, open PRs and monitor CI. |

Measured CI baseline: run42916359440 took36m37s; all18 test jobs started within2–3s, ordinary shard5 test step36m00s versus shard4 20m13s. Bulk weights predate the merged BC1 speedups. This supports recalibration, not an advance claim of savings.

Initial host snapshot: approximately30GiB free; load14.82 on10logicalCPUs and several foreign busy processes. This is not a qualified quiet window. Do not pause system services or unrelated jobs, change scientific/native freshness limits, weaken validation, or call models/providers. Native timing qualification uses the existing protocol and records actual evidence; ordinary correctness checks need not be mislabeled timing experiments.

No new environments or full corpus copies. Branch before edits; helpers stay under scripts/adhoc. Exactly one tiny canary before broader affected checks; stop failed prerequisites and retain outputs. Preserve protected-file packet boundaries; prepare exact necessary changes for lead review instead of silently applying old pending approvals. Merge remains subject to the user's per-PR rule. Deferred schema/Core/RO-Crate work remains outside this task.
