# Expansion workload and cost planning — 2026-09-13

This is a planning draft, not a launch manifest. The first CHORUS API canary
failed validation and is excluded. Its five settled requests cost an estimated
$3.291465, leaving $196.708535 of the additional allocation. No further paid
job is eligible until the defects are fixed and a distinct retry is registered
and reviewed with that spending carried forward.

| Work | Proposed count | Treatment |
|---|---:|---|
| Bridge2AI full generations | 30 | Five datasets × three replicates × API/agentic. CHORUS rep1 canaries may count if unchanged. |
| External full generations | 2 | Kids First through both runtimes. |
| Derived cores | 32 | Deterministic; no separate generation call. |
| Study semantic primary ratings | 120 | Sixty full/core records × two rubrics. |
| Study semantic additional repeat ratings | 80 | Rep1 of five datasets × two runtimes × two variants × two rubrics × two additional ratings. |
| External semantic ratings including repeats | 24 | Four full/core records × two rubrics × three ratings; proposed external canary panel. |
| Direct API rubric canary ratings | 16 | Eight generation-canary full/core records × two rubrics; sequential first-contract acceptance required. |
| Field-oriented agent canary ratings | 16 | Same eight records × two rubric instruments, separate from semantic totals. |
| Presence, schema, pair, provenance, receipts, snippets, report checks | All eligible records | Offline checks with pinned instrument identities. |
| Grounding, fitness and subtype model judgments | To enumerate from accepted records | Each scored leaf has its own request count; do not hide the calls inside one nominal score. Reuse requires identical input and complete instrument identities. |
| Record/source review and historical adjudication | To enumerate | Current-record review and disputed historical judgments stay separate. |

The $200 additional budget remains the binding limit, with a cumulative $5 ceiling for each generation or evaluation attempt. At the cap, the 32 generation attempts alone reserve up to $160. The proposed rubric matrix adds 256 sessions before fitness/grounding and adjudication. These cap ceilings are not cost estimates and do not assert that the whole matrix is funded.

Historical context: the completed reference rescore has a known terminal CLI subtotal of $161.39939450 across 63 sessions, with 56 accepted ratings and two interrupted sessions still unpriced. Dividing that subtotal by accepted ratings allocates about $2.88 per accepted rating, including known failed-session costs; it is not a measured per-rating price or a complete invoice. Applying that allocation only as a planning scenario puts the 200 study semantic ratings at about $576.43, or about $645.60 including the proposed 24 external semantic ratings. Full/core size differences and the new transport controls make this an uncertain extrapolation.

One historical CHORUS generation cost $3.30811950 by catalogue-based usage accounting. Multiplying one such example by 32 gives $105.86, not a cohort forecast: larger source bundles, different runtimes, output lengths and repair attempts can differ substantially.

Run the reviewed canaries within the existing cap, measure actual request usage, then fix the job-level expansion manifest and revised projection. Do not silently drop a rubric, runtime, dataset, variant or repeat to fit the cap, and do not exceed the authorized budget. Any scope or budget choice needed for expansion must be explicit after these measurements.
