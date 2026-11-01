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

## Round 3: fail-closed ownership and restored controls

Every regular file or symlink starting with `P_` or `.P_` is a candidate in
metadata, its immediate `intermediate/`, and the selected output directories.
There is no list of known writers. Only positive per-file attribution to a
different guarded identity excludes a candidate. A guarded `P_X` or
`VOICE_PEDIATRIC` can therefore share a label with `P` or `VOICE`, respectively.
An unguarded or ambiguous `P_reconcile_full.yaml` is refused; that may be an
ordinary `P_reconcile` run or P's reconcile snapshot. This false refusal is an
accepted consequence: use a new label. Phase names never decide ownership.
Likewise, guarded `P` history alone does not own an unattributed `P_X` file:
that broader prefix is ambiguous for selected `P_X`. A per-file identity or
path/hash binding can still establish foreign ownership.
The sibling tests now initialize actual guarded history; arbitrary sibling
filenames and an invalid journal no longer suffice to exclude evidence.

The verifier uses the same inventory, including dot temporaries, within its
unchanged **generic_v6 API** scope. Provenance's historical intermediate
fallback narrows the inventory to `intermediate/`; its generation-bound index
remains authoritative when present. Shared no-resume uses the full inventory.
Execution residue checks additionally distinguish their own freshly created
coordination locks: only exclusive creation followed by a currently held lock
with the same canonical path/inode/mtime and zero bytes qualifies. Directory
aliases resolve to that canonical path; a symlink lock file still refuses. The complete inventory
and verifier still include those locks. Pre-existing, released, edited or
replaced locks are never excused by this startup scope distinction. A new
identity sharing old unattributed sidecar locks may therefore require a new
output directory, even when another identity's provenance is guarded.

The completeness test drives plain, shared v1/v2, receipt completion,
readdress, removal repair, typed audit, report regate and after-repair paths
with synthetic replies. It discovers actual writer output, including atomic
temporaries, then tests each artifact alone in both resume modes. Separate
controls drive context admission/refusal/collisions and incomplete completion.
The retired midnight `[completed=True, journal=False]` and reasoning
`[portable=True]` cases now have explicit zero-call, unchanged-tree refusal
replacements. A separate guarded index-publication interruption control
preserves the original recovery coverage without permitting legacy recovery.

`test_public_execute_refuses_existing_unowned_state_before_lock[unknown]`
now expects the D69 inspection-only refusal before shared registration's
older ownership diagnostic. It retains zero-call/zero-lock assertions and
now checks the whole tree, including directory and file metadata. Foreign
guarded-owner and already-spent shared-run diagnostics stay unchanged.

The broad validation found ten more fixture/expectation interactions with the
complete inventory. Their changes retain the original downstream checks:

- The intermediate-prefix sibling fixture now has a guarded journal before
  its snapshots appear; the flat-label completed fixture binds its report as
  well as its full/core outputs.
- The D55 fresh-launch stub initializes accounting while its new locks are
  held, as the real executor does, instead of leaving only released locks.
- The three predecessor-activation cases and the post-publication activation
  case bind their completed predecessor's four lock paths explicitly. Their
  interruption, damage and recovery assertions remain intact.
- The concurrency test expects the earlier inspection-only refusal for an
  unattributed foreign label and checks the whole tree. The two split/flat
  cases retain direct physical-lock exclusion in both directions, then check
  that public execution refuses pre-existing sidecars without writes. Their
  meta-test stubs use the same expected refusal messages.

The ordinary shard also exposed eight `test_api_batch_cost.py` nodes whose
mocked executor bypassed the run guard while their setup left journal-less
accounting. The three pending-call cases (also inherited by
`ApiBatchSuccessGapsTest`) now use real guarded ledger writes. The two unkeyed
row tests retain their exact cost assertions on a guarded generation displaying
legacy-shaped rows; the zero-cost case is renamed to state that scope. A new
journal-less legacy-label case instead requires refusal, no batch lock, no
dispatch and an unchanged tree. No guard is mocked or relaxed.

After main's test additions changed the shard assignment, the ordinary shard
holding this file exposed fifteen further fixture interactions. The selected
shape-repair control in `test_shared_generation_scope_context.py` initializes
guarded accounting before writing its full-record fixture. In
`test_shared_generation_resources.py`, the twelve public copied-resource
parameters and two public imported-schema-root parameters initialize guarded
accounting before creating their authority/lock hardlinks. Their exact repair
request, alias-refusal, trapped-writer and unchanged-byte assertions remain.
This setup exercises those downstream guards without bypassing D69's earlier
refusal of unguarded output or lock residue.
