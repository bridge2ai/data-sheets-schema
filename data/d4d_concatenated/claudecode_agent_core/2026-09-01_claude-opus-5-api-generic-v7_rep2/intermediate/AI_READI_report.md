# Phase 4 Reconciliation Report — AI_READI

Version label: `2026-09-01_claude-opus-5-api-generic-v7_rep2`
Records reconciled: full (`AI_READI_d4d.yaml`) and core (`AI_READI_d4d_core.yaml`)

---

## 1. Summary of the audit

The Phase 3 audit returned 23 findings against the full record: 1 high, 8 medium, and 14 low. Fifteen of the low-severity findings were confirmations that an omission was deliberate and evidence-backed (errata, `existing_uses`, `use_repository`, the four annotation/labeling/tooling/imputation slots, `compression`) or notes on value provenance rather than defects. No fabricated dataset facts were found, no prior-D4D contamination was detected, and no shape violations against the schema digest were reported.

The substantive defects clustered in four areas:

1. **`creators`** — one Creator object collapsed the organizational creator of record, a principal investigator, and ten institutional affiliations drawn from sponsor/collaborator/official rosters rather than from any statement about dataset authorship; source commentary sat in `notes` rather than `source_caveats`.
2. **`data_governance`** — `committee_name` and `committee_contact` were constructed rather than transcribed.
3. **Interpretive enum and boolean determinations** — `hipaa_compliant`, `is_representative`, `was_inferred_derived`, `data_topic`, `RO_CRATE` in `conforms_to_standard`, and two `is_described_by` relationship types were the record's own judgments, not source statements.
4. **A minted fragment identifier and a derived count** — the root-metadata `file_collections` entry that nothing in the record referenced, and its computed `file_count: 9`.

---

## 2. Changes made

Each change below is visible by comparing the original and reconciled records supplied above. Changes were applied to the full record and carried through to the core record wherever the affected slot appears in both.

### 2.1 `creators` — split into two entities, affiliations narrowed, notes relocated (high + two medium)

**Original:** a single Creator object with `principal_investigator: Aaron Y. Lee`, ten `affiliations` (Washington University in St. Louis, University of Washington, UAB, UCSD, Johns Hopkins, OHSU, Stanford, California Medical Innovations Institute, University of Utah, University of Massachusetts Lowell), a `notes` field explaining that the creator of record is the AI-READI Consortium, and a `source_caveats` on the PI affiliation conflict.

**Reconciled:** two Creator objects.

- The first carries `affiliations: [{name: AI-READI Consortium}]` with a `source_caveats` recording that FAIRhub registers a single creator with `nameType: "Organizational"`, that the RO-Crate records the same author and publisher, and that no source supplies an identifier for the consortium as an organization — so none is asserted.
- The second carries the PI with a single affiliation, Washington University in St. Louis (`ROR:01yc7t268`), and a `source_caveats` recording the tier-1 disagreement between FAIRhub (Washington University in St. Louis) and the RO-Crate (Department of Ophthalmology, University of Washington), and explaining that the FAIRhub affiliation is recorded because it supplies a registry identifier.

Nine ROR CURIEs were dropped: `ROR:00cvxb145`, `ROR:008s83205`, `ROR:0168r3w48`, `ROR:00za53h95`, `ROR:009avj582`, `ROR:00f54p054`, `ROR:0156zyn36`, `ROR:03r0ha626`, `ROR:03hamhx47`. Each is grounded in the bundle as a study sponsor, collaborator, or overall-official affiliation, but none is attested as an affiliation of the dataset's creator, and University of Utah and UMass Lowell appear only against individual officials.

The `notes` field was removed entirely; its content is now carried by the two `source_caveats` fields, which is where the schema places trust annotation about sibling slots.

The core record's `creators` slot mirrors the full record exactly.

### 2.2 `data_governance.committee_name` — replaced with the attested string (medium)

**Original:** `AI-READI Data Access Committee`.
**Reconciled:** `AI-READI Consortium`, taken verbatim from the RO-Crate's `dataGovernanceCommittee` field (tier 1). The `notes` field was rewritten to record both what the RO-Crate states and that the BMJ Open protocol refers to a Data Access Committee "without naming it further".

### 2.3 `data_governance.committee_contact` — removed (medium)

**Original:** a Person object naming Aaron Y. Lee with his ORCID.
**Reconciled:** the slot is absent. A new sentence opens `data_governance.source_caveats`: "No contact person is asserted for the governance committee: no source in the bundle designates one." The pre-existing caveat about accountable-organization attribution was retained beneath it. Lee remains recorded as study PI and central contact in `creators` and `maintainers`, where the bundle does attest those roles.

### 2.4 `conforms_to_standard` — `RO_CRATE` removed (medium)

**Original (dataset level):** `[CDS, DICOM, OMOP_CDM, WFDB, OPEN_MHEALTH, ESDS, RO_CRATE]`.
**Reconciled:** `[CDS, DICOM, OMOP_CDM, WFDB, OPEN_MHEALTH, ESDS]`. RO-Crate describes a metadata packaging artifact about the dataset, not a standard the dataset's own content follows; the remaining six terms all correspond to content standards named in the bundle's data-type standards mapping. Applied identically in the core record.

### 2.5 Root-metadata `file_collections` entry — removed, content moved to prose (two medium)

**Original:** a tenth `file_collections` entry with `id: ark:59853/rocrate-b2ai-aireadi-release-3-0-0#root-metadata`, `file_count: 9`, `path: /`, and a description listing the nine CDS-required root files.

**Reconciled:** the entry is gone from both records. Two defects are resolved together: the minted fragment identifier that no value in the record referenced (contrary to the v6 minting rule), and the `file_count: 9` derived by counting entries in a list the bundle never totals. The nine filenames — and the fact that `participants.tsv` carries the recommended split — are now stated in dataset-level `notes`, where they are described rather than labeled. The core record's `distributions` list drops from ten entries to nine, matching.

### 2.6 `instances[0].data_topic` — removed (medium)

**Original:** `data_topic: B2AI_TOPIC:43` (Diabetes).
**Reconciled:** the slot is absent, and a new `source_caveats` on the instance object records that "the bundle supplies no topic or substrate classification for instances, and the instance spans survey, clinical, imaging, waveform, wearable and environmental data forms that no single term covers." `data_substrate` remains omitted as before. Applied identically in the core record.

### 2.7 `regulatory_restrictions.hipaa_compliant` — removed (low)

**Original:** `hipaa_compliant: compliant`.
**Reconciled:** the slot is absent. A new `source_caveats` on the object states that no source makes a compliance determination and directs the reader to `other_compliance`, which was rewritten to state what the sources actually say: FAIRhub records `deIdentHIPAA` as true, and the release is stated to contain no PHI as defined by the Privacy Rule. The phrase "verified by the project against the Safe Harbor method" was dropped from `other_compliance` for the same reason as §2.9. Applied identically in the core record.

### 2.8 `sampling_strategies[0].is_representative` — removed (low)

**Original:** `is_representative: false`.
**Reconciled:** the slot is absent. `why_not_representative` is retained, since its content is directly attested (the deliberate equal-proportion balancing rationale). The object's `source_caveats` now opens "No representativeness determination is asserted: no source in the bundle states one," followed by the pre-existing reconciliation of the healthsheet "all possible instances" answer against FAIRhub's "Non-Probability Sample". Applied identically in the core record.

### 2.9 `is_deidentified` — the two source statements separated (low)

**Original:** `method` merged FAIRhub's "no identifiers were collected so no active de-identification was necessary" with Nature Metabolism's "stripped of PHI ... via the Safe Harbor method" into one causal narrative.

**Reconciled:**
- `method` now carries only the tier-1 FAIRhub statement.
- `deidentification_details` carries the tier-3 Nature Metabolism statement, quoted, alongside the FAIRhub flags and the RO-Crate `deidentified: true`.
- `identifiers_removed` drops "per the HIPAA Safe Harbor method", retaining "Protected Health Information".
- `source_caveats` was rewritten to name the tension explicitly, identify the tiers, and state that the tier-1 statement occupies `method` while the tier-3 statement is recorded rather than merged.

`participant_privacy[0].anonymization_method` was correspondingly changed from "by the Safe Harbor method" to "Removal of HIPAA-defined Protected Health Information from the public set". Applied identically in the core record.

### 2.10 `acquisition_methods[0].was_inferred_derived` — removed (low)

**Original:** `was_inferred_derived: false`, which contradicted the record's own `variables` entries showing BMI, waist-hip ratio, and log CS as derived.
**Reconciled:** the slot is absent, and a new `source_caveats` records that the healthsheet answer the object draws on "distinguishes only directly observable from subject-reported acquisition and does not state whether any values were inferred or derived", then names the three derived variables. Applied identically in the core record.

### 2.11 `related_datasets` — relationship type changed for the two publications (low)

**Original:** `is_described_by` for both `doi:10.1038/s42255-024-01165-x` and `doi:10.1136/bmjopen-2024-097449`.
**Reconciled:** both changed to `is_documented_by`, and each entry gained a `source_caveats` stating that no source asserts a typed relation to the publication and that the chosen term is "the closest available term rather than an attested relationship type". The RO-Crate lists both under `associatedPublication`; FAIRhub's `relatedIdentifier` block uses `IsDocumentedBy` for the two documentation URLs, which makes `is_documented_by` the nearer term in the permitted enum. The two `is_new_version_of` entries were left unchanged, being directly supported by the FAIRhub versions list. Applied identically in the core record.

### 2.12 `human_subject_research.ethics_review_board` — conflict moved to `source_caveats` (low)

**Original:** the value narrated the RO-Crate name and the UW postal address together as an inline conflict, inconsistent with the sibling `ethical_reviews[0]` object which places the same conflict in `source_caveats`.
**Reconciled:** `ethics_review_board` now states the body and its contact details plainly; a new `source_caveats` on `human_subject_research` carries the naming conflict, matching the treatment in `ethical_reviews[0]`. Applied identically in the core record.

### 2.13 `external_resources[5].source_caveats` — inference removed (low)

**Original:** characterized the BMJ Open citation as naming "the University of Washington IRB protocol number rather than a trial registration" — the record's own judgment that a source erred.
**Reconciled:** the caveat now quotes the BMJ text verbatim and observes that it is "the same string the same publication and the RO-Crate give as the University of Washington IRB protocol number", leaving the reader to draw the conclusion. Applied identically in the core record.

### 2.14 `source_caveats` (dataset level) — provenance of the total added (low)

A final sentence was appended to the top-level `source_caveats` in both records: `total_size_bytes` is taken from the FAIRhub API `data.size` field (3815969779678) rather than summed from the per-collection `total_bytes` values, which cover the nine data-type subcrates but not the root metadata files. This resolves the ambiguity the audit flagged without changing the value, which is directly attested.

---

## 3. Findings left as-is

### 3.1 `publisher` (low)

`publisher: https://fairhub.io/` is unchanged. The declared range is `uriorcurie`; no schema-declared prefix covers FAIRhub, so a URL is the permitted fallback. The audit's observation that FAIRhub records `publisherName: "FAIRhub"` is correct, but a bare name is not an identifier and the slot's range asks for one. The value stands.

### 3.2 `total_size_bytes` (low)

The integer is unchanged, being directly taken from the FAIRhub API. Only the provenance annotation was added (§2.14).

### 3.3 Confirmed omissions (low, seven findings)

The audit flagged these to confirm the omissions were deliberate rather than oversights. Each was verified against the bundle and each remains omitted in both records:

- **`errata`** — the healthsheet's erratum question has an empty response, which is absence of information, not an assertion of none.
- **`existing_uses`** — the healthsheet answers "No"; the ExistingUse class offers no field to carry a negative.
- **`use_repository`** — the healthsheet answers "No"; same reasoning.
- **`annotation_analyses`, `labeling_strategies`, `machine_annotation_tools`, `imputation_protocols`** — the healthsheet repeatedly answers "N/A - no labels are provided" and the RO-Crate records `rai:dataAnnotationProtocol: "N/A - no labels are provided"`; no imputation is described anywhere. The absence of labeling is instead stated in `instances[0].label: false` with `label_description`, and the absence of imputation in `missing_data_documentation[0].handling_strategy`.
- **`compression`** — no compression or archive format appears in the bundle; the FAIRhub `format` list contains only `application/dicom`, `text/markdown`, `text/csv`, `application/json`.

---

## 4. Referent consistency

Both records describe the same referent: version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, DOI `10.60775/fairhub.3`, as published on FAIRhub — the release itself, not the AI-READI study, not the project, and not the biorepository. Biospecimens are described in `notes` as explicitly outside the release. The three declared source conflicts (institutional attribution, target enrollment, collection start date) remain resolved in favor of the higher-ranked source with the alternative recorded, per the source ranking.

---

## 5. Slot counts and validation

| | Full | Core |
|---|---|---|
| Top-level slots populated, before | 68 | 62 |
| Top-level slots populated, after | 68 | 62 |

No top-level slot was added or removed. All removals were of nested keys (`data_topic`, `is_representative`, `was_inferred_derived`, `hipaa_compliant`, `committee_contact`, `creators[].notes`) or of list entries (one `file_collections` entry / one `distributions` entry, nine `affiliations`, one `conforms_to_standard` term). One list gained an entry: `creators` went from one object to two.

Both files were validated after reconciliation:

- Full: `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — passed.
- Core: `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — passed.

The core header now carries `# Phase 4 reconciliation: completed`.