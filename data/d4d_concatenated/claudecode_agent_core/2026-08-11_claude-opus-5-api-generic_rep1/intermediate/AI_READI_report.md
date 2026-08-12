# Reconciliation Report — AI_READI

**Version label:** `2026-08-11_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-api-generic_rep1/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-api-generic_rep1/AI_READI_d4d_core.yaml`

**Source of dataset facts:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 files). No prior D4D record was read, opened, grepped, or consulted at any phase.

---

## 1. Referent declaration

`Dataset` admits one referent. The referent for both records is:

> **Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17 on FAIRhub — 2,280 participants, 356,343 files, 3,815,969,779,678 bytes, data collected 2023-07-19 to 2025-05-01.

This is the referent the bundle best supports: it is the object described by the FAIRhub API record (the single largest and most structured source in the bundle), the object documented at `docs.aireadi.org/docs/3`, and the object whose healthsheet is reproduced in full. Versions 1.0.0 and 2.0.0 are represented as *related datasets* and *version history*, not as the referent. The AI-READI **study** (NCT06002048, target enrolment 4,000, running to 2027) is the generating activity, not the referent; study facts appear only where they describe the provenance of the released data.

Consequence held consistently across both records: every count, size, date-range, split figure and file listing in either record describes v3.0.0. Facts about v1.0.0 and v2.0.0 appear only inside `version_access`, `related_datasets`, `distribution_dates` and `updates`, and are labelled with their version in each case.

---

## 2. Source conflicts in the bundle

The bundle is internally inconsistent on four points. Per the uniform decision rules, these are represented rather than silently resolved; each is now carried in a `source_caveats` slot at the point of use, not only at top level.

| Conflict | Evidence A | Evidence B | Handling |
|---|---|---|---|
| Managing organisation / lead sponsor | FAIRhub `managingOrganization` and `leadSponsor` both give **Washington University in St. Louis** (ROR `01yc7t268`), and attach that affiliation to Aaron Lee, Cecilia Lee and the central contact | NIH RePORTER gives organisation **University of Washington**; the BMJ protocol, the licence agreement ("UNIVERSITY OF WASHINGTON (Licensor)"), the IRB application and the study location list all give University of Washington | Both are now stated. `creators` entries for the Lee PIs carry a per-entry `source_caveats` naming the discrepancy; the top-level caveat is retained. Neither institution is presented as settled fact. |
| Target enrolment | 4,000 (BMJ protocol, Nature Metabolism, NIH RePORTER, FAIRhub `enrollmentCount`) | 4,600 (IRB protocol form, twice) | Both stated in `sampling_strategies` notes. 4,000 is used nowhere as a bare figure. |
| Acronym expansion | "Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights" (BMJ, Nature Metabolism) | "Artificial Intelligence Ready and **Exploratory** Atlas for Diabetes Insights" (NIH RePORTER, FAIRhub healthsheet, FAIRhub study title, README) | Both recorded in `notes`; neither expansion is asserted in `title` or `name`, which use the bundle's dataset title verbatim. |
| File count | Root `fileCount` 356,343; `size` 3,815,969,779,678 | Sum of the nine `numberOfFiles` directory values is 356,334 — a shortfall of 9, matching the nine root-level metadata files | Root figures used for `total_file_count` / `total_size_bytes`. The nine-file reconciliation is now stated as an *observation about the arithmetic*, not as a counted value (see §3.2). |

---

## 3. Findings acted on

### 3.1 Core `distributions` block replaced (high)

**Finding.** The core record carried a `distributions` list whose slot name is absent from the schema inventory, and whose member keys (`path`, `bytes`, `conforms_to`, `format`, `media_type`) match no declared object range — in particular `bytes`, where `FileCollection` declares `total_bytes`.

**Change.** The block was rewritten as `file_collections`, mirroring the full record's structure: one entry per top-level datatype directory, keyed on `id`, with `path`, `file_count`, `total_bytes`, `collection_type`, `description` and `conforms_to`. The per-directory format assignments moved onto each entry's `conforms_to`.

**Reason.** A slot that does not exist cannot validate, and the audit's reading of the digest is correct: `file_collections` is the declared home for per-directory groupings. This was the only finding that blocked core validation.

### 3.2 Synthetic fragment identifiers removed (high)

**Finding.** `id` values of the form `https://doi.org/10.60775/fairhub.3#split-train` and `...#cardiac_ecg` were minted by the generator; no such identifiers appear in the bundle.

**Change.** Retained, but re-based. `DataSubset` and `FileCollection` both require `id`, so these entries cannot exist without one. The fragments were re-based off a record-local namespace rather than off the dataset DOI, so that they no longer imply that the DOI resolves to sub-entities the registrar does not mint. A `source_caveats` on each affected entry now states that the identifier is a record-local construction, not a transcribed identifier.

**Reason.** The schema forces an `id`; the honest remedy is to keep the entries and disclose the construction, rather than to drop well-evidenced splits and directories in order to avoid minting a key. Rebasing removes the false implication that these are registered DOI fragments.

### 3.3 Inferred root-level file count withdrawn (medium)

**Finding.** `file_collections[9].file_count: 9` was inferred from the length of the root `metadataFileList`, not transcribed.

**Change.** The numeric `file_count` was removed from that entry. The nine enumerated filenames remain in the entry `description`; the arithmetic observation (356,343 − 356,334 = 9) moved to `source_caveats` on the same entry.

**Reason.** A numeric slot presents its value as counted. The bundle enumerates nine files but never states a root file count, and the arithmetic agreement is corroboration, not a source statement.

### 3.4 Prose extracted from atomic-valued slots (medium — systematic)

This was the dominant defect class. In each case the prose moved to the entry's `notes`, and the slot retained only the value its range implies.

| Slot | Before | After |
|---|---|---|
| `creators[*].principal_investigator` | Name plus role commentary and e-mail | Name only; role, contact and affiliation-conflict commentary in `notes` / `source_caveats` |
| `funders[0].grants` | One prose sentence bundling award title, amount, period, application ID; then two bare identifiers | Three bare identifiers: `OT2OD032644`, `P30DK035816`, `UL1TR003096`. Award title, amount (USD 5,026,499), period (2022-09-01 – 2025-08-31), application ID 10471118 and project number 1OT2OD032644-01 in `notes` |
| `distribution_dates[0].release_dates` | Three prose sentences each bundling date, version, DOI, participant count, accessibility | Three ISO dates: `2024-05-03`, `2024-11-08`, `2025-11-17`. Version/DOI/count mapping in `notes` |
| `distribution_formats` | One entry with a six-format paragraph in `format` and four comma-joined values in `media_type` | Four entries, one per declared MIME type (`application/dicom`, `text/csv`, `text/markdown`, `application/json`), each with a single `media_type`. Scope annotations in per-entry `notes` |
| `conforms_to` (top level) | Seven-standard paragraph mapping standards to directories | `Clinical Dataset Structure (CDS) v0.1.1` — the standard governing the dataset's own layout. The seven-standard breakdown was already correctly carried per-directory on `file_collections`; the mapping paragraph moved to `notes` |

**Reason.** The digest gives these slots atomic or near-atomic ranges. Packing enumerations and commentary into them defeats the point of the structure and makes the values unusable to any consumer reading the slot by its declared range.

### 3.5 Over-asserted values softened (low, but factual)

| Slot | Before | After | Reason |
|---|---|---|---|
| `regulatory_restrictions.hipaa_compliant` | `compliant` | `not_applicable`, with `notes` reproducing the bundle's actual statements: PHI stripped under the Safe Harbor method; "we checked that no identifiable data per US HIPAA were present" | No source in the bundle issues a compliance determination. The enum value asserted a certification nobody made. `not_applicable` reflects that the released public set is asserted to contain no PHI, which is the bundle's actual claim |
| `regulatory_restrictions.confidentiality_level` | `restricted` | Slot removed; the tiered arrangement described in `notes` and in `license_and_use_terms` | The bundle assigns no confidentiality level. A single enum cannot represent a public tier gated by self-attestation plus a controlled tier gated by a DUA |
| `is_deidentified.identifiable_elements_present` (core) | `false` | Slot removed from core, matching the full record's omission | The bundle's own flag reads `deIdentType: NoDeIdentification` with `deIdentDirect: true` and `deIdentHIPAA: true`, and the accompanying detail says no identifiers were collected so no active de-identification was necessary. Asserting a boolean against that is stronger than the evidence. The narrative is preserved in `deidentification_details` and `source_caveats` |
| `keywords` | Included `Salutogenesis` | `Salutogenesis` removed | It appears in neither the FAIRhub `subject` list nor the study `keywordList`. It is pervasive in the bundle's prose but is not declared metadata of the dataset. The remaining ten terms are transcribed from the two declared lists, with their source noted |

### 3.6 Biorepository facts re-scoped (low)

**Finding.** A PBMC/PAXgene shipping-delay entry was classed as a `measurement_bias` of the dataset, and a biorepository entry set `sensitive_elements_present: true`, though both describe the UAB CCTS biospecimen collection, which is not part of the v3.0.0 release.

**Change.** Both entries were removed from `known_biases` and `sensitive_elements`. The biorepository is now described once, in `external_resources`, as a companion resource of the generating study, with its handling caveats and its finite-sample limitation attached there. The `sensitive_elements` list now contains only the single entry describing the controlled-access tier, whose `sensitive_elements_present` is `false` for the public release and whose notes enumerate the controlled variables (5-digit ZIP, sex, race, ethnicity, genetic sequencing, past health records, medications, traffic and accident reports).

**Reason.** Properties of a resource outside the referent were being asserted as properties of the referent, producing an internal contradiction where one `sensitive_elements` entry said true and another said false about the same release.

### 3.7 Core structural omissions restored (medium — systematic)

The core record had dropped eight well-evidenced slots while carrying the same facts as prose in `notes`. The digest is explicit that `notes` is for residual content only, after every fitting slot is used. Restored to core:

- `variables` — the 39 `VariableMetadata` entries from BMJ Open Tables 2 and 4, the healthsheet device section and the imaging protocol
- `splits` and `subsets` — the 70/15/15 train/validation/test partition and its three `DataSubset` entries
- `relationships` — single visit per participant; all instances from one prospective project
- `related_datasets` — the six typed relationships (two prior versions, two documentation sites, two publications)
- `total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678)
- `participant_privacy` — anonymisation, watermarking, tiered release, residual re-identification risk

The corresponding paragraphs were deleted from core `notes` so the facts are stated once.

### 3.8 Split composition destructured (low)

`DataSubset.description` had carried the per-split composition as prose. Since `DataSubset` accepts the top-level slot set, each subset now carries `subpopulations` entries for race/ethnicity, sex and diabetes status, with the counts from the README table, plus mean age in `notes`. `description` retains only the split's purpose and proportion.

### 3.9 Negative-finding slot cleared (low)

`existing_uses[0].examples` had held the string "None recorded. The healthsheet … answers 'No'". The `existing_uses` slot was removed entirely; the negative finding — that the healthsheet reports no prior use and no use-tracking repository — moved to `notes`, alongside the parallel negative for `use_repository`.

### 3.10 Redundancies and small alignments

- `created_by` removed; the AI-READI Consortium is already the organisational entry in `creators`.
- `citation` removed from the full record, aligning it with core. The bundle contains no citation string — only a pointer to `docs.aireadi.org/docs/3/citation`, which is not in the bundle. That pointer, plus the licence's acknowledgement obligation, is now in `notes`. A slot whose value is commentary on its own emptiness is worse than an absent slot.
- Full and core now agree slot-for-slot on `collection_notifications`, `collection_consents` and `consent_revocations`, all three carried as structured entries in both records rather than folded into `informed_consent[0].notes` in core.
- `human_subject_research.special_populations` reworded: it now records that no special population was targeted and that minors, pregnant people, people with gestational diabetes and people with type 1 diabetes were excluded — the exclusion criteria moved to `notes` rather than standing as the slot's value.

---

## 4. Findings left as-is

### 4.1 `publisher` as a URI (low)

Retained as `https://fairhub.io/`. The slot range is `uriorcurie` and the bundle gives only the name "FAIRhub". A CURIE is unavailable and the platform URL is the only identifier the bundle supplies for that entity. A `source_caveats` now records that the URL was substituted for a name. Dropping the slot would lose a fact the bundle does state.

### 4.2 `license_and_use_terms` describing licence v1.0 (low)

Retained. The record's `license` field names the v2.0 licence (`https://doi.org/10.5281/zenodo.17555036`), which governs v3.0.0 but whose text is **not in the bundle**. The bundle contains the full text of v1.0 only (`AI-READI-LICENSE-v1.0_row11.txt`). Rather than drop the only licence content available, the clause summary is retained with its `source_caveats` strengthened: it now states in the first clause that the summarised text is the superseded v1.0 and that the operative v2.0 text was not available to this record. Removing the summary would leave the record silent on licence substance; presenting v1.0 clauses without the flag would misrepresent them as operative.

### 4.3 `data_use_permission: disease_specific_research` (low)

Retained. It is the closest available enum value to the bundle's access condition ("Agreeing to use the data only for type 2 diabetes related research"). The enum cannot express the tiered arrangement or the concurrent commercial permission. A `notes` entry now states that the value describes the public tier's attestation only, that the licence separately permits commercial reuse, and that the controlled tier additionally requires a data use agreement.

### 4.4 `instances[0].counts: 2280` (low)

Retained. The digest supplies no unit semantics for `counts`, and `instance_type` states explicitly that each instance is an individual participant, which disambiguates. The file count is carried separately in `total_file_count`.

### 4.5 The WashU/UW conflict is not resolved (low)

Left unresolved by design. The audit is right that the body of the record leaned toward UW while the caveat noted the conflict; that asymmetry is now corrected by attaching per-entry caveats (§3.4, §2) rather than by picking a side. The uniform decision rules require representing what the evidence states rather than silently selecting one, and the bundle genuinely contains both. No source in the bundle explains the discrepancy — it may be a FAIRhub metadata error, but the record cannot assert that.

### 4.6 `version: "3.0.0"` alongside multi-version content (low)

Retained without change. The referent declaration in §1 and the per-entry version labelling in `version_access`, `related_datasets`, `distribution_dates` and `updates` are the intended mechanism for this. Removing the version history would lose well-evidenced facts about the release series.

### 4.7 `notes` content that has no fitting slot (low)

The return-of-results narrative (exam card at visit; Dexcom report by encrypted e-mail after the 10-day period; laboratory results at annual data release with reference ranges; emergency-referral thresholds for blood pressure, heart rate, and suspected retinal detachment, tumour or disc oedema) remains in `notes`. No slot in the inventory covers return of individual results to participants. It is retained because it is substantive provenance about the participant relationship. The biorepository and compensation paragraphs flagged by the audit have been moved out (§3.6, §3.7).

---

## 5. Divergences between the paired records

After reconciliation, the two records differ only where the core schema offers no corresponding slot. All divergences arising from generator choice rather than schema shape have been eliminated. Specifically:

- Core no longer omits `variables`, `splits`, `subsets`, `relationships`, `related_datasets`, `participant_privacy`, `total_file_count` or `total_size_bytes`.
- Core no longer carries a `distributions` block; it carries `file_collections`, as the full record does.
- Both records now omit `citation` and `created_by`, and both omit `is_deidentified.identifiable_elements_present`.
- Both records carry `collection_notifications`, `collection_consents` and `consent_revocations` as structured entries.

Any residual slot present in the full record and absent from core is absent because the core schema does not declare it. Each such case is a schema-shape consequence, not a judgment about the evidence.

---

## 6. Outcome

| Item | Result |
|---|---|
| Full record slot count | 71 |
| Core record slot count | 48 |
| Full validates (`Dataset`) | Yes |
| Core validates (`CoreDataset`) | Yes |
| High-severity findings | 2 — both remediated |
| Medium-severity findings | 10 — 9 remediated, 1 retained with strengthened caveat (§4.2) |
| Low-severity findings | 18 — 11 remediated, 7 retained with reasons (§4) |
| Referent consistent across both records | Yes (§1) |
| Prior D4D reuse | None. No file under `data/d4d_concatenated/` or any `*_crate_d4d.yaml` was read at any phase |
| Provenance record written | Yes — `d4d provenance record --project AI_READI --method claudecode_agent --label 2026-08-11_claude-opus-5-api-generic_rep1` |

**Reconciliation outcome: reconciled.** Both records validate; both describe the same referent with the same facts; the remaining divergences are schema-shape consequences and are enumerated in §5.