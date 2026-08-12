# Reconciliation Report — AI_READI

**Version label:** `2026-08-11_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (declared input bundle only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 files)
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-api-generic_rep1/AI_READI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-api-generic_rep1/AI_READI_d4d_core.yaml`

---

## 1. Referent declaration

Both records describe **one referent**: *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, **version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17 on FAIRhub.

The bundle also describes three adjacent entities that are **not** the referent and were held outside the record body:

| Adjacent entity | Why not the referent | Where represented |
|---|---|---|
| The AI-READI **study** (NCT06002048, 4,000-participant target, 2022–2027) | A study, not a dataset; its enrolment target and completion date describe the protocol, not the release | `purposes`, `collection_timeframes`, `human_subject_research`, `sampling_strategies` |
| Dataset **v1.0.0 and v2.0.0** | Distinct DOIs, distinct participant counts, both marked no longer accessible | `related_datasets` (typed), `version_access`, `distribution_dates` |
| The **UAB CCTS biorepository** | Physical specimens; no part of the 3.82 TB release | `external_resources`, `notes` |

All size, file-count, participant-count and split figures in both records apply to v3.0.0 only.

---

## 2. Source conflicts carried forward, not silently resolved

The bundle contains four internal disagreements. Per the provenance guard, each is now represented rather than adjudicated.

| Conflict | Evidence | Treatment after reconciliation |
|---|---|---|
| Managing organisation / lead sponsor | FAIRhub API `managingOrganization` and `leadSponsor` both give *Washington University in St. Louis* (ROR `01yc7t268`); the BMJ Open protocol, the NIH RePORTER record, the IRB protocol and the FAIRhub `locationList` all give *University of Washington* (ROR `00cvxb145`), and the licence names UW as Licensor | **Changed.** Previously the body of the record presented UW throughout with the conflict noted only in top-level `source_caveats`. Both affiliations are now carried in `creators[0].affiliations` and in `human_subject_research.notes`, with the caveat retained. Neither is presented as the resolved value. |
| Target enrolment | 4,000 (BMJ Open, Nature Metabolism, FAIRhub `enrollmentCount`, README) vs 4,600 (IRB protocol, twice) | Both figures retained in `sampling_strategies[0].notes`; caveat retained. |
| Acronym expansion | *Artificial Intelligence Ready and **Equitable** Atlas* (BMJ Open, Nature Metabolism) vs *…Ready and **Exploratory** Atlas* (NIH RePORTER, healthsheet, README, study_description) | Both retained in `title`-adjacent `notes`; caveat retained. |
| File count | Header and `data.fileCount` give 356,343; the nine `numberOfFiles` values sum to 356,334 | `total_file_count: 356343` (the declared figure) with the nine-way discrepancy flagged in `source_caveats`. |

---

## 3. High-severity findings — both remediated

### 3.1 Core `distributions` block was not a schema slot

**Finding.** The core record carried a `distributions` list whose key names (`path`, `bytes`, `format`, `media_type`, `conforms_to`) match no declared object range. `FileCollection` uses `total_bytes` and `file_count`; there is no `bytes`.

**Change.** The block was removed and re-expressed as `file_collections`, mirroring the full record's nine directory-level entries plus the root-metadata entry. Each entry now carries `id`, `path`, `collection_type`, `file_count`, `total_bytes`, `conforms_to` and `description`. The per-directory standards (WFDB, OMOP CDM, ESDS ASCII, DICOM, Open mHealth) sit on the individual collections where the bundle assigns them.

**Effect.** The core record now validates against `CoreDataset`; before the change it would not have.

### 3.2 Synthetic fragment identifiers

**Finding.** `#split-train`, `#cardiac_ecg` and similar fragments were minted by the generator and appear nowhere in the bundle.

**Change.** Retained, but **documented as record-local constructions**. Every `DataSubset` and `FileCollection` entry now carries a `source_caveats` line stating that the identifier is a record-local construction over the FAIRhub DOI and is not an identifier asserted by any source. `id` is a required key on both ranges, so omission was not available; the alternative — omitting the entries entirely — would have discarded well-evidenced split and directory content. Directory-derived fragments (`#cardiac_ecg`) at least reuse the bundle's own `directoryName` values; split fragments do not, and are flagged more strongly.

---

## 4. Shape corrections — prose moved out of atomic-valued slots

This was the dominant systematic defect. Eight slots held multi-clause prose where the schema calls for an atomic value. In every case the fact was preserved; only its placement changed.

| Slot | Before | After |
|---|---|---|
| `creators[*].principal_investigator` | `"Aaron Y. Lee (Study Principal Investigator; contact e-mail leeay@uw.edu)"` | Name only; role, ORCID and contact moved to the entry's `notes` |
| `creators[0]` (organisational) | `"AI-READI Consortium (organizational creator of record in the FAIRhub DataCite metadata)"` | Name only; provenance moved to `source_caveats` |
| `funders[0].grants` | First element a full sentence carrying award amount, period and application ID; later elements bare identifiers | Three bare identifiers (`OT2OD032644`, `P30DK035816`, `UL1TR003096`); amount, period, application ID, project number and award title moved to `funders[0].notes` |
| `distribution_dates[0].release_dates` | Three prose sentences bundling date, version, DOI, participant count, accessibility | Three ISO dates (`2024-05-03`, `2024-11-08`, `2025-11-17`); the rest moved to `notes`, with version/DOI facts already held in `version_access` |
| `distribution_formats` | One entry with a six-format paragraph in `format` and four comma-joined values in `media_type` | Four entries, one per declared media type (`application/dicom`, `text/csv`, `application/json`, `text/markdown`), each with a single `format` and `media_type`; WFDB and `.tsv` noted where the bundle supports them |
| `conforms_to` (top level) | Seven-standard, nine-directory mapping paragraph | `"Clinical Dataset Structure (CDS) v0.1.1"`; the per-directory mapping remains on each `file_collection`, and the full enumeration moved to `notes` |
| `subsets[*].description` | Split composition packed into prose | Composition expressed through `subpopulations` on each `DataSubset` (race/ethnicity, sex, diabetes status counts); `description` reduced to the split's role and proportion |
| `existing_uses[0].examples` | A negative statement (`"None recorded…"`) in an examples list | Slot omitted; the healthsheet's "No" recorded in `existing_uses[0].notes` |

---

## 5. Over-assertion — four values softened or dropped

| Slot | Prior value | Change | Reason |
|---|---|---|---|
| `regulatory_restrictions.hipaa_compliant` | `compliant` | → `not_applicable`, with the Safe Harbor stripping and the team's verification recorded in `notes` | No source in the bundle makes a formal compliance determination or uses the word "compliant" of the dataset. The enum value asserted a certification. |
| `regulatory_restrictions.confidentiality_level` | `restricted` | **Omitted**; the tiered public/controlled arrangement described in `notes` | The bundle assigns no confidentiality level. A single enum cannot represent a two-tier release. |
| `is_deidentified.identifiable_elements_present` (core) | `false` | **Omitted** from both records | The FAIRhub flag reads `deIdentType: NoDeIdentification` with `deIdentDirect: true` and `deIdentHIPAA: true` — self-contradictory on its face. The prose gloss ("No identifiers were collected so no active de-identification was necessary") is retained verbatim in `deidentification_details`, and the flag conflict in `source_caveats`. This also removes a full/core divergence. |
| `keywords` | Included `"Salutogenesis"` | Term removed | Pervasive in the bundle's prose but present in neither the FAIRhub `subject` list nor the study `keywordList`. Adding it asserted dataset metadata no source carries. The concept remains in `description`, `purposes` and `tasks`. |
| `license_and_use_terms.data_use_permission` | `disease_specific_research`, unqualified | Value retained, `notes` now states it describes the **public tier only** and that the same licence permits commercial reuse | The enum admits one value; the scope limitation was previously unstated. |

---

## 6. Referent-boundary corrections

Two entries attributed properties of the biorepository to the released dataset.

- **`known_biases`** — the PBMC/PAXgene overnight-shipping entry (`measurement_bias`) was **removed** from `known_biases`. Its own notes conceded it affects specimen handling, and no biospecimen data are in the 3.82 TB release. The fact is preserved in `external_resources` under the biorepository description, where the BMJ Open protocol places it.
- **`sensitive_elements`** — the biorepository entry set `sensitive_elements_present: true` while the sibling dataset entry set it `false`, producing a contradiction within one slot. The biorepository entry was **removed**; the genomic and specimen content is described in `external_resources`. The remaining entry describes the controlled-access tier (5-digit ZIP, sex, race, ethnicity, genetic sequencing, medications, past health records, traffic and accident reports), which *is* part of the dataset's access structure.

---

## 7. Full ↔ core divergence — resolved

Eight slots were present in the full record and absent from the core record while the same facts survived as prose in core `notes`. Per the schema digest, `notes` holds residual content only after every fitting slot is used. All eight were **restored to the core record** in structured form, and the corresponding prose removed from `notes`:

`variables` · `splits` · `subsets` · `relationships` · `related_datasets` · `participant_privacy` · `total_file_count` · `total_size_bytes`

Two further divergences resolved:

- **`citation`** — the full record carried a value that was commentary about the slot's own emptiness ("citation instructions are not reproduced in the source…") plus constructed DataCite components; the core record omitted the slot. The bundle genuinely contains no citation string, only pointers to `https://docs.aireadi.org/docs/3/citation`. **Both records now omit `citation`**, with the pointer in `external_resources` and the licence's acknowledgement obligation in `license_and_use_terms`.
- **`collection_notifications` / `collection_consents` / `consent_revocations`** — full carried three structured entries; core folded all three into `informed_consent[0].notes`. **Core now carries the three structured entries**, matching full.

Both records now populate the same slots wherever the core schema provides them. No core omission remains unjustified.

---

## 8. Left as-is, with reasoning

| Item | Decision | Reasoning |
|---|---|---|
| `id` = `https://doi.org/10.60775/fairhub.3` | Kept | Resolvable, unique, derived directly from the declared DOI. `id` is required. |
| `publisher` = `https://fairhub.io/` | Kept, caveated | Range is `uriorcurie`; the bundle gives `publisherName: "FAIRhub"` as a name only. The URI is a minimal resolution of a name to its platform. Now flagged in `source_caveats` as a record-local resolution. |
| `created_by` duplicating `creators[0]` | Kept | Redundant but not incorrect; `created_by` is a plain-string convenience slot and the organisational creator is the correct filler. |
| `file_collections[9].file_count: 9` (root metadata) | Kept, flagged | Counted from the nine enumerated `metadataFileList` entries at root. The bundle does not state the number. The existing inference flag is correct practice and was strengthened, not removed. |
| `instances[0].counts: 2280` | Kept | Participant-level counting is fixed by `instance_type` ("an individual participant") and by the healthsheet's explicit "Each instance represents an individual patient." File-level counts live in `total_file_count`. |
| `human_subject_research.special_populations` describing exclusions | Kept, reworded | The bundle's only statement about protected populations is that they were excluded (no minors, no pregnancy, no gestational diabetes, no T1DM, upper age bound 85). Recording the exclusions is the honest response; the value now reads as an exclusion statement rather than an inclusion list. `at_risk_populations` remains populated only with the guardian/assent fields the IRB protocol marks N/A. |
| `license_and_use_terms.license_terms` summarising **v1.0** while `license` names **v2.0** | Kept, foregrounded | Only the v1.0 text is in the bundle (`AI-READI-LICENSE-v1.0_row11.txt`); the FAIRhub metadata names "AI-READI custom license v2.0" at `10.5281/zenodo.17555036` without reproducing it. The v1.0 clause summary is the only licence content available. The caveat was moved to the **head** of `license_terms` so a reader meets it before the clauses. |
| Four source conflicts | Kept unresolved | Section 2. The guard requires representation over selection. |
| `version: "3.0.0"` alongside v1/v2 facts elsewhere | Kept | Consistent with the declared referent. A `notes` sentence now states explicitly that all size, count and split figures apply to v3.0.0 and that v1/v2 figures appear only in relationship and history slots. |
| `notes` content: biorepository, return-of-results | Kept in `notes` | Return-of-incidental-findings procedure (BP thresholds, retinal detachment, disc oedema referral) and the exam-card / encrypted-email results return have no fitting structured slot. The biorepository paragraph was reduced — its substance moved to `external_resources` — leaving only the cross-reference. |

---

## 9. Final state

| | Full | Core |
|---|---|---|
| Populated top-level slots | **79** | **48** |
| `file_collections` entries | 10 | 10 |
| `variables` entries | 39 | 39 |
| `subsets` entries | 3 | 3 |
| Slots carrying an inference flag | 6 | 4 |
| Unresolved source conflicts declared | 4 | 4 |

**Validation**

- `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` → **PASS**
- `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` → **PASS**

**Provenance guard**

No previously generated D4D record was read, opened, grepped or consulted. Factual inputs were the declared bundle and the two schema files only. No prior-D4D reuse.

**Outcome:** reconciled. Two high-severity findings remediated; eight shape corrections applied; four over-asserted values softened or dropped; two referent-boundary violations removed; ten full/core divergences resolved. Twelve findings were left as-is, each with a stated reason above.