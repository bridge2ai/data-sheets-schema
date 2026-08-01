# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Referent decision

The declared bundle describes a single named dataset — *Flagship Dataset of Type 2 Diabetes from the AI-READI Project* — captured at two different release states. The input sheet selects the v2.0.0 documentation and the v2.0.0 FAIRhub record; the bundle also carries the v3.0.0 documentation and the v3.0.0 FAIRhub API metadata, and both curation notes instruct that v3 be preferred where the two disagree (FAIRhub marks the v2 record "no longer accessible").

**Referent held for both records: dataset version 3.0.0**, DOI `10.60775/fairhub.3`, 2,280 participants, 356,343 files, 3.82 TB, released 2025-11-17.

Consequences carried consistently through both records:

- `version` = `3.0.0`; `doi`, `issued`, `total_file_count`, `total_size_bytes` all take v3 values.
- v2.0.0 evidence (2.01 TB, 165,051 files, 1,067 participants) is retained only as *version history*, never as a competing description of the referent.
- The v1.0 license text — the only license text physically present in the bundle — is retained as evidence, but the referent's governing license is the v2.0 custom license at `10.5281/zenodo.17555036`, per the v3 metadata.

This choice was already applied consistently in both records; the audit confirmed no drift and required no correction here.

---

## 2. Audit outcome in brief

Nineteen findings were raised: one high, four medium, fourteen low. Twelve findings produced edits; seven were left as-is. Three of the low findings were **positive verifications** — cases where the records were audited specifically because the bundle is self-contradictory, and were confirmed to have handled the contradiction correctly.

No prior D4D record was consulted at any phase. All corrections were re-grounded against the declared bundle only.

---

## 3. Changes made to the core record

### 3.1 `resources` — removed (high severity)

The core record carried FAIRhub records 1, 2, and 4 under `resources`, whose schema definition is *"Sub-resources or component datasets that are part of this dataset."*

The bundle does not support a part-of relation for any of the three:

- v1.0.0 and v2.0.0 are **superseded prior versions** of the same dataset, not components of v3.0.0. The FAIRhub version list presents them as siblings in a lineage, not as parts.
- Record 4 is explicitly typed in the FAIRhub API as `"child": 4` of a `"mini": false` parent, described on the page as *"A smaller version is available for pipeline development"* — and the source manifest curation note states directly that record 4 *"is a distinct 'Mini Version' (100 participants, DOI 10.60775/fairhub.4) for pipeline development, **not a version of this dataset**, and was not captured."* The bundle therefore contains no captured evidence about record 4's contents at all.

Asserting composition here would have manufactured a structural relationship the evidence contradicts. The slot was removed. Version lineage remains fully represented in `version_access` (which enumerates all three DOIs with their release dates and notes that v2.0.0 is no longer accessible) and in `distribution_dates`. No information was lost.

### 3.2 `collection_timeframes` — synthesized range removed

Same defect as the full record; see §4.2. The phrase "approximately 4 to 10 percent" was replaced with the two attributed source figures.

### 3.3 `distributions` — non-distribution entry removed

The final list entry restated whole-dataset totals (356,343 files; 3,815,969,779,678 bytes) as though they constituted a distribution. Totals are not a distribution format, and the full record already carries them in the purpose-built `total_file_count` and `total_size_bytes` slots. The entry was removed; the remaining entries (DICOM, CSV, JSON, Markdown, WFDB, plus the self-attestation-gated FAIRhub access path) are unchanged.

### 3.4 Edits mirrored from the full record

For paired consistency, the following corrections were applied identically in the core record: removal of `conforms_to_schema`; removal of "Salutogenesis" from `keywords`; trimming of the inferred clause in `known_limitations`; rebalancing of the blood-volume attribution in `collection_mechanisms`.

---

## 4. Changes made to the full record

### 4.1 `citation` — reduced to what the bundle supplies

The value opened with a constructed citation string (`AI-READI Consortium (2025). Flagship Dataset of Type 2 Diabetes from the AI-READI Project (Version 3.0.0). FAIRhub. https://doi.org/10.60775/fairhub.3.`). No such string appears anywhere in the bundle. It was assembled from separate metadata fields — `creator.creatorName`, `publicationYear`, `title.titleValue`, `version`, `publisher.publisherName`, `identifier.identifierValue`.

Every source that touches citation in this bundle supplies a **pointer, not a string**:

- FAIRhub v3 page: *"When using this resource, please follow the citation instructions provided at https://docs.aireadi.org/docs/3/citation"*
- README: *"please cite the resources specified in the AI-READI documentation for version 3.0.0 of the dataset at https://docs.aireadi.org"*
- License §3: *"The current citation for you to use can be found here: docs.aireadi.org."*
- Healthsheet (uses, Q2): *"use of the dataset requires citation to the resources specified in https://docs.aireadi.org."*

The docs citation page itself is not in the bundle. The fabricated string was deleted; the slot now records only the pointer and the fact that citation is a stated condition of use, which is fully evidenced. Preferring omission of the unsupported half over retaining a plausible-looking DataCite rendering.

### 4.2 `collection_timeframes` — synthesized range replaced with attributed figures (medium)

The record read "approximately 4 to 10 percent of participants are expected to undergo a follow-up examination in year 4." No source states a range. The bundle states two different, non-equivalent quantities:

| Source | Statement |
|---|---|
| Healthsheet (collection, Q5) | *"Approximately 4% of participants are expected to undergo a follow-up examination in Year 4."* |
| NIH RePORTER abstract; FAIRhub README; study `detailedDescription` | *"longitudinal data from 10% of the study cohort"* |
| IRB protocol §5.1 | *"we intend to invite 10% of the study population"* |

These are not endpoints of a span: one is an expected completion rate, the others are a cohort-design target and an invitation intent. Collapsing them into "4 to 10 percent" invented a claim held by no source. Under the bundle-disagreement rule, the value now reports both figures with attribution and does not adjudicate between them.

### 4.3 `known_limitations` — inferred impact clause removed (medium)

The entry read: *"Marijuana use was not assessed for participants living in Alabama because it is an illegal substance there, producing a site-dependent gap in that variable."*

The first clause is directly supported (BMJ Open Table 1 footnote: *"Marijuana use not assessed for participants living in Alabama because it is an illegal substance"*; IRB §5.1 distinguishes the UW/UCSD and UAB questionnaire variants). The trailing clause is the record's own inference — no source characterizes this as a limitation of the released dataset, and the healthsheet's own limitations discussion does not mention it. The clause was cut; the factual exclusion is retained.

### 4.4 `conforms_to_schema` — removed (low)

Held `https://schema.aireadi.org/v0.1.0/dataset_description.json`. That URI is the schema of the `dataset_description.json` metadata *file* inside the release, not a schema the dataset conforms to. It also cites v0.1.0 while the dataset's actual structural standard, already correctly recorded in `conforms_to`, is Clinical Dataset Structure (CDS) v0.1.1. Retaining it would have implied dataset-level conformance to a file-level artifact schema. Removed; `conforms_to` and `conforms_to_class` are unaffected.

### 4.5 `publisher` — corrected (low)

Held `https://fairhub.io/`. The bundle declares `"publisher": {"publisherName": "FAIRhub"}` — a name, not a URI — and separately declares `managingOrganization` as Washington University in St. Louis with ROR `https://ror.org/01yc7t268`. Substituting the platform homepage for the declared publisher name introduced an identifier the metadata does not assign. The slot now carries the FAIRhub ROR-style identifier where the bundle supplies one and otherwise defers; the managing-organization tension continues to be handled in `maintainers` (§5.2) rather than being folded in here.

### 4.6 `keywords` — "Salutogenesis" removed (low)

The keyword list otherwise reproduces two controlled vocabularies verbatim: the FAIRhub `subject` array (Diabetes mellitus / Machine Learning / Artificial Intelligence / Electrocardiography / Continuous Glucose Monitoring / Retinal imaging / Eye exam, most with LOINC or MeSH codes) and the study `keywordList` (which adds Retinal Imaging, Data Sharing, Exploratory Data Collection). "Salutogenesis" appears in neither. It is pervasive in the bundle's prose — it is arguably the project's central concept — but adding a term to an otherwise-transcribed controlled list misrepresents the list as sourced. Removed. The concept remains fully expressed in `purposes`, `description`, and `addressing_gaps`.

### 4.7 Four slots added for paired-record consistency (low)

These were present in the core record and absent from the full record despite identical supporting evidence. Asymmetry between paired records is itself a defect. Added to the full record:

- **`annotation_analyses`** — records that no annotation analysis applies. Healthsheet labeling Q1–Q5 answer "N/A - no labels are provided" and Q3 explains the dataset *"is a hypothesis-agnostic dataset aimed at facilitating multiple potential downstream AI/ML applications."*
- **`machine_annotation_tools`** — records that no annotation tooling was used, distinguishing this from the automated format-conversion pipelines described in the README changelog ("automated + custom" processing) and the preprocessing answers.
- **`use_repository`** — healthsheet uses Q3: *"Is there a repository that links to any or all papers or systems that use the dataset? ... No."* FAIRhub's usage panel (views, cited-by, access-approved counters) is noted as the only tracking surface present.
- **`status`** — study `statusModule.overallStatus` = "Enrolling by invitation", actual start 2023-07-19, anticipated completion 2027-01-01, with v3.0.0 released 2025-11-17.

### 4.8 `collection_mechanisms` — blood-volume attribution rebalanced (medium)

The value read "approximately 50-60 mL of blood (reported as 53 mL in the protocol publication)". Both figures are real and they disagree:

- IRB protocol §5.1: *"We will collect approximately 50-60 ml of blood (about 3-4 spoonfuls)."*
- BMJ Open, Biospecimen processing: *"Blood (53 mL) is collected for clinical lab assays and biobanking purposes."*

The parenthetical form presented the IRB figure as the headline and the published figure as a footnote, which is an implicit adjudication. Both figures are now stated with their sources at equal weight. No numeric change.

---

## 5. Left as-is, with reasons

### 5.1 `is_deidentified` — contradictory source metadata, faithfully reported (verified correct)

The v3 `datasetDeIdentLevel` block is internally inconsistent: `deIdentType: "NoDeIdentification"` alongside `deIdentDirect: true` and `deIdentHIPAA: true`, with the free-text note *"No identifiers were collected so no active de-identification was necessary but we checked that no identifiable data per US HIPAA were present."* This sits against the Nature Metabolism claim that the public set is *"stripped of Protected Health Information (PHI) ... via the 'Safe Harbor' method"* and the README's *"contain no protected health information (PHI)."* Compounding this, healthsheet composition Q13 and preprocessing Q1 — both of which ask directly about de-identification measures — are among the three unanswered questions in the sheet.

The record reports the contradiction as a contradiction and flags the unanswered questions. That is the correct handling under the disagreement rule. **Unchanged.**

### 5.2 `maintainers` — three-way institutional tension, surfaced not resolved (verified correct)

The bundle names three different responsible institutions: FAIRhub metadata gives `managingOrganization` and `leadSponsor` as **Washington University in St. Louis** (ROR `01yc7t268`), including for PI Aaron Lee's affiliation; NIH RePORTER gives the awardee organization as **University of Washington**; the license names **University of Washington** as Licensor; and the publications affiliate Aaron Lee and Cecilia Lee with the University of Washington, Seattle. The WashU attribution appears only in the FAIRhub structured metadata and is inconsistent with every other source, but it is what that metadata states.

The record lists the claims with their sources rather than selecting one. **Unchanged.**

### 5.3 `direct_collection` — EHR lookback discrepancy, attributed per source (verified correct)

BMJ Open: *"all patients aged ≥40 years of age who had a medical encounter within each health system site (UAB, UCSD, UW) between 2020 and 2025."* Healthsheet collection Q7: *"patients who have had an encounter with the sites' health systems within the past 2 years."* Different windows, different documents, both retained with attribution. **Unchanged.**

### 5.4 `issued` — fabricated time precision retained under structural necessity

`2025-11-17T00:00:00Z` adds a time and timezone the bundle never supplies (`"dateValue": "2025-11-17"`). The slot range is `datetime` and the validator requires a full timestamp; midnight-UTC is the conventional zero-information padding. Removing the slot would discard a well-evidenced date to avoid a purely structural artifact. **Retained**, and recorded here so the added precision is not mistaken for evidence.

### 5.5 `license` — single scalar resolved to the referent's license

The scalar `license` slot admits one value and now carries the v2.0 custom license (`10.5281/zenodo.17555036`), consistent with the v3.0.0 referent. This is in tension with the bundle's evidence weighting: the **v1.0 license is the only license whose full text is present**, captured as its own source, and the source manifest explicitly notes that its Zenodo DOI *"is retained explicitly because an older DOI-only extraction carried this identifier separately."*

Resolving the scalar to the referent's own license is required by the single-referent rule. The richer picture — both license versions, the specific obligations quoted from the v1.0 text (non-transferability, the Models carve-out with its memorization-minimization duty, the anti-reidentification and no-clinical-decisions restrictions, NIH GDS security compliance, the one-dollar liability cap) — is carried in `license_and_use_terms`, `ip_restrictions`, `prohibited_uses`, and `regulatory_restrictions`. **Unchanged**, noted as an evidence-scope decision rather than an omission.

### 5.6 `variables` — 13-item selection retained, scope noted

The slot holds 13 `VariableMetadata` entries. The available evidence is substantially larger: BMJ Open Table 2 enumerates roughly 40 laboratory analytes with units, reference ranges, and stated rationale for inclusion; Table 4 details per-device retinal scan types and image counts; the IRB protocol references an uploaded full variable list that is not itself in the bundle.

Expanding to full transcription would convert the record into a data dictionary, and there is no target density to hit. The selection spans the modality breadth (clinical labs, vitals, imaging, CGM, wearable, environmental, survey) rather than exhausting any one domain. **Unchanged**, with the sampling nature recorded here so the slot is not read as an exhaustive inventory.

### 5.7 Unanswered healthsheet questions — not backfilled

Three of the 84 healthsheet questions are unanswered (empty-string responses): composition Q13 (re-identification avoidance measures), preprocessing Q1 (de-identification preprocessing), and maintenance Q3 (erratum). Each corresponds to a slot a datasheet would normally populate. All three were left unpopulated or explicitly marked as not stated rather than inferred from adjacent material. Notably, `errata` is omitted entirely rather than being filled with an assertion that no errata exist — the source is silent, not negative.

---

## 6. Cross-record consistency check

After reconciliation the two records were re-diffed on every shared slot:

| Dimension | Full | Core | Agree |
|---|---|---|---|
| Referent version | 3.0.0 | 3.0.0 | ✓ |
| DOI | 10.60775/fairhub.3 | 10.60775/fairhub.3 | ✓ |
| Participant count | 2,280 | 2,280 | ✓ |
| File count / size | 356,343 / 3.82 TB | 356,343 / 3.82 TB | ✓ |
| Release date | 2025-11-17 | 2025-11-17 | ✓ |
| Collection window | 2023-07-19 → 2025-05-01 | 2023-07-19 → 2025-05-01 | ✓ |
| License | AI-READI custom v2.0 | AI-READI custom v2.0 | ✓ |
| Splits | 1576 / 352 / 352 | 1576 / 352 / 352 | ✓ |
| Follow-up figures | 4% and 10%, attributed | 4% and 10%, attributed | ✓ |
| Keywords | controlled lists only | controlled lists only | ✓ |

No residual contradictions between the paired records.

---

## 7. Final state

| | Full | Core |
|---|---|---|
| Slots populated | 74 | 31 |
| Edits applied | 8 | 6 |
| Schema | `data_sheets_schema_all.yaml` / `Dataset` | `data_sheets_schema_core_all.yaml` / `CoreDataset` |
| `linkml-validate` | **pass** | **pass** |

**Reconciliation outcome: resolved.** One high-severity structural misuse corrected (core `resources`), three medium-severity synthesis defects corrected (constructed citation, merged follow-up range, inferred limitation clause), eight low-severity issues corrected, and seven items deliberately retained with the reasoning recorded above. Three audit findings were positive verifications confirming that the bundle's genuine internal conflicts — de-identification status, managing institution, and EHR lookback window — are surfaced rather than silently resolved.