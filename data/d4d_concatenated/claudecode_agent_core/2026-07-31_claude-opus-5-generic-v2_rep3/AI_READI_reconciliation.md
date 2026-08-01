# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Referent:** *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, version 3.0.0, DOI `10.60775/fairhub.3` — the current FAIRhub release. Held consistently across both records. The v2.0.0 FAIRhub record and v2 documentation in the bundle are treated as evidence about a superseded release, per the bundle's own curation notes.

---

## 1. Audit outcome

The Phase 3 audit returned **23 findings: 0 high, 4 medium, 19 low**. No evidence of prior-D4D reuse was found; the provenance guard held. Numeric content verified clean: the nine file-collection counts sum to 356,334 against a declared 356,343 (difference = the nine root metadata files), byte sizes sum to 3,815,969,360,064 against a declared 3,815,969,779,678 (difference ≈ 419 KB of metadata), and every subpopulation and split figure reconciles to the 2,280-participant total.

---

## 2. Changes made

### 2.1 `at_risk_populations` — unsupported prisoner determination removed (both records)

**Finding severity:** medium.

Both records asserted that "the IRB protocol records that prisoners are not a target population and that the research is not expected to enrol prisoners." Re-reading the bundle confirms the audit: IRB sections 2.3 and 2.4 appear as an **unanswered blank template**. The checkbox options are reproduced but no selection is recorded, and no completed prisoner determination appears anywhere in the extracted text.

Attributing a determination to a blank form is fabrication regardless of how probable the determination is. The sentence was removed from both records. What remains in the slot is the evidence-backed material: the ≥40-year age floor, and the exclusion of pregnancy, gestational diabetes, and type 1 diabetes — all of which appear as completed eligibility criteria in both the healthsheet and the study metadata.

### 2.2 Lead-sponsor conflict now represented rather than silently resolved (both records)

**Finding severity:** medium.

The bundle contains a genuine, unresolvable disagreement about the responsible institution:

| Source | Institution named |
|---|---|
| FAIRhub API `studyDescription.leadSponsor` | Washington University in St. Louis (ROR `01yc7t268`) |
| FAIRhub API `managingOrganization` | Washington University in St. Louis |
| FAIRhub API `responsibleParty` / central contact affiliation | Washington University in St. Louis |
| NIH RePORTER, project 10471118 | UNIVERSITY OF WASHINGTON |
| Data License Agreement v1.0 | "UNIVERSITY OF WASHINGTON ('Licensor')" |
| BMJ protocol, IRB approval | University of Washington (STUDY00016228) |

Neither record mentioned Washington University in St. Louis at all, and `ip_restrictions` flatly asserted "the Licensor (the University of Washington)."

The prompt requires representing disagreement rather than selecting one side. Both records were amended: `created_by` and `publisher` now record both institutional attributions with their sources; `ip_restrictions` and `license_and_use_terms` now state that the licence text in the bundle names the University of Washington as Licensor **while** the structured dataset metadata names Washington University in St. Louis as lead sponsor and managing organization, without adjudicating between them.

### 2.3 `related_datasets` added (full record)

**Finding severity:** medium.

Typed dataset relationships were clearly supported but had been dispersed into `version_access`, `external_resources`, `distribution_dates`, and `intended_uses`. Three `DatasetRelationship` objects were added, each carrying the two required keys:

- `IsNewVersionOf` → `10.60775/fairhub.1` (v1.0.0, 3 May 2024, 204 participants)
- `IsNewVersionOf` → `10.60775/fairhub.2` (v2.0.0, 8 Nov 2024, 1,067 participants)
- `HasPart` → `10.60775/fairhub.4` (Mini Version, 100 participants; recorded in the API as `"child": 4`)

The dispersed mentions were left in place where they answer their own slot's question (version history in `version_access`, release dates in `distribution_dates`) and removed where they did not — see 2.4.

### 2.4 Mini Version removed from `intended_uses` (full record)

**Finding severity:** low.

The Mini Version (DOI `10.60775/fairhub.4`, 100 participants) had been listed as an intended use of this dataset. The bundle's own curation note states it is "a distinct 'Mini Version' ... not a version of this dataset." Pipeline development conducted against a different dataset is not a use of this one. The entry was removed; the relationship is now carried in `related_datasets` where it belongs.

### 2.5 `keywords` — "Salutogenesis" removed (both records)

**Finding severity:** low.

Neither the FAIRhub keyword list (Diabetes mellitus, Machine Learning, Artificial Intelligence, Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam) nor the `studyDescription.keywordList` contains "Salutogenesis." It appears throughout the bundle as narrative vocabulary, not as a declared keyword. The `keywords` slot takes declared descriptors; the term was removed from both records. The concept remains present in `purposes` and `description`, where it is a fair characterisation of stated intent.

### 2.6 Licence version provenance corrected (both records)

**Finding severity:** low.

The operative terms populating `license_and_use_terms`, `prohibited_uses`, and `ip_restrictions` — licence grant scope, the model-distribution condition, the re-identification prohibition, the NIH GDS security requirement, the one-dollar liability cap, indemnification, title retention — all derive from the **v1.0** University of Washington Data License Agreement, the only licence text in the bundle. The released dataset is governed by "AI-READI custom license v2.0" (`10.5281/zenodo.17555036`), whose text is *not* in the bundle.

Both records had asserted that v1.0 "sets out the same structure," an inference the bundle does not establish. That assertion was removed. The slots now state explicitly that the governing licence is v2.0 by DOI, that its text is not present in the declared bundle, and that the enumerated terms are drawn from the v1.0 agreement that is present.

### 2.7 `version_access` — over-read healthsheet answer corrected (both records)

**Finding severity:** low.

Both records stated "the healthsheet states that older versions will not continue to be supported." The healthsheet answered that maintenance question with **"N/A"** and only restated that the dataset will not be updated in place. It made no statement about withdrawal of support. The sentence was replaced with the independently supported facts: the v2.0.0 FAIRhub record carries the banner "This version of the dataset is no longer accessible," and the v2 documentation page carries the corresponding notice. Those are direct quotations from the bundle; the healthsheet inference was not.

### 2.8 `citation` — synthesised string replaced (full record)

**Finding severity:** low.

The citation had been synthesised from DataCite fields into a formatted string. The bundle provides no citation string; it provides only the instruction to "follow the citation instructions provided at https://docs.aireadi.org/docs/3/citation."

Under the v2 rule that a slot must carry the information asked for rather than a pointer to where it lives, a pointer is not an acceptable value either. The slot was **omitted**. The constituent facts the citation would have carried — creator (AI-READI Consortium), title, version 3.0.0, publication year 2025, DOI, publisher FAIRhub — are all present in their own slots, where they are grounded rather than assembled.

### 2.9 Two source disagreements now represented (both records)

**Finding severity:** low (×2).

- **Target enrolment.** All records gave 4,000. The IRB narrative states "a cross-sectional dataset of 4600 people across the US" in one passage, while its own enrolment table sums to 4,000 and every other source says 4,000. `human_subject_research` and `sampling_strategies` now record 4,000 as the figure given across the study metadata, healthsheet, protocol, and RePORTER abstract, and note the single conflicting 4,600 figure in the IRB narrative.
- **Blood volume.** Both records gave "approximately 50-60 mL" (the IRB figure). The BMJ protocol states "Blood (53 mL) is collected." `acquisition_methods` now carries both with attribution.

### 2.10 `variables` — NOx units claim corrected (full record)

**Finding severity:** low.

The nitrogen oxides variable was described as "reported as a Sensirion NOx index." The bundle's variable table lists "Nitrogen oxides (NO and NO2)." The NOx Index reference in the bundle is a pointer to a Sensirion documentation search, not a statement about the released variable's units. The units claim was removed; the variable description now matches the table.

### 2.11 `conforms_to_schema` added (both records)

**Finding severity:** low.

Only `conforms_to` (the CDS specification) had been populated. The bundle supplies explicit schema URIs that answer `conforms_to_schema` directly: `https://schema.aireadi.org/v0.1.0/dataset_description.json` and `https://schema.aireadi.org/v0.1.1/dataset_structure_description.json`. Both are now recorded.

### 2.12 `known_biases` → `known_limitations` reclassification (full record)

**Finding severity:** low.

Multi-device measurement heterogeneity had been framed as a bias. The healthsheet frames it as a generalization factor and states the multiple devices were deliberately included "to enhance generalizability and represent the diverse range of equipment utilized in clinical settings." That is a limitation on comparability, not a systematic bias — and the stated intent runs the opposite direction from a bias claim. The item was moved to `known_limitations` with the healthsheet's own framing.

### 2.13 `discouraged_uses` — synthesised entries removed (both records)

**Finding severity:** low.

Both entries (extrapolating representativeness; assuming group balance) were synthesised from stated limitations rather than drawn from any statement about discouraged use. The bundle's only answer to the discouraged/prohibited-use question points to the licence restrictions. Both entries were removed. The underlying facts remain in `known_limitations`, where they are what the bundle actually says; `prohibited_uses` continues to carry the licence-derived restrictions, which are genuinely prohibitions.

### 2.14 `subpopulations` — controlled-access qualification applied consistently (both records)

**Finding severity:** low.

Eleven `Subpopulation` objects derive from the README recommended-split table, while the healthsheet answers **"No"** to whether the dataset identifies demographic sub-populations, and the race/ethnicity and sex fields are withheld from the public release. Six entries carried that qualification; the diabetes-status and age entries did not. The qualification was applied uniformly: every entry now records that the split counts appear in the README while the corresponding participant-level fields are held under controlled access.

### 2.15 `sensitive_elements` — biorepository scoping resolved (full record)

**Finding severity:** low.

Biospecimens (plasma, serum, buffy coats, DNA, PAXgene RNA, PBMCs) were listed as a sensitive element of the dataset while the same entry conceded they are governed by separate procedures and are not part of the downloadable dataset. That is internally inconsistent about the referent. The entry was removed from `sensitive_elements`, which now covers only elements of the dataset as distributed. The biorepository remains described in `acquisition_methods` and `future_use_impacts`, which concern the study rather than the release.

### 2.16 `is_deidentified` — flag interpretation softened (both records)

**Finding severity:** low.

Rendering `deIdentDirect: true` / `deIdentHIPAA: true` as identifiers being "flagged as handled" is an interpretation of ambiguous booleans that sit alongside `deIdentType: NoDeIdentification` and the explanation that no identifiers were collected. The slot now quotes the `deIdentDetails` text directly — "No identifiers were collected so no active de-identification was necessary but we checked that no identifiable data per US HIPAA were present in the data" — and records the flag values without glossing them.

### 2.17 Core-record slot placement corrected

**Finding severity:** low (×2).

Against the `CoreDataset` slot inventory, the audit's conditional concerns resolved as follows:

- **Confirmed misplacement.** `future_use_impacts` carried the recommended 70/15/15 train/validation/test split. `CoreDataset` has a `splits` slot; the content was moved there. This is a field-fit correction under the v2 rule.
- **Confirmed misplacement.** `distributions` carried the nine per-directory file inventories alongside a separate `distribution_formats`. The inventories were moved to `file_collections`, and `total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678) were populated as dedicated numeric slots, matching the full record.
- **Not misplacements.** `CoreDataset` has no `participant_compensation`, `participant_privacy`, `collection_notifications`, or `consent_revocations` slots. The compensation, device-privacy, notification, and revocation content folded into `human_subject_research`, `at_risk_populations`, and `informed_consent` is therefore correctly placed for the core schema, and was left as-is.

---

## 3. Left unchanged, with reasoning

### 3.1 `creators` — affiliation list not expanded

The audit noted that the single `Creator` object omits Meharry Medical College, Portland State University, University of Utah, University of Massachusetts Lowell, and the NIH institutes from its affiliation enumeration.

Left as-is. The bundle names exactly one creator — `"creatorName": "AI-READI Consortium"`, `"nameType": "Organizational"` — so the multivalued-slot rule is already satisfied by a single object. The affiliation list is a supporting enumeration, not the slot's subject, and the omitted institutions appear in the Nature Metabolism author-affiliation footnotes rather than in any creator declaration. Expanding the list would improve completeness marginally while shifting the object further from what the bundle declares. The consortium membership is separately recoverable from `external_resources`, which points to the project team page.

### 3.2 Numeric discrepancies in file counts and sizes

The 9-file and ~419 KB gaps between the summed directory inventories and the declared totals are fully explained by the nine root-level metadata files (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`), which the API lists in `metadataFileList` outside the directory tree. Both records already carry the declared totals and the per-directory figures. No change needed; noted here so the arithmetic is auditable.

### 3.3 v2.0.0 evidence retained

The bundle includes the v2.0.0 FAIRhub record (2.01 TB, 165,051 files) and the v2 documentation page, both marked superseded by curation notes. These are retained as evidence about the prior release — in `related_datasets` and `version_access` — rather than removed. They document version history, which is what those slots ask for. The v3.0.0 figures alone populate `total_file_count`, `total_size_bytes`, and `version`.

### 3.4 Healthsheet-derived content

Substantial material in both records originates in the FAIRhub healthsheet, which is itself a datasheet-style artifact. The bundle's curation note flags that material drawn from it "is closer to transcription than extraction." This is inherent to the declared bundle and is not a defect to correct — the healthsheet is a legitimate source within the bundle. Noted for downstream interpretation of these records' independence.

### 3.5 `dataset_structure_description` file inventory

Roughly 48 KB of the API response is a file/directory listing that the bundle's curation note characterises as "low-value bulk rather than evidence." Directory-level descriptions, standards, and counts were used; the leaf-level file listing was not mined for additional slots. Consistent with the note and with the preference for omission over padding.

---

## 4. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Populated slots | 61 | 34 |
| Schema | `data_sheets_schema_all.yaml` (`Dataset`) | `data_sheets_schema_core_all.yaml` (`CoreDataset`) |
| Validation | pass | pass |

**Slot changes, full record:** −1 (`citation` omitted), +2 (`related_datasets`, `conforms_to_schema`), −1 (`discouraged_uses` emptied and omitted). Net +0 against a starting 61; content revised in 14 further slots.

**Slot changes, core record:** −1 (`citation`), +3 (`conforms_to_schema`, `total_file_count`, `total_size_bytes`), +1 (`splits`), +1 (`file_collections`), −1 (`distributions` emptied and omitted), −1 (`discouraged_uses` omitted). Content revised in 9 further slots.

**Consistency check:** the referent, version, DOI, participant count (2,280), collection window (19 July 2023 – 1 May 2025), release date (17 November 2025), licence identification, and the institutional-attribution conflict are now stated identically across both records.

---

## 5. Provenance

No previously generated D4D record was read, opened, grepped, or consulted at any phase. All factual content derives from `data/preprocessed/concatenated/AI_READI_preprocessed.txt` and the two schema files. The audit found no prior-D4D reuse, and none occurred.