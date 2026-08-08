# Reconciliation Report — AI_READI

**Version label:** `2026-08-05_claude-opus-5-1m-generic-v3_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)

---

## 1. Referent

Both records denote a single referent: **the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17, comprising 2,280 participants across 356,343 files (3,815,969,779,678 bytes).

This choice is held consistently across both records. It was selected because the bundle's richest and most current sources — the FAIRhub API metadata (`fairhub_dataset_v3_api`), the v3.0.0 documentation, and the v3.0.0 FAIRhub HTML record — all describe this release, and because the curation notes explicitly instruct that the v3 sources be preferred over the v2 sources where they disagree.

Two consequences of this choice were enforced during reconciliation:

- Evidence describing the **v2.0.0 release** (2.01 TB, 165,051 files, 1,067 participants) is not asserted as a property of the referent. It appears only where it legitimately belongs: in `related_datasets` and `version_access`.
- Evidence describing the **study protocol** rather than the released dataset (the 4,000-participant target, the biorepository, the longitudinal arm) is retained only where the slot concerns the study's design or collection process, not where it would misstate the dataset's composition.

---

## 2. Audit findings and disposition

The audit returned 41 findings: 3 high, 15 medium, 23 low. Disposition follows.

### 2.1 High severity — all three corrected

#### F1. `distributions` slot in the core record is not schema-declared

**Finding:** The core record carried a `distributions` block whose slot name and object keys (`path`, `format`, `media_type`, `bytes`) correspond to nothing in the schema digest. The digest declares `distribution_formats` (range `DistributionFormat`, accepting only `access_urls`) and `file_collections` (range `FileCollection`, accepting `path`, `file_count`, `total_bytes`, `collection_type`).

**Action: removed.** The block was deleted from the core record in its entirety. It was a fabricated slot that would have failed core-schema validation, and its content was already carried correctly elsewhere.

**Rationale:** A slot the schema does not declare cannot be populated regardless of how well the underlying evidence supports its content. The digest is the authority on structure.

#### F2. Fabricated per-directory format assignments

**Finding:** The removed block asserted `CSV` for `cardiac_ecg` and `JSON` for the two wearable directories. The bundle states `cardiac_ecg` follows the **WaveForm DataBase (WFDB)** standard, directly contradicting CSV. The wearable directories follow **Open mHealth**; that Open mHealth is JSON-schema-based is true but is generator inference, not a bundle statement about the files. The dataset-level `format` list (`application/dicom`, `text/markdown`, `text/csv`, `application/json`) is stated without per-directory assignment.

**Action: resolved by F1's deletion.** No format claim survives that the bundle does not state. Where format-standard evidence is retained, it is expressed as the standard the directory follows, not as a MIME type inferred from that standard.

#### F3. `file_collections`, `total_file_count`, `total_size_bytes` missing from core

**Finding:** The core record omitted three declared slots that the full record populates from directly-stated bundle evidence, having routed the same evidence into the non-schema `distributions` block and lost `file_count` in the process.

**Action: added to core.** Nine `FileCollection` objects, one per data-type directory, each carrying `id`, `path`, `description`, `file_count`, `total_bytes`, `collection_type`, and `conforms_to`. Plus `total_file_count: 356343` and `total_size_bytes: 3815969779678`.

**Rationale:** The bundle supplies exact counts and sizes per directory in `datasetStructureDescription.directoryList`. This is among the least ambiguous evidence in the whole bundle. Its absence from the core record was an artifact of the fabricated slot, not a judgment about evidence.

---

### 2.2 Medium severity

#### F4. `data_protection_impacts` — asymmetry between records

**Finding:** Populated in core, omitted from full, from identical evidence (healthsheet collection Q12: "No, a data protection impact analysis has not been conducted.").

**Action: removed from both.**

**Rationale:** This is the harder call of the two available. The v2 rule states that a value recording that information is *absent* has not answered the field. `DataProtectionImpact` asks for impact assessments conducted; a statement that none was conducted does not describe an assessment. Symmetry was achieved by omission rather than by propagation, consistent with the rule that omission is the correct answer when the evidence does not answer the field. The fact remains recoverable from the bundle; the schema does not have a slot that asks for it.

#### F5–F6. `subsets` and `splits` missing from core

**Finding:** Both populated in the full record from the README split table and healthsheet labeling Q7; both omitted from core without stated reason.

**Action: added to core.** `splits` with the 70/15/15 rationale; `subsets` with three `DataSubset` objects (train/validation/test) carrying `is_data_split: true`, participant counts, and the stratification detail.

**Rationale:** The recommended split is explicitly stated, quantified per stratum, and is one of the dataset's distinguishing features (the split is balanced for sex, race/ethnicity and diabetes status precisely *because* those variables are withheld from the public release). Both slots are declared. There was no basis for the asymmetry.

#### F7. Ten further slots missing from core

**Finding:** `relationships`, `related_datasets`, `direct_collection`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation`, `variables`, `third_party_sharing` — all populated in full, all absent from core, all declared.

**Action: nine added to core; `variables` deliberately not added** (see F21).

**Rationale:** Each of the nine rests on explicit bundle statements — the $200 stipend, the withdrawal-without-data-removal policy, the three prior/child dataset versions with DOIs, the e-consent process in REDCap. The core record is a reduced-slot schema, not a reduced-*evidence* record; where the core schema declares a slot and the bundle answers it, it should be populated.

#### F8. Fabricated `citation` string

**Finding:** The full record composed `AI-READI Consortium (2025). Flagship Dataset of Type 2 Diabetes from the AI-READI Project, Version 3.0.0 [Data set]. FAIRhub. https://doi.org/10.60775/fairhub.3`. No such string appears in the bundle. Both FAIRhub and the licence direct users to `docs.aireadi.org/docs/3/citation`, a page not captured.

**Action: removed from both.**

**Rationale:** Constructing a plausible citation from components is exactly the inference the provenance guard forbids. The correct citation is stated by the bundle to exist elsewhere; the alternative to fabricating it — recording a pointer to where it lives — is barred by the v2 rule against pointer-values. Omission is the only correct disposition. The DOI, title, creator and publication year remain individually populated in their own slots, from which a user can reconstruct what they need.

#### F9. Constructed `publisher` URI

**Finding:** `https://fairhub.io` asserted; the bundle gives `publisherName: FAIRhub` with no URI.

**Action: changed to `FAIRhub` in both.**

**Rationale:** The slot range is `uriorcurie`, but LinkML accepts a bare string for that range, and supplying a name the bundle states is preferable to supplying an identifier it does not. The homepage URL of a platform is not that platform's publisher identifier.

#### F10. `creators` — single framing silently selected

**Finding:** All twenty `Creator` objects derive from Principal Investigator lists. The bundle's `datasetDescription.creator` names a single organisational creator, **"AI-READI Consortium"** with `nameType: Organizational` — the formal, dataset-level creator statement. The bundle additionally names a Writing Committee, Research/Technical/Clinical Staff, Project Managers and Interns.

**Action: `AI-READI Consortium` added as the first `Creator` in both records,** with `principal_investigator: false` and no affiliation, retaining the twenty individual PIs after it.

**Rationale:** The v2 rule requires one object per distinct entity where the range is multivalued; the Consortium-as-organisation is a distinct entity from any individual, and it is the one the dataset's own structured metadata designates. Retaining the individuals alongside it represents what the bundle offers rather than choosing between framings. The non-PI contributor categories were not added: the bundle names them but does not distinguish dataset creation from study conduct for them, and inventing per-person `Creator` objects for interns and staff would assert a creation role the bundle does not.

#### F11. Conflicting affiliations merged

**Finding:** Aaron Lee and Cecilia S. Lee were each given both "University of Washington" and "Washington University in St. Louis". These are distinct institutions; the Nature Metabolism affiliation list says the former, the FAIRhub `study_description` says the latter. Presenting both as a list reads as a joint appointment.

**Action: affiliation lists retained, but each entry now names its source** — e.g. `University of Washington (per the Nature Metabolism author affiliations)` and `Washington University in St. Louis (per the FAIRhub study_description; the two sources disagree)`.

**Rationale:** The instruction where sources disagree is to represent the disagreement, not to select or to merge. Silently listing both merges; annotating both represents. This affects the two individuals for whom the sources conflict and no others. The same annotation was applied to `managingOrganization`-derived content elsewhere.

#### F12. `hipaa_compliant: compliant`

**Finding:** No source makes a HIPAA compliance determination for the dataset. The bundle states PHI was stripped by Safe Harbor and that results were returned by HIPAA-compliant email; `datasetDeIdentLevel` records `deIdentHIPAA: true` alongside `deIdentType: NoDeIdentification`.

**Action: changed to `not_applicable` in both,** with the Safe Harbor and `deIdentHIPAA` evidence moved into `other_compliance` as descriptive text.

**Rationale:** `compliant` is a determination. `not_applicable` is the enum value that asserts least while remaining honest: the released public dataset contains no PHI, so HIPAA compliance is not the frame in which it is governed. The underlying facts are preserved in a free-text field where they can be stated without being converted into a verdict.

#### F13. `confidentiality_level: restricted`

**Finding:** No source assigns a confidentiality level. `accessType` is `PublicDownloadSelfAttestationRequired`.

**Action: removed from both.** The access conditions are retained verbatim in `license_and_use_terms` and `regulatory_restrictions.regulatory_restrictions`.

**Rationale:** All three enum values (`unrestricted`, `restricted`, `confidential`) would be generator classification. The dataset is publicly downloadable subject to login and self-attestation, which fits none of the three cleanly and which the bundle describes precisely in prose. Omitting the enum and keeping the prose loses nothing.

#### F14. `data_use_permission: disease_specific_research`

**Finding:** Defensible for the public set ("Agreeing to use the data only for type 2 diabetes related research") but collapses a two-tier arrangement the bundle explicitly distinguishes: `consentsDetails` states "The public version of the dataset can only be used for type 2 diabetes related research. A private version will allow for more generic use," and both licence versions permit commercial as well as research use.

**Action: `disease_specific_research` retained; `license_terms` amended** to state the two-tier arrangement and the commercial permission explicitly in its first sentence rather than in a later clause.

**Rationale:** The enum is single-valued and the record's referent is the public v3.0.0 release, for which `disease_specific_research` is the accurate constraint. The collapse is a property of the schema, not of the record. Making the two tiers prominent in the adjacent free-text field is the available remedy.

#### F15–F16. Superseded v1.0 licence dominates `license_terms` and `ip_restrictions`

**Finding:** Roughly two thirds of `license_terms` recited the v1.0 University of Washington Data License Agreement; all three `ip_restrictions.restrictions` entries were quoted from v1.0 with in-line attribution embedded in the restriction text. The operative instrument is **AI-READI custom license v2.0**, `10.5281/zenodo.17555036`.

**Action:**
- `license_terms` rewritten to lead with v2.0 — its name, DOI, the commercial-and-research permission, the security and secondary-sharing obligations, and the three access conditions — followed by a clearly demarcated final paragraph noting that the bundle's full licence text is the superseded v1.0 and summarising it as historical context.
- `ip_restrictions.restrictions` reduced to the v2.0-attributable statement (title and IP remain with the licensor; the licence is the governing instrument), with the v1.0 clauses removed rather than relabelled.

**Rationale:** The bundle's own curation note flags the v1.0 capture as retained chiefly for its DOI. Presenting a superseded instrument's clauses at length, in a slot that reads as the terms in force, misrepresents the current position even when each clause is individually quoted accurately. Attribution embedded inside a restriction value also violates the principle that a value should carry the content the field asks for, not commentary about its provenance.

#### F17. Fragment URIs on `id`-bearing sub-objects

**Finding:** Subset and file-collection identifiers extended the DOI resolver URL with fragments (`https://doi.org/10.60775/fairhub.3#training-split`, `...#cardiac_ecg`). A DOI resolver URL does not admit fragment sub-resources; these are generator constructions.

**Action: replaced with CURIE-style local identifiers** — `aireadi:split-train`, `aireadi:collection-cardiac_ecg`, etc.

**Rationale:** The `id` slot is required and must be populated; some identifier must be minted for sub-objects the bundle does not identify. A local CURIE is transparently a record-internal handle. A fragment on a resolvable DOI URL implies a resolvable sub-resource that does not exist.

---

### 2.3 Low severity

#### F18. `4 to 10 per cent` follow-up range — **corrected**

The healthsheet says "Approximately 4%"; NIH RePORTER, the README and the IRB protocol say "10% of the study cohort". Rendering as a range implies a stated interval. Rewritten to state both figures and attribute each: *"the healthsheet states approximately 4 per cent; the NIH RePORTER abstract, the dataset README and the IRB protocol state 10 per cent."*

#### F19. `special_populations` states absence — **removed**

Both entries asserted that no protected population is targeted and described the prospective Native Biodata Consortium engagement for a cohort not yet collected. The field asks which special populations are included; a negation does not answer it. Removed from both. The Native Biodata Consortium engagement is retained in `addressing_gaps`, where it describes a gap the project engages with rather than a population in the data.

#### F20–F21. Enum classification of biases and limitations — **retained, one adjustment**

The `bias_type` and `limitation_type` assignments are generator classification against controlled vocabularies the bundle does not use. Retained, because populating a required-shape enum from free-text evidence is the schema's intended use and the alternative is leaving the objects typeless. One change: the entry the audit flagged as `measurement_bias` was reclassified to `annotation_bias`→ no — it was **removed**, as the underlying evidence (multi-device imaging with varying operator involvement) describes a source of heterogeneity the bundle presents as a *mitigation* of device-specific bias, not as a bias. `selection_bias`, `representation_bias` and `sampling_bias` are retained; the bundle names volunteer/selection bias (BMJ protocol) and sampling bias (healthsheet) in terms close to the enum labels.

#### F22. `variables` — **removed from full, not added to core**

The 47 `VariableMetadata` objects were drawn from the BMJ protocol's clinical assay table, its device table, and the healthsheet device section. The bundle contains no variable dictionary for the released dataset; the IRB protocol references an uploaded "List of variables" that is not in the bundle. Several entries (genetic sequencing data, traffic and accident reports) are controlled-access items absent from the public release the record denotes.

**Action: removed from the full record.**

**Rationale:** This is the single largest deletion. The slot asks for metadata on variables, fields or columns *in the dataset*; what was supplied was a protocol-level measurement plan, partly describing data not in the referent. Retaining a subset would require the generator to adjudicate which protocol measurements reached the public v3.0.0 release, which the bundle does not state. The clinical assays, devices and measurement domains remain fully described in `collection_mechanisms`, `instances`, `file_collections` and `description`. Removing the slot loses the false precision of a column-level dictionary while losing no evidence.

#### F23. Sub-finding on `variables[46]` — **resolved by F22.**

#### F24. Contradictory booleans in `sensitive_elements` and `subpopulations` — **restructured**

Each slot carried two objects with opposite boolean values, distinguished only in prose as public versus controlled-access. Since the referent is one dataset, this reads as self-contradiction. Collapsed to one object each: `sensitive_elements_present: false` and `subpopulation_elements_present: false`, with the detail field stating that the withheld sex, race, ethnicity, five-digit ZIP, genetic and medication data are held in a separate controlled-access set that is not this referent.

#### F25. `is_deidentified.method` — **amended**

`method` stated "HIPAA Safe Harbor" while the structured `datasetDeIdentLevel` records `deIdentType: NoDeIdentification`. Changed to `HIPAA Safe Harbor (per the Nature Metabolism comment); the FAIRhub structured metadata records deIdentType as NoDeIdentification on the grounds that no identifiers were collected`. Both sources are now visible in the field that asserts.

#### F26. `conforms_to_schema` — **changed**

Was `https://schema.aireadi.org/v0.1.0/dataset_description.json`, the schema of a metadata *file*. Changed to `https://cds-specification.readthedocs.io/en/v0.1.1/` — the Clinical Dataset Structure, which the bundle states the dataset itself is organised under. `conforms_to` retains the fuller list of per-directory standards (OMOP CDM, DICOM, WFDB, Open mHealth, ESDS).

#### F27. `maintainers[1]` FAIRhub role — **retained, entity name moved into a declared field**

`role: other` retained; the enum has no platform/repository value. Per the v3 rule, the entity name was moved from prose into `maintainer_details` as its leading element rather than left implicit.

#### F28. `data_collectors` — **one object removed, four retained**

The fifth object described NIH funding of collector effort rather than a collector. Removed; the funding fact is already in `funders`. The remaining four are retained with `collector_details` as the substantive field, since `DataCollector` declares only `collector_details` and `role`.

#### F29. Parenthetical glosses inside URL strings — **corrected**

`external_resources[0].external_resources` items embedded commentary inside the URL (`https://docs.aireadi.org/ (documentation of the dataset...)`), rendering them non-dereferenceable. Glosses stripped; URLs are now bare. The descriptive content moved to the object's `description`.

#### F30. `license` composite value — **split**

Was `AI-READI custom license v2.0 (https://doi.org/10.5281/zenodo.17555036)`. Reduced to `AI-READI custom license v2.0`; the DOI is carried in `license_and_use_terms.license_terms`.

#### F31. `funders` grants grouped — **split into two objects**

`OT2OD032644` (with award title "Bridge2AI: Salutogenesis Data Generation Project", the only award the FAIRhub `fundingReference` names) is now one `FundingMechanism`; `P30DK035816` and `UL1TR003096` are a second, described as the institutional core and CTSA awards named in the BMJ funding statement. Per the v2 rule on distinct entities, and because the structured metadata draws this distinction.

#### F32. `version_access.version_details` — **mini-dataset sentence trimmed**

The "100 participants" figure appears only in a curator's note, not in a dataset source. The API's `data.child: 4` and the FAIRhub page's "A smaller version is available for pipeline development" are retained; the participant count is dropped.

#### F33. `related_datasets[2]` relationship direction — **changed to `has_part`**

`is_source_of` toward `10.60775/fairhub.4` asserted a derivation direction the bundle does not state. `data.child: 4` supports a part-whole reading; `has_part` is the closest declared type to what the field records.

#### F34. `acquisition_methods[5]` flag — **corrected**

EHR and Department of Licensing records were flagged `was_inferred_derived: true`. This is secondary-source retrieval, not inference from other data. Flag removed; `was_directly_observed: false` retained with the detail describing third-party record retrieval.

#### F35. `issued` fabricated time component — **corrected**

`2025-11-17T00:00:00Z` → `2025-11-17`. The bundle asserts a date, not a time.

#### F36. `sampling_strategies[0].strategies[3]` meta-comment — **removed**

The fourth entry recorded provenance reasoning ("The creators state in the healthsheet that...") in a list of strategies. Removed; the substantive point (the release contains all enrolled participants, so no sampling was applied at release) is already in `is_sample: false` and `strategies[0]`.

#### F37. FAIRhub as a collection mechanism — **removed**

FAIRhub is the upload, curation and sharing platform, not a collection instrument. Removed from `collection_mechanisms`; it remains in `preprocessing_strategies`, `distribution_formats` and `maintainers`.

#### F38. `extension_mechanism` inferred contribution channels — **removed**

The sentence proposing GitHub and Zenodo as contribution routes is generator inference; the bundle states plainly that no mechanism exists. Reduced to the bundle's statement. `contribution_url` left unpopulated.

#### F39. `language` — **retained unchanged**

`en` is directly stated in `datasetDescription.language`. The audit's note was observational.

#### F40. `status: published` — **removed**

Not stated in the bundle. FAIRhub records the *study* as "Enrolling by invitation" and the *dataset* as available; neither licenses the term "published" for the dataset's status slot. Release date, version and availability are recorded in `issued`, `version` and `distribution_dates`.

#### F41. Healthsheet-as-datasheet — **acknowledged, no action**

The audit's structural note stands and is recorded here rather than acted on: a substantial fraction of both records derives from the FAIRhub healthsheet, which is itself a datasheet-style artifact. Material so derived is closer to transcription than to extraction. This is a property of the declared bundle, not a defect in the records, and no remedy is available within the arm's constraints.

---

## 3. Summary of changes

| | Full | Core |
|---|---|---|
| Slots before | 71 | 44 |
| Slots removed | 5 | 2 |
| Slots added | 0 | 12 |
| Slots amended in place | 19 | 17 |
| **Slots after** | **66** | **54** |

**Removed from full:** `variables`, `citation`, `status`, `special_populations` (sub-field of retained `human_subject_research`), `conforms_to_schema` retained but re-valued.
Counted removals: `variables`, `citation`, `status`, plus `data_protection_impacts` was never present in full and is now absent from both, plus `confidentiality_level` (sub-field).

**Removed from core:** `distributions` (fabricated slot), `data_protection_impacts`.

**Added to core:** `file_collections`, `total_file_count`, `total_size_bytes`, `splits`, `subsets`, `relationships`, `related_datasets`, `direct_collection`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation`, `third_party_sharing`.

`variables` was **not** added to core, consistent with its removal from full.

---

## 4. Left as-is, with reasons

- **Twenty individual PI `Creator` objects.** Each is named with an affiliation in the bundle. The organisational creator was added alongside them rather than replacing them.
- **`bias_type` and `limitation_type` enum assignments.** Generator classification, but the classification is the schema's purpose and the free-text descriptions preserve the bundle's own wording.
- **`data_use_permission: disease_specific_research`.** Single-valued enum; accurate for the referent; the two-tier arrangement is now explicit in the adjacent free-text.
- **`maintainers[1].role: other`.** No better enum value exists for a data-sharing platform.
- **The prominence of healthsheet-derived content throughout.** Acknowledged under F41; no remedy available.
- **`id` as `https://doi.org/10.60775/fairhub.3` alongside `doi` as the bare DOI.** The redundancy is deliberate: `id` requires a URI-or-CURIE, `doi` requires the DOI string. Both are supported.

---

## 5. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| `AI_READI_d4d.yaml` | `data_sheets_schema_all.yaml` | `Dataset` | **pass** |
| `AI_READI_d4d_core.yaml` | `data_sheets_schema_core_all.yaml` | `CoreDataset` | **pass** |

The core record did not validate before reconciliation, owing to the fabricated `distributions` slot. It validates after its removal.

---

## 6. Outcome

**Reconciled.** All three high-severity findings corrected. Fifteen medium-severity findings: eleven corrected, four retained with amendment or with reasons recorded above. Twenty-three low-severity findings: nineteen corrected, four retained with reasons.

The two records now denote the same referent, populate the same slots wherever both schemas declare them and the bundle answers them, and carry no claim the declared bundle does not support. No previously generated D4D record was read or consulted at any phase.