# Authentic pre-D41 controls for D68/D69

The i1/i2 and C1–C8 plain `before/` trees are exact captures emitted by
`f8c5ac73caba610d40c49aaceddb31ead3590a72`, retained by the independent reviewer
under `review-d41-legacy-20261030/run1/evidence/captures/`. Each invocation and
SHA-256/size manifest is retained. `import_d68_fixtures_20261030.py` verifies both
copies. No embedded path, timestamp, hash or generation ID was rewritten.
Tests relocate only the invocation and pass an explicit root mapping to the
read-only verifier. Neither the original paths nor the review workspace are
accessed by CI. The f8 generator remains pinned under `scripts/adhoc/`, outside
CI; its i1/i2 selectors reproduce the reviewer's extra cases.

The additional `split` before-tree was generated on 2026-10-31 by
`scripts/adhoc/capture_d68_split_layout_20261031.py`, using the same pinned f8
checkout's real runner and offline FakeClient. Its ordinary `out_dir=None`
layout puts full output under `custom/synthetic` and core output/provenance
under `custom_core/synthetic`. The canary completed four fake calls, persisted
20 files and recorded f8 itself as `repo.commit`; no captured provenance bytes
were rewritten. This establishes pre-D41 code ancestry despite the later
capture timestamp. The original generator report remains under
`.d68-validation/split-layout-f8/generation.json`. CI reads the committed plain
capture, manifest and invocation, without the generator or old checkout.

| Original case | Disposition under D68/D69 |
|---|---|
| C1 unrelated archive | Rewritten against authentic c1; entire tree unchanged on refusal. |
| C2 malformed ledger | Rewritten against authentic c2; no archival or spending. |
| C3 missing ledger | Rewritten against authentic c3; fresh restart now refuses. |
| C4 interrupted index activation | Rewritten against authentic call 3; prepared journal-less ledger never resumes. |
| C5 missing input identity | Rewritten against exact f8 call-1 before-tree; earlier no-spend refusal replaces the old diagnostic. The captured historical test hand-wrote this progress, so it is not production-emitted evidence. |
| C6 unreadable index | Rewritten against exact f8 call-1 before-tree; both resume modes refuse, preserving every byte. The captured historical test hand-wrote this index, so it is not production-emitted evidence. |
| C7 portable completed run | Old current-ledger-deletion parameter retired: it tested guarded damage, not pre-D41 history. Authentic c7 now verifies read-only and refuses execution. Current guarded damage remains covered by the D41 suites. |
| C8 malformed prior reasoning | Old portable/current-ledger-deletion parameter retired for the same age conflation. Authentic c8 now refuses without changes. The intact current-journal restart parameter remains. |

i1 is completed with its original ledger; i2 is interrupted with its original
ledger. Both refuse execution; i1 additionally passes read-only verification.
Absence of a journal does not classify i2/C2/C4 as pre-D41 at runtime: without
a surviving provenance commit or timestamp their runtime age is unestablished.
Their fixture origin is independently established by the pinned capture source.

C5/C6 come from the committed design evidence archive, imported one case at a
time with the same manifest-checking helper. CI reads only the resulting plain
trees. Their source archive SHA-256 is
`314ad171427e2a42244fe963874c1082137ea99228bc40d6f12809058a36de6a`.

No recovery authorization or import is implemented (review item 5 is superseded
by the owner's Option 3). Under D73(b), the verifier covers **generic_v6 API
records with a structured request spec only**. Other API conditions, including
v7/v8, and agentic records are unsupported. It does not currently verify the
committed historical campaign records; the lead will file the scope extension.
Any rerun must use an ordinary new label/registration.

## D73 decisions and further accepted flips

D73(a) makes `age unestablished` eligible and reported. Positive post-D41
ancestry still makes a missing integrity block ineligible. Age is informational
in canary results and registered-evaluation output, outside quality rows and
the evaluation plan hash. The quality-measurement test now also asserts that unknown age is eligible and
reported without adding a measurement.

The owner accepted these four further D68/D69 flips in D73(c):

- `test_foreign_flat_label_provenance_does_not_masquerade_as_current_history`:
  a new label cannot overwrite unguarded flat-layout provenance; both guard
  entry points refuse, preserving the evidence.
- `test_a_legacy_continuation_adopts_rows_without_a_generation_before_its_boundary`:
  legacy adoption is now refused in both preparation modes; old charges stay
  readable and the tree is unchanged.
- `test_legacy_public_boundary_is_unchanged`, renamed
  `test_legacy_public_boundary_refuses_residue_before_any_write`: unowned partial
  output is refused before locks or execution in both resume modes.
- Explicit fresh restart over legacy residue is refused. The C1–C6 rows above
  name each authentic replacement, including the earlier C5 diagnostic.

The D70-only fixture additions in `test_method_resolution.py` (two timestamps),
`test_report_gate.py` (two timestamps), `test_duplicate_keys.py` (one timestamp)
and `test_registered_eval_runner.py` (one clean integrity block) are all
reverted. These fixtures again exercise unknown age; they no longer need
invented age/integrity evidence to reach their original assertions.

The retired C7 `[True-False]` and C8 `[True]` parameters are both among the
16 NF3-B / #5409 nodes. The complete node-by-node disposition, including
the preserved parser checks and the two repaired `metadata_dir` stubs, is in
`notes/reviews/d73_5212_review_followup_2026-10-31.md`.
