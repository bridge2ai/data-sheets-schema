# N2d independent instruction-delta review — 2026-10-25

Refs #4354. This reviews the complete offline r1 render at
`f0f980858506c60e769f54c5a85d58026568d4eb`, before the subsequent catalog dependency
guard fix. It does not certify a launch, native success, scientific equivalence,
human judgments, an empirical receipt floor or the 900-second acceptance gate.

The new comparison still has seven hunks, but its H6 has an additional API-only
report clarification. Both arms also contain the substantially revised R9 rule.
Neither fact was established by counting hunks. The conclusion remains that
current uniform rules match while complete instructions and stage exposure differ.

## Evidence and reproduction

Input directory: `/private/tmp/d4d-native-n2-parity-20261025-r1/`. Historical
comparison: `../d4d-executions/codex-n1-2026-10-23/evidence/`
`n1b-current-target-instruction-review.md`, which reviewed the old current-target
render at `9315de8125e9504336a18bed4affb34c7662e8d0`.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Current API25 instruction | 87577 | `2e8efbeb608959740cd80ecdcddee35e965928525fe4564046c68bb0d3314083` |
| Current native26 instruction | 131395 | `cc503fd057e73ccef748f3f3d4926011d4b7eb1738a6d68bca3160846d5d9241` |
| Current complete diff | 103909 | `00001a136c7277cbed96f56ed27aec0a543a0f4ff94c3b8a6c33fa3f2e2c8094` |
| Historical-to-current API diff | 10045 | `305bfe1ac460818260680281cd3becaa6c5ab7c2a21d5f0c60cd4dd7668f15a0` |
| Historical-to-current native diff | 106560 | `06d6c6624605ad4191403f9ef339d1f49043cd3b0fa27c84f335e3fb12df76f2` |
| Complete current R9, once per arm | 4433 | `2ae71e83e11a096764b63bc4037786d756d5e31523e3fe71701505b976eaf765` |
| Current uniform rules, surrounding whitespace trimmed | 25589 | `c5c5b36189ee163f5669d514955a20ce6345b02fc839a39221d05afe0f56d0ee` |

The read-only [comparison helper](../scripts/adhoc/native_n2_review_parity_deltas_20261025.py)
pins all seven instruction/diff inputs, parses every bash command fence with
`shlex` without executing commands, rejects duplicate JSON keys, decodes embedded
JSON and checks its declared byte hashes. It compares complete leaf values,
including paths, rather than normalizing them away. Its result supplements manual
reading of all textual hunks and the changed source assets.

```bash
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/native_n2_review_parity_deltas_20261025.py --evidence /private/tmp/d4d-native-n2-parity-20261025-r1 --output /private/tmp/d4d-native-n2-delta-review-20261025/complete
```

The command completed successfully without importing production code or invoking
providers, native tools, registration or GitHub. The output is
`/private/tmp/d4d-native-n2-delta-review-20261025/complete/structural_deltas.json`,
SHA256 `f41074d24d223704a0e40dbf7f93346a884a0f95be372bbc7fb6a202ec8a6e85`.
The helper refuses an existing output directory; use a fresh directory to repeat.
The preliminary parent-directory JSON is retained but superseded: its first parser
omitted the numbered `phase1_receipts` heading. The completed helper handles digits
and verifies that every bash fence was parsed. This is a utility verification,
not a rerun of the native acceptance tests.

## Every current API-to-native hunk

The categories below use **scientific** for factual/structural exposure and
evidence obligations, and **execution procedure** for delivery, orchestration,
identity and presentation. A mixed hunk remains mixed even when most bytes are
paths or commands.

| Hunk / diff line / header | Actual difference and disposition |
|---|---|
| H1 / 3 / `@@ -1,95 +1,40 @@` | **Scientific + execution procedure.** Replaces API factual/phase/no-tools boundary and full header with native pair generation, provenance and schema-only rules. Native later requires reading declared files; API receives supplied text/digest in phase requests. Current labels, dates and provider/model placeholders are fixture identity. The factual boundary and presentation remain different despite common source pins. |
| H2 / 136 / `@@ -481,7 +426,6 @@` | **Execution procedure, presentation only.** Removes one blank line before shared rules. Extracted uniform content is identical; this does not cover the rest of the instruction. |
| H3 / 144 / `@@ -522,152 +466,134 @@` | **Scientific + execution procedure.** Replaces API RETURN/execution metadata and protocol-7 batch/grammar prefix with relocated role review, native stages, receipt-v1 policy and attribution drafts. Original immutability, one consumed receipt answer, unsupported-candidate preservation, pending floor, ordered stage reads and bounded drafts remain explicit. Removed top-level batch text contains scientific duties as well as orchestration; later native raw policies/stage contracts do not establish equal operative emphasis. |
| H4 / 425 / `@@ -694,7 +620,7 @@` | **Execution procedure.** Changes authoring a complete audit to checking the helper-assembled aggregate and answering the current stage contract. Adjacent evidence element shapes remain the same. |
| H5 / 434 / `@@ -961,7 +887,7 @@` | **Execution procedure.** Changes adding `source_review` to an authored audit into its inclusion in the checked aggregate. Final-report claims/source-review duties remain. |
| H6 / 443 / `@@ -1048,130 +974,131 @@` | **Scientific + execution procedure.** Native permits pre-seal Phase1 receipt correction while preserving terminal Phase3/4 source failures. API source metadata projection, audit namespace/example and schema guidance become native captured context/vocabulary, file roles, full-schema reads, headers, receipt shape and command order. Role review relocates to H3. **New since N1b:** API's explicit flat-claims/status-matching paragraph is absent from native's report appendix. That is additional model-visible evidence/format guidance, not merely a moved paragraph. |
| H7 / 691 / `@@ -1256,50 +1183,108 @@` | **Scientific + execution procedure.** API receipt-v2 continuation and registration become native helper commands plus recorder metadata; native receipt-v1 duties are already in H3. Native full-schema/context/asset exposure remains scientific. Tool order, paths, raw answers, provenance ownership and hypothetical runtime bounds are procedure. Parsed recorder metadata must be considered, not discarded as shell boilerplate. |

H2/H4/H5 remain procedure-only; H1/H3/H6/H7 remain mixed. H6's new paragraph is
the reason the old seven-row ledger cannot be reused without amendment.

## Every historical-to-current hunk

| Arm / hunk header | Change and classification |
|---|---|
| API `@@ -62,7 +62,7 @@` | **Procedure:** historical run label replaced by explicit hypothetical render label. |
| API `@@ -79,7 +79,7 @@` | **Procedure:** historical CBORG provider header replaced by unauthenticated hypothetical provider. This is not a live route observation. |
| API `@@ -89,7 +89,7 @@` | **Procedure:** generation date becomes fixture date 2026-10-25. |
| API `@@ -373,31 +373,62 @@` | **Scientific:** revised R9 decision rule, detailed below; shared verbatim with current native. |
| API `@@ -1140,6 +1171,8 @@` | **Scientific + procedure:** explicit evidence-status/qualification guidance and flat final-report assertion shape, absent from the native initial instruction. |
| API `@@ -1269,4 +1302,4 @@` | **Procedure:** receipt registration ID becomes `OFFLINE-NOT-REGISTERED-receipt` with consequent serialized length/hash changes. Its limits, pending floor and runtime policy are unchanged. |
| Native `@@ -1,4 +1,4 @@` | **Procedure:** hypothetical run label changes. |
| Native `@@ -318,31 +318,62 @@` | **Scientific:** same revised R9 as API. |
| Native `@@ -967,7 +998,7 @@` | **Procedure/source identity:** vocabulary path moves to the current checkout. Its bytes, hash and raw vocabulary content are unchanged; no new context judgment is established. |
| Native `@@ -985,35 +1016,35 @@` | **Procedure:** all declared helper/model output paths relocate. Role roster and ownership are unchanged. |
| Native `@@ -1032,10 +1063,10 @@` | **Procedure/source identity:** schema path and fixture date change. Captured schema content hashes are unchanged. |
| Native `@@ -1169,91 +1200,91 @@` | **Scientific + procedure:** command arguments relocate, labels/IDs/date change, and recorder metadata binds the two revised scientific assets. Runtime limit-basis wording changes to explicit offline-fixture prose; actual bounds do not change. The structured comparison exposes all nested changes. |

### R9 is a scientific condition change relative to N1b

The old R9 was 2,213 bytes (SHA `debc8c4b...`); the new one is 4,433 bytes.
The old common uniform section was 23,369 bytes; the new one is 25,589 bytes.
The text now:

- Limits observable-fact enum derivation explicitly to `confidentiality_level`
  and `hipaa_compliant`; other enum slots remain under direct-category evidence.
- Distinguishes public licences/citation/download forms from registration,
  identity checks and signed/accepted dataset-specific conditions; differentiates
  review of each access request from a study's own collection ethics approval.
- Specifies review precedence, the least restrictive tier offering actual data
  from this dataset, exclusion of metadata/documentation/code/sample/synthetic-only
  tiers, and recording each tier's conditions and coverage in access-review prose.
- Distinguishes access conditions from data sensitivity and rejects tier names
  or external classification labels as receipts for the enum.
- Narrows HIPAA `not_applicable` to evidence of no human-participant data;
  supplies explicit HIPAA/Safe Harbor/Expert Determination evidence for
  `compliant`; no-PHI or unspecified de-identification alone supports neither.

These are claims about the changed generation instrument, not an independent
legal or scientific endorsement of that instrument. The selected generic-v10
and uniform-v2 assets also revise their introductory version/date descriptions.
Their hashes change consistently in the native descriptor and registration.
No other selected scientific asset hash changes in the parsed recorder metadata.

### New report guidance is asymmetric, but the native duty is not absent

`api_runner.evidence_phase_contract` adds the paragraph only for renderers 25/27
and report/report_regate (`api_runner.py`, near line 2377). Native render calls
the same function with renderer 26 (`native_shared_render.py`, near line 338),
so this clarification is not included. The native evidence-protocol projection
already requires the source/artifact assertion shapes, says `unstated` cannot
support a retained claim, warns against `fact` masking operational/prospective
scope, and requires status agreement for a supported claim (protocol-v7 near
lines 458–479). Therefore this is **different explicitness/presentation of
existing obligations**, not evidence that native is permitted contradictory
statuses or wrapped top-level assertions. Its effect on generation is unmeasured.
Accept it as a declared package difference or authorize a separately reviewed
alignment; do not silently change frozen historical prompts to claim parity.

## Embedded recorder and effective-stage limits

The completed helper parsed the same **17 command roles** in both native texts.
All **37 changed command tokens**, excluding separately decoded recorder JSON,
are relocated paths or run labels. Within recorder metadata it retained **74
changed leaves**: output/resource/schema/vocabulary paths; two revised prompt
asset hashes and their lengths; resulting descriptor/registration hashes;
hypothetical labels, IDs and date; and runtime limit-basis prose plus resulting
hashes/lengths. It found no changed numerical bounds, draft allowance, runtime
model/provider/effort, receipt floor or protocol version. The complete generation
context differs in exactly one leaf, the vocabulary identity path. Its scope
assertions, source policy and raw vocabulary comments remain identical.

That result compares declarations, not actual file reads, native authentication,
tool observations or execution. Toolchain resource path changes alone do not
prove every referenced resource's effective behavior is equivalent.

The existing stage-exposure distinction also remains visible in current source:
native `native_shared_stage._request` carries complete raw policies and an outer
owner schema/catalog; API typed construction/runtime retain the target S7 schema
projection. Top-level uniform/R9 equality does not equalize those requests,
conversation history, fresh-context workers, receipt transport, reconciliation
detail, computed report counts or repair allowances. This review has not rerun
stage execution or established equal model attention. Pending human applicability
and audit-recall judgments remain pending.

No production files or historical artifacts were edited for this review. The
next clean-source parity run must retain this r1 evidence and independently pin
the final source head; unchanged hunk count alone is not its acceptance criterion.
