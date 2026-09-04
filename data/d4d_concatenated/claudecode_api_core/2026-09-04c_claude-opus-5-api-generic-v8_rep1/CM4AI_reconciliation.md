# Phase 4 Reconciliation Report — CM4AI

## Scope

Phase 3 audited the full record against the declared bundle and returned seven findings: one medium-severity, six low-severity. No high-severity defects were reported. This phase applied the audit's one explicit repair recommendation, made one clarifying edit prompted by the medium-severity finding, added one derivation note prompted by the audit's confirmation of `total_file_count`, and left every other finding as-is with reasons recorded below. The core record was kept in projection alignment with the full record throughout.

## What the audit found

1. **`data_governance.notes` — medium.** The Data Access Committee clause is a forward-looking statement from the CM4AI preprint sitting beside a slot that otherwise describes current governance. The audit judged it borderline and asked that its tense be preserved and its provenance stay clear.
2. **`external_resources[1].archival` — low.** `archival: true` was asserted for the Nature 2025 publication with no passage in the bundle stating that the resource is archived or persistence-guaranteed. The audit recommended removal.
3. **`subpopulations` — low.** Both entries describe donors of the source cell lines rather than subpopulations among data instances. Each already carries an explicit `source_caveats` disclaiming exactly this. Flagged for visibility only.
4. **`ethical_reviews[0].contact_person.id` — low.** The `mailto:` URI was reviewed and found conforming: no personal-identifier prefix value is attested for Vardit Ravitsky in this role, so the resolvable URI is the permitted fallback. No repair required.
5. **`ethical_reviews[0]` — low.** Two ethics contacts are named in prose but only one populates `contact_person`. Since `contact_person` has range `Person` rather than `Person[]`, this is the schema-permitted shape. No repair required.
6. **File-size notes — low.** File sizes are held in `notes` rather than the integer `bytes` slot, because the unit base is unstated in the source. Audit confirmed this as correct restraint. No repair required.
7. **`total_file_count` — low.** The value 10 is both explicitly stated by the release page and equal to the sum of the six collections' `file_count` values, so it is not a derived-figure defect. No repair required.

## Changes made

### Full record

**`external_resources[1].archival` — removed.** Comparing the two full records, the original entry for the Nature 2025 publication ends with `archival: true` following the `description`; the reconciled entry ends with the `description` and carries no `archival` key. This applies the audit's single explicit repair. The bundle's Nature source is a journal article page; nothing in it states that the resource is archived or that persistence is guaranteed, and the boolean was an inference from the resource's kind rather than a fact the documents supply.

**`data_governance.notes` — changed.** The original reads: "The CM4AI project preprint states that a Data Access Committee will supervise ethical matters related to dataset distribution and potential dual licensing for commercial use; the release record names a single data governance contact." The reconciled text inserts an explicit tense marker: "…for commercial use; this is a statement of intent in the preprint rather than a description of current practice. The release record names a single data governance contact." The future tense the preprint used is preserved unchanged; the addition makes the plan/practice distinction explicit rather than relying on the reader to infer it from "will supervise."

**`source_caveats` — changed.** A sentence was added recording that `total_file_count` is the release page's enumerated figure and that it coincides with the sum of the six collections' `file_count` values: "File count: `total_file_count` records the ten files the release page enumerates; this equals the sum of the six file_collections' file_count values (2 + 2 + 3 + 1 + 1 + 1)." The value itself is unchanged and remains source-stated rather than derived; the note makes the coincidence with the arithmetic visible so a reader does not need to recompute it to confirm the collections are complete.

### Core record

**`external_resources[1].archival` — removed.** The core record's Nature entry originally carried `archival: true`; the reconciled core entry does not. Projection alignment with the full record.

**`data_governance.notes` — changed.** The same tense-marking sentence was inserted, matching the full record.

**`source_caveats` — changed.** The same file-count sentence was inserted, matching the full record.

**Header — changed.** `# Phase 4 reconciliation: completed` is present in the reconciled core header, as required once this phase has actually run.

## What was left as-is

**`subpopulations` (both entries, both records) — retained.** Finding 3 is a genuine tension: the slot description asks for demographic or other groups within the dataset, and these two entries describe the donors of the source cell lines. But the entries are the only donor-demographic evidence the bundle supplies, each already carries a `source_caveats` stating in plain terms that it "describes the donor of the cell line used to generate the data… and not a subpopulation of data instances identified within the release," and the audit itself judged the mismatch acceptable with the caveat retained. Removing them would delete attested, caveated evidence; moving them elsewhere would put donor demographics in a slot that fits them worse. Both entries and both caveats are unchanged in both records.

**`ethical_reviews[0].contact_person.id` — retained.** Finding 4 explicitly concluded "Noted as conforming; no repair required." The bundle gives Vardit Ravitsky's email in this role but no personal registry identifier for her in it, so the `mailto:` URI is the permitted fallback under the identifier rules. Unchanged in both records.

**`ethical_reviews[0]` (single `contact_person` for two named contacts) — retained.** Finding 5 concluded "this is the schema-permitted shape… No repair required." The schema digest lists `contact_person` on `EthicalReview` with range `Person`, singular, not `Person[]`. Jean-Christophe Bélisle-Pipon's name and address are carried in `review_details`, which is where a second contact can go given that range. Unchanged in both records.

**File-size notes — retained.** Finding 6 confirmed this as correct restraint. The release reports sizes only as "113.3 KB", "3.8 GB" and similar, with no statement of whether the base is 1000 or 1024, so no integer byte value can be written without inventing precision. The record-level `source_caveats` already explains this. The values are unchanged. The two records hold them at different paths: in the full record each sits on a `File` under `file_collections[*].resources[*].notes`; in the core record, where the projection flattens collections and their files into a single `distributions` list, each sits on the corresponding `distributions[*].notes`. The disposition table below records the two paths separately for that reason.

**`total_file_count: 10` — retained.** Finding 7 confirmed the value is source-stated and not a derived figure. It remains in the full record with the value unchanged; only the explanatory caveat sentence was added. This slot does not appear in the core record, which is a projection difference rather than a reconciliation change, so its disposition row names the full record only.

**`total_size_bytes` — remained omitted (both records).** Not among the audit's findings, but noted here because the audit's summary singled it out as correctly restrained. It is absent from both records before and after.

## Outcome

Two substantive edits across both records (one removal, one clarifying rewrite), plus one caveat addition, plus the required core header line. Five audit findings were closed with no change, four of them on the audit's own conclusion that no repair was required. The core record remains a projection of the full record: every slot the core carries holds the same value the full record holds, with the file-level entries reorganized into `distributions` as that schema requires.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `external_resources[1].archival` | removed | both | Bundle states nothing about archival status or persistence guarantee for the Nature 2025 publication; the boolean was inferred from the resource being a journal article. Audit's one explicit repair recommendation. |
| `data_governance.notes` | changed | both | Added an explicit marker that the Data Access Committee clause is a preprint statement of intent rather than current practice; the preprint's future tense is preserved unchanged. |
| `source_caveats` | changed | both | Added a note recording that `total_file_count` is the release page's enumerated figure and coincides with the sum of the six collections' `file_count` values (2+2+3+1+1+1). |
| `total_file_count` | retained | full | Explicitly stated by the release page ("1 to 10 of 10 Files") and consistent with the collections' sum; not a derived-figure defect per audit finding 7. Not carried by the core schema. |
| `subpopulations[0]` | retained | both | Donor demographics rather than instance subpopulations, but the only such evidence the bundle supplies and already disclaimed in its own `source_caveats`; audit judged acceptable as written. |
| `subpopulations[1]` | retained | both | Same as above: KOLF2.1J donor description, caveated in place, retained on the audit's assessment. |
| `ethical_reviews[0].contact_person.id` | retained | both | `mailto:` URI is the permitted fallback where no personal registry identifier is attested for this person in this role; audit found it conforming. |
| `ethical_reviews[0].review_details` | retained | both | Carries the second ethics contact in prose because `contact_person` has range `Person`, not `Person[]`; audit found this the schema-permitted shape. |
| `file_collections[0].resources[0].notes` | retained | full | Size held in prose because the source's unit base is unstated and `bytes` is declared integer; audit confirmed as correct restraint. Same reasoning applies to the other nine file `notes` values in this record. |
| `distributions[1].notes` | retained | core | The core-record counterpart of the same value, carried on the flattened `distributions` entry rather than on a nested `File`; retained for the same reason. |