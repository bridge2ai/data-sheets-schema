# Reconciliation Report — CHoRUS Datasheet

**Project:** CHORUS
**Label:** 2026-09-04f_claude-opus-5-api-generic-v8_rep1
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation against the Phase 3 audit

---

## 1. What the audit found

The Phase 3 audit returned thirteen findings, none critical: four medium and nine low. They group into five kinds of defect.

1. **Field-purpose errors in `distribution_formats`.** The single entry carried an access route (`"Controlled-access cloud enclave"`) in the `format` field, and collapsed the five per-modality formats the webinar's data-inventory table states (OMOP, OHNLP, DICOM, WFDB, EDF+ and Persyst) into one object.
2. **Absence statements sitting in fields that should answer their question.** `updates.frequency`, `splits[0].split_details`, `labeling_strategies[0].labeling_details` and `intended_uses[1].usage_notes` each ended in a clause reporting what the documents do *not* say.
3. **A tense/subject error.** `existing_uses[0].examples[1]` described the AIM-AHEAD cohort-2 curriculum — prospective in the source, with CFA release 2025-09-02, notice of award 2025-11-10 and program start 2025-11-17 — as a current use.
4. **An unsupported enum value.** `instances[1].data_substrate: B2AI_SUBSTRATE:37` (Relational Database) asserted a storage substrate the bundle never names.
5. **Hygiene and shape items.** A prose paragraph in the short-token `status` slot; inconsistent Creator modeling between the PI and the other six leadership-team entries; minted fragment identifiers on classes whose digest does not require `id` and which nothing in the record references; two multivalency questions (`MissingInfo.why_missing`, `HumanSubjectResearch.special_populations`); and one inference (`at_risk_populations.at_risk_groups_included`) left unqualified.

The audit also recorded three things it checked and found sound, which the reconciliation preserved unchanged: the 50,000 vs. 45K cohort-size conflict and the 7,642-admissions vs. 1000-images imaging conflict are both carried in `source_caveats` with the higher-ranked source preferred; the MIT License is kept out of a dataset `license` slot and confined to `license_and_use_terms` with a caveat that it is a statement about the code.

---

## 2. What was changed

### 2.1 `distribution_formats` — rebuilt as five entries (both records)

The original single object with `format: Controlled-access cloud enclave` is gone from both records. In its place are five objects, one per modality-standard pair the webinar states: `OMOP Common Data Model`, `OHNLP`, `DICOM`, `WFDB`, `EDF+ and Persyst`. The enclave, Azure and OHDSI-tool-stack material was not discarded — it now sits in the `notes` of the OMOP entry (and, for telemetry, in the WFDB entry's `notes`), where it describes the working environment rather than posing as a format. This addresses both medium findings against this slot at once: the `format` field now holds a format, and the multivalued slot now carries one object per distinct entity.

### 2.2 `existing_uses` — cohort-2 example removed, caveat added (both records)

`examples` now holds only the attested present-tense claim ("the datasets are being used for training activities and publications"). The cohort-2 coursework sentence was deleted from `examples`, and a new `source_caveats` on the same object records why: the program is prospective in the source, with the three dates the audit named, so its curriculum belongs in `intended_uses` — where it already appears as the third entry, unchanged.

### 2.3 Absence statements relocated to `source_caveats` (both records)

Four values were split, the attested claim staying in the answering field and the absence moving to a sibling `source_caveats`:

- `updates.frequency` was **removed entirely**. Its attested half (sites provide regular status updates) was folded into `updates.update_details`, and a new `updates.source_caveats` records that no release cadence or versioning policy is stated. The audit offered "keep only the attested part or omit"; omission was chosen because a site status-update rhythm is not a dataset release cadence, and putting it in `frequency` would answer a neighbouring question.
- `splits[0].split_details` now ends at the award abstract's statement; the planned-capability qualification and the absent size/availability moved to `splits[0].source_caveats`.
- `labeling_strategies[0].labeling_details` likewise; a new `source_caveats` carries the future-tense qualification and the absence of released labels.
- `intended_uses[1].usage_notes` — not itemized in the audit but the same defect — lost its trailing "the source documents do not report that this holdout set has been released", which is now `intended_uses[1].source_caveats`.

### 2.4 `instances[1].data_substrate` — removed (both records)

`B2AI_SUBSTRATE:37` is gone. The remaining substrate terms (`:11` DICOM, `:49` Waveform Data, `:43` Text) are each named or directly stated by the bundle and were retained.

### 2.5 `status` — reduced to a token (both records)

`status` now reads `partially released`. The two-sentence paragraph is not lost: the release-progress facts it restated are already carried by `description` and by `updates.update_details`, both unchanged.

### 2.6 `creators` — uniform shape (both records)

Every Creator entry now carries a `name`, including Eric Rosenthal's, which previously had none. The nested `principal_investigator` Person object was kept on that entry alone — the PI designation is attested only for him, by NIH RePORTER — and retains its minted `#person-eric-rosenthal` id, which the Person class requires. The other six entries are unchanged apart from the removal of their minted `id` keys (§2.7).

### 2.7 Minted identifiers removed from optional-`id` objects (both records)

Fragment ids were removed from every entry under `creators`, `funders`, `data_collectors`, `maintainers`, `intended_uses`, `existing_uses`, `instances`, `subpopulations`, `acquisition_methods`, `collection_mechanisms`, `sampling_strategies`, `preprocessing_strategies`, `cleaning_strategies`, `labeling_strategies`, `ethical_reviews` and `external_resources`. Nothing in either record pointed at any of them.

Two classes of minted id were **kept**: the five `file_collections[*].id` values (`#collection-omop`, `#collection-waveform-telemetry`, `#collection-imaging`, `#collection-clinical-notes`, `#collection-eeg`), because `FileCollection` requires `id` — and these are the same ids the core record's `distributions` entries carry, so they are also referenced across the pair; and `creators[0].principal_investigator.id`, because `Person` requires `id`.

### 2.8 `at_risk_populations` — inference marked (both records)

`at_risk_groups_included: true` is retained, but the absence material that was sitting in `notes` moved to a new `source_caveats` that states plainly that the boolean is an inference from the reported PICU and NICU admissions and that the documents neither characterize the cohort as at-risk nor describe assent, guardian consent or protections. `notes` now holds only the attested fact.

---

## 3. What was left as-is

**`instances[*].missing_information[0].why_missing` (multivalency, low).** Left as a list in both records. The audit flagged this as a shape *risk* to verify, not a confirmed defect; the schema digest's `MissingInfo` entry lists `why_missing` among the accepted keys without stating a range or cardinality, so the digest does not support a change either way. Both records validate. Unchanged.

**`human_subject_research.special_populations` (multivalency, low).** Same disposition and same reasoning: the digest lists `special_populations` and `regulatory_compliance` under `HumanSubjectResearch` without declaring cardinality. `special_populations` remains a one-item list in both records; `regulatory_compliance` was never populated. Unchanged.

**Source-conflict handling.** The audit found this correct and no change was made. The top-level `source_caveats` on both records still reports both cohort figures and both imaging counts, names the manifest ranking as the reason for preferring chorus4ai.org, and notes the extraction damage to the webinar's inventory table.

**`license_and_use_terms` / absence of a dataset `license`.** Confirmed sound by the audit; unchanged in both records.

**`data_governance.access_review_process`.** The audit's remedy for the `distribution_formats` defect noted this slot already carries the access route. It does, and it was left exactly as written.

---

## 4. Full-versus-core consistency

The core record is a projection of the reconciled full record; every change above was applied to both where the core schema declares the slot. The core carries `distributions` (projected from `file_collections`) in place of `file_collections`, and does not carry `splits`, `direct_collection`, `participant_privacy`, `raw_data_sources`… — of these, only `splits`, `direct_collection` and `participant_privacy` were touched or questioned, and of those only `splits` was changed, so it is dispositioned `full`. The core header retains `# Sources:` and now carries `# Phase 4 reconciliation: completed`.

Referent: the record describes the CHoRUS dataset itself — the multicenter multimodal critical-care collection — not the CHoRUS project, the GitHub organization, or the AIM-AHEAD training program. That choice is held consistently across both records; the training program appears only as an access route and an intended use, and the GitHub organization only under `external_resources` and `extension_mechanism`.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `distribution_formats[0].format` | changed | both | Held an access route; now holds `OMOP Common Data Model`. Enclave/Azure/OHDSI detail moved to the entry's `notes`. |
| `distribution_formats` | added | both | Rebuilt from one collapsed entry to five, one per bundle-attested modality standard (OMOP, OHNLP, DICOM, WFDB, EDF+ and Persyst). |
| `updates.frequency` | removed | both | Stated an absence rather than answering; attested half folded into `update_details`, absence into `updates.source_caveats`. |
| `updates.update_details` | changed | both | Absorbed the attested site status-update cadence from the removed `frequency`. |
| `updates.source_caveats` | added | both | Records that no release cadence or versioning policy is stated. |
| `existing_uses[0].examples` | changed | both | Prospective cohort-2 curriculum example removed; only the attested present-tense use remains. |
| `existing_uses[0].source_caveats` | added | both | Records that cohort 2 is prospective (CFA 2025-09-02, award 2025-11-10, start 2025-11-17) and is carried under `intended_uses`. |
| `instances[1].data_substrate` | removed | both | `B2AI_SUBSTRATE:37` not attested; the bundle names no storage substrate for the OMOP rows. |
| `status` | changed | both | Reduced from a two-sentence paragraph to the token `partially released`; progress detail already in `description` and `updates`. |
| `labeling_strategies[0].labeling_details` | changed | both | Trailing absence clause removed; attested future-tense plan retained. |
| `labeling_strategies[0].source_caveats` | added | both | Holds the future-tense qualification and the absence of released labels. |
| `splits[0].split_details` | changed | full | Trailing absence clause removed; award-abstract statement retained. |
| `splits[0].source_caveats` | added | full | Holds the planned-capability qualification and the unreported size/availability. Core schema does not carry `splits`. |
| `intended_uses[1].usage_notes` | changed | both | Trailing absence clause moved out. |
| `intended_uses[1].source_caveats` | added | both | Records that the holdout set is not reported as released. |
| `creators[0].name` | added | both | Creator entry for Eric Rosenthal previously had no `name`, unlike the other six; roster shape now uniform. |
| `creators[0].principal_investigator` | retained | both | PI designation attested only for Rosenthal, by NIH RePORTER; `Person` requires its `id`, so the minted fragment stays. |
| `creators[*].id` | removed | both | Minted fragments on an optional-`id` class that nothing in either record references. |
| `funders[0].id` | removed | both | As above. |
| `data_collectors[*].id` | removed | both | As above. |
| `maintainers[*].id` | removed | both | As above. |
| `intended_uses[*].id` | removed | both | As above. |
| `existing_uses[0].id` | removed | both | As above. |
| `instances[*].id` | removed | both | As above. |
| `subpopulations[*].id` | removed | both | As above. |
| `acquisition_methods[*].id` | removed | both | As above. |
| `collection_mechanisms[*].id` | removed | both | As above. |
| `sampling_strategies[0].id` | removed | both | As above. |
| `preprocessing_strategies[*].id` | removed | both | As above. |
| `cleaning_strategies[*].id` | removed | both | As above. |
| `labeling_strategies[0].id` | removed | both | As above. |
| `ethical_reviews[0].id` | removed | both | As above. |
| `external_resources[*].id` | removed | both | As above. |
| `file_collections[*].id` | retained | full | `FileCollection` requires `id`; the same ids are referenced by the core record's `distributions` entries. |
| `at_risk_populations.at_risk_groups_included` | retained | both | Inference from reported PICU/NICU admissions kept, now qualified. |
| `at_risk_populations.source_caveats` | added | both | States that the boolean is an inference and that no assent, guardian consent or protections are described. |
| `at_risk_populations.notes` | changed | both | Reduced to the attested fact; absence material moved to `source_caveats`. |
| `instances[2].missing_information[0].why_missing` | retained | both | Multivalency flagged as a risk only; the digest declares no cardinality for `MissingInfo.why_missing`, and both records validate. |
| `instances[4].missing_information[0].why_missing` | retained | both | As above. |
| `human_subject_research.special_populations` | retained | both | Multivalency flagged as a risk only; the digest declares no cardinality for it. Content (PICU/NICU implying minors and neonates) is supported. |
| `source_caveats` | retained | both | Source-conflict handling confirmed correct by the audit; both cohort figures and both imaging counts preserved with the ranking rationale. |
| `license_and_use_terms` | retained | both | MIT correctly confined to a statement about the code, with a caveat; no dataset `license` asserted. |
| `data_governance.access_review_process` | retained | both | Already carries the access route the `distribution_formats` remedy referred to; left exactly as written. |