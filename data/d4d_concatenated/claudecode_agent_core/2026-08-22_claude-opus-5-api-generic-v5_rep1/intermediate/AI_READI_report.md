# AI-READI D4D Reconciliation Report

**Version label:** `2026-08-22_claude-opus-5-api-generic-v5_rep1`
**Arm:** BASELINE (input documents only)
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Scope and method

The Phase 3 audit returned 34 findings across both records: 3 high, 15 medium and 16 low severity. Each was assessed against the declared input bundle (`data/preprocessed/concatenated/AI_READI_preprocessed.txt`), the schema digest for `Dataset`/`CoreDataset`, and the uniform decision rules in the generation prompt.

Findings were resolved in one of four ways:

- **Fixed** — the record was changed.
- **Fixed by omission** — an unsupported or misleading value was removed rather than replaced.
- **Documented** — the value was retained and a `source_caveats` or `notes` entry was added recording the limitation.
- **Left as-is** — the audit's premise did not hold, or the existing treatment was already correct.

The comparison below is drawn from the original and reconciled records as supplied. Nothing is reported as changed that cannot be located in that comparison.

---

## 2. High-severity findings

### 2.1 Core `distributions` — slot and object shape not in the digest (fixed, partially)

**Finding.** The core record carried a `distributions` block whose slot name and object keys (`path`, `format`, `media_type`, `bytes`, `conforms_to`, `conforms_to_standard`, `notes`) do not appear in the supplied `Dataset`/`CoreDataset` slot inventory or in the object-range list. The full record carries the same material in `file_collections` (range `FileCollection`, required `id`, accepting `path`, `file_count`, `total_bytes`, `collection_type`).

**Resolution.** The `distributions` block is **still present** in the reconciled core record. It was not removed. The supplied digest describes the *full* `Dataset` class and its object ranges; it does not enumerate the core schema's own slot list, so the digest alone cannot establish that `distributions`/`CoreDistribution` is undeclared in `data_sheets_schema_core_all.yaml`. Removing a block on the strength of a digest that does not cover the relevant class would have been the wrong call, and the core record validated against the core schema. The block was therefore retained and corrected in the two respects the bundle *does* settle — see 2.2 below.

**Residual risk.** The report cannot confirm from the material supplied that the object keys used match the declared `CoreDistribution` range. Validation passing is the only evidence available on this point.

### 2.2 Core `distributions[*].format` — unsupported `TXT` values (fixed by omission)

**Finding.** `format: TXT` was asserted for `cardiac_ecg/` (WFDB signal + header files) and `environment/` (ESDS ASCII guidelines). The bundle states only that these directories follow WFDB and the NASA ASCII File Format Guidelines respectively; neither source names TXT, and neither names any file extension.

**Resolution — fixed by omission.** Both `format: TXT` values were removed. Comparing the two core records:

| Distribution | Original | Reconciled |
|---|---|---|
| `cardiac_ecg/` | `format: TXT` | no `format`; `notes` added: "WFDB comprises paired signal and header files. The bundle names no file extension, container format or media type for these files, and WFDB has no representation in the `format` or `media_type` enumerations, so both slots are omitted." |
| `environment/` | `format: TXT` | no `format`; `notes` added: "The bundle states only that these files follow the ESDS ASCII file format guidelines and names no specific delimited or plain-text format, so the `format` and `media_type` slots are omitted rather than approximated." |

This is the prompt's omission-over-inference rule applied directly: an absent slot is the correct answer where the evidence is absent.

The audit also noted the record's own concession that DICOM has no representation in the enumeration. That concession was retained in the four imaging distributions' `notes`, and the corresponding `source_caveats` item (14) was expanded to cover WFDB and ESDS as well as DICOM.

**Additionally**, the two Open mHealth directories (`wearable_activity_monitor/`, `wearable_blood_glucose/`) retain `format: JSON` and `media_type: application/json`, but each now carries a new `source_caveats` recording that JSON is *inferred* from the dataset-level format list and the Open mHealth JSON schema library rather than stated for those directories. The inference is disclosed rather than hidden.

### 2.3 Full `file_collections[*].conforms_to_standard: CDS` (left as-is)

**Finding.** Flagged for completeness only; the audit confirmed `CDS` is a permitted value in the `conforms_to_standard` enumeration.

**Resolution — left as-is.** No change. The value is valid per the digest. The audit's residual concern — whether the schema's `CDS` means "Clinical Data Standard" or "Clinical Dataset Structure" — cannot be settled from the material supplied, and the bundle consistently uses "Clinical Dataset Structure (CDS) v0.1.1", which is what the prose in `conforms_to` records.

---

## 3. Identifier findings

### 3.1 Minted grant identifiers on a foreign RePORTER URL (fixed by omission)

**Finding — medium.** Grants P30DK035816 and UL1TR003096 were given identifiers minted as fragments on the RePORTER project-details URL for a *different* award (OT2OD032644). A fragment on another grant's page does not name these grants and makes a misleading claim about that RePORTER record. Per the v5 minting rule, these grants have referents outside the record, so the identifier must come from the evidence or be omitted.

**Resolution — fixed by omission in both records.** The `FundingMechanism` object that bundled the two minted grants was replaced with two separate objects, each naming its grant in prose and carrying no `Grant` object:

- Original (both records): one funder object with `grants:` containing two entries with `id: .../10885481#P30DK035816` and `id: .../10885481#UL1TR003096`.
- Reconciled (both records): two funder objects, each `grantor: National Institutes of Health`, each with a `notes` naming the grant number and its source, and each with a `source_caveats` reading "No award identifier or URI for [grant] appears in the bundle, so no grant identifier is recorded; the grant number is given in prose only."

The full record's P30/UL1 caveat additionally disambiguates UL1TR003096 from UL1TR001442, which appears in the Nature Metabolism competing-interests statement as a different author's funding.

A new `source_caveats` item (14 in the full record, 15 in the core) records the general policy: only the primary Bridge2AI award has award URIs in the bundle; the other funders carry no `Grant` object rather than a minted one.

### 3.2 Project homepage used as Creator identifier (documented)

**Finding — medium.** `https://aireadi.org/` is used as the `id` of the Creator object for the AI-READI Consortium. The bundle attests this URL as the project website, not as an identifier for the consortium as an agent.

**Resolution — documented, value retained.** No registry identifier for the consortium appears anywhere in the bundle, and the v5 rule forbids supplying one from outside the evidence. `uriorcurie` admits a URI where no declared prefix covers the entity, so the homepage is defensible as a fallback. The original `source_caveats` on this object addressed only the affiliations; the reconciled version adds: "The identifier used is the project website, which the bundle attests as the project's web presence rather than as a registry identifier for the consortium; no registry identifier for the consortium appears anywhere in the bundle." A parallel item was added to the record-level `source_caveats` (item 15 full, 16 core).

### 3.3 DOI-fragment identifiers for subsets and file collections (left as-is)

**Finding — low.** `doi:10.60775/fairhub.3#training-split` and similar fragment identifiers are unlikely to resolve, since DOI resolution admits no fragment component.

**Resolution — left as-is.** These identifiers are still present in both records, unchanged. They name parts of this dataset that exist nowhere outside the record, so the v5 minting rule applies and requires a fragment on an attested identifier. The DOI is the attested identifier the bundle supplies. Non-resolvability of the fragment form is a consequence of the rule, not a violation of it; substituting a resolvable URL would break the traceability the rule exists to preserve.

### 3.4 `publisher` as a homepage URL (left as-is)

**Finding — low.** `https://fairhub.io/` is a website rather than an entity identifier for the publishing organization.

**Resolution — left as-is.** Unchanged in both records. The bundle gives only `publisherName: FAIRhub` with no registry identifier. Supplying one from outside the evidence is prohibited; the `uri` half of `uriorcurie` covers the fallback.

### 3.5 Mixed identifier forms in `related_datasets` (documented)

**Finding — low.** The slot mixes DOI CURIEs with two documentation URLs, and the URLs name non-dataset targets that also appear in `external_resources`.

**Resolution — documented in both records.** The entries were retained, reordered so the DOI-targeted relationships come first, and each URL-targeted entry gained a `source_caveats`: "This target is a documentation site rather than a dataset. It is recorded here because the dataset description declares it as a related identifier with relation type IsDocumentedBy; it also appears under external_resources." The FAIRhub dataset description declares both as `relatedIdentifier` entries with `relationType: IsDocumentedBy`, so recording them is faithful to the source; the duplication with `external_resources` is now disclosed rather than silent.

---

## 4. Creators — collapsed multivalued slot (fixed)

**Finding — medium.** A single `Creator` object collapsed an organizational consortium, a named PI and eight institutions, while the bundle names sixteen Study Principal Investigators individually, each with an ORCID and a stated affiliation. `credit_roles` was omitted although the bundle supplies role information.

**Resolution — fixed in both records.** The single object was expanded. Comparing:

- **Original (both records):** one `Creator` with `id: https://aireadi.org/`, `principal_investigator: Aaron Lee`, and eight `affiliations`.
- **Reconciled full record:** nineteen `Creator` objects — one organizational (consortium), sixteen naming individual Study Principal Investigators with their ORCID and FAIRhub-recorded affiliation, one recording the three data collection sites, and one recording the collaborator list.
- **Reconciled core record:** eighteen `Creator` objects — the same, with the separate data-collection-sites object folded into the collaborators object (its content is preserved in that object's `notes`).

`credit_roles` was populated where the bundle supports it: `supervision` and `project_administration` for Aaron Lee (responsible party and central contact), `writing_original_draft` for the five PIs named on the Nature Metabolism Writing Committee, and `data_curation` additionally for Bhavesh Patel.

Two per-object `source_caveats` were added recording affiliation conflicts the ranking cannot fully settle: Aaron Lee (FAIRhub gives Washington University in St. Louis; RO-Crate gives University of Washington — both tier 1) and Cecilia S. Lee (FAIRhub gives Washington University in St. Louis; Nature Metabolism gives University of Washington — tier 1 preferred).

The full record's data-collection-sites object carries its own `source_caveats` acknowledging that `Creator` has no slot for an institution acting in a collection role without an associated person, and that the study PI is repeated there as a shape workaround rather than as an authorship claim.

---

## 5. Slots present in core but absent from full (all fixed)

The audit identified seven cases where the core record stated content the full record did not — simultaneously a full-record omission and a core-states-more violation. All seven were resolved by **adding the slot to the full record**, since the bundle supports each.

| Slot | Bundle support | Now in full record |
|---|---|---|
| `existing_uses` | healthsheet uses §1 ("No"); FAIRhub API `cited: 0`, `viewCount: 24636` | Yes — one object with `examples` and `notes` |
| `use_repository` | healthsheet uses §3 ("No") | Yes — with `repository_url: https://fairhub.io/datasets/3` |
| `other_tasks` | Nature Metabolism (CDS, FAIRhub reuse by future DGPs) | Yes — one `task_details` |
| `data_protection_impacts` | healthsheet collection §12 ("No") | Yes — one `impact_details` |
| `extension_mechanism` | healthsheet maintenance §7 ("No"); GitHub org in README | Yes — with `contribution_url: https://github.com/AI-READI` |
| `labeling_strategies` | healthsheet labeling section (all N/A); RO-Crate `rai:dataAnnotationProtocol` | Yes — one `labeling_details` |
| `regulatory_restrictions.confidentiality_level` | RO-Crate "HL7:2N (normal)" + access conditions | Yes — `restricted`, with the mapping disclosed in `notes` |

The `confidentiality_level: restricted` mapping is an interpretation the bundle does not itself make. It is retained in both records with the interpretive step stated in `regulatory_restrictions.notes`: the enumerated value reflects the access conditions (verified-ID login, use attestation, restrictive license) while the RO-Crate's own HL7 scale value is quoted verbatim alongside it.

Both `extension_mechanism` and `use_repository` also gained URL fields in the core record relative to its original, matching the full record.

---

## 6. Core record — content displaced from dropped slots (fixed)

The core schema has no `collection_notifications`, `participant_privacy` or `participant_compensation`. The original core record handled this by folding their content into unrelated fields. Three cases were corrected.

### 6.1 `informed_consent[0].withdrawal_mechanism` (fixed)

- **Original:** withdrawal text followed by "Participants were notified of the data collection in advance: every individual was aware of it, since this was active, prospective collection rather than passive collection or secondary use of existing data."
- **Reconciled:** the notification sentence removed; `withdrawal_mechanism` now answers only the question it asks. The notification content moved to the record-level `notes`, expanded with the invitation-letter and REDCap-interface detail from the bundle.

### 6.2 `is_deidentified.deidentification_details` (fixed)

- **Original:** participant-identifier scheme, re-identification risk and watermarking were appended to `deidentification_details`, which is the field for de-identification method.
- **Reconciled:** `deidentification_details` now ends at "The RO-Crate records the dataset as deidentified." A new `notes` field on the same object carries the privacy material, prefaced "Related privacy measures, recorded here because the core schema has no separate slot for them", and expanded to include the device-selection and storage protections the original core record had dropped entirely.

### 6.3 Participant compensation (fixed)

- **Original:** buried mid-paragraph in the record-level `notes`, one sentence.
- **Reconciled:** promoted to its own labelled section within `notes` ("Participant compensation.") with the full detail — amount, funding source, timing, non-proration, travel reimbursement cap, rideshare assistance. The full record carries this in `participant_compensation` with `compensation_provided`, `compensation_amount`, `compensation_type`, `compensation_rationale` and a new `retention_incentives` field.

### 6.4 `citation` dropped from core (fixed)

- **Original core:** no `citation` slot; the citation text sat in `notes`.
- **Reconciled core:** still no `citation` slot, but the citation is now the *first* labelled item in `notes` ("Citation.") rather than mid-paragraph, and `existing_uses[0].notes` cross-references it. The full record retains `citation` as a top-level slot. This remains an asymmetry between the paired records; the core schema's slot inventory was not available to confirm whether `citation` is declared there.

---

## 7. Structured fields left empty while content sat in prose (fixed)

### 7.1 `subsets` — DataSubset composition (fixed, full record)

- **Original:** three `DataSubset` objects each carrying `id`, `name`, `description`, `is_data_split`, `is_subpopulation`, with all demographic composition written into the `description` prose.
- **Reconciled:** `description` reduced to the partition's role and share; composition moved into declared structured fields — an `instances` entry with `counts` (1576 / 352 / 352) and four `subpopulations` entries per subset (race/ethnicity, sex, diabetes status, age), each with `identification` and `distribution`.

### 7.2 `collection_timeframes` — empty date fields (fixed, both records)

- **Original:** two objects; the second populated only `timeframe_details` and `source_caveats` while naming six dates in prose.
- **Reconciled:** five objects, four of which populate `start_date` and/or `end_date`: 2023-07-19/2025-05-01 (v3.0.0 collection), 2023-07-18/2023-11-30 (pilot), 2023-12-01 (formal collection start), 2022-09-01/2025-08-31 (award period), 2023-07-19/2027-01-01 (study status dates). The tier conflict caveat is retained on the last object.

### 7.3 `at_risk_populations.special_protections` (documented)

**Finding — low.** The value states eligibility criteria rather than protections.

**Resolution — documented.** The value is unchanged in both records. The full inclusion/exclusion criteria were added to `sampling_strategies.strategies` as a new bullet, where they answer the field directly, and the core record's `at_risk_populations.source_caveats` now notes "those criteria are also recorded under sampling_strategies". Given `at_risk_groups_included: false`, the statement that the groups were excluded *is* the protection, so the value was not removed.

---

## 8. Vocabulary coverage (fixed)

### 8.1 `instances.data_substrate` and `data_topic` (fixed, full record)

**Finding — low.** `data_substrate` omitted entirely; a single `data_topic` (`B2AI_TOPIC:43`, Diabetes) for a nine-modality dataset.

**Resolution — fixed in the full record.** `instances` expanded from one object to twelve. The participant-level object retains `counts: 2280`, `data_topic: B2AI_TOPIC:43`, `label: false` and gains a `missing_information` entry. Eleven further objects cover the modalities, each with the fitting substrate and topic terms:

| Modality | `data_substrate` | `data_topic` |
|---|---|---|
| OMOP clinical | 6 (CSV) | 4 (Clinical Observations) |
| Survey responses | 80 (Questionnaire response data) | 31 (Survey) |
| SDoH responses | — | 29 (SDoH) |
| 12-lead ECG | 49 (Waveform Data) | 10 (EKG) |
| Retinal photography | 65 (Retinal Image) | 24 (Ophthalmic Imaging) |
| OCT | 67 | 24 |
| OCTA | 68 | 24 |
| FLIO | 66 | 24 |
| CGM | 78 (Glucose monitoring data) | 38 (Glucose Monitoring) |
| Activity monitor | 73 (Physical activity data) | 39 (Activity Monitoring) |
| Environmental sensor | 69 (Time-series data) | 11 (Environment) |

**Core record:** the single participant-level `Instance` was retained, with a new `source_caveats` explaining that the participant-level instance spans nine data types with different substrates so no single term applies, and pointing to the full record for the per-modality enumeration. The core record therefore states strictly less than the full record on this point, as required.

### 8.2 `variables` — partial coverage (fixed, full record)

**Finding — low.** 33 `VariableMetadata` objects against roughly 40 laboratory analytes with units and reference ranges in Table 2, plus eleven named spectral channels; selection basis not stated.

**Resolution — fixed.** Expanded to approximately 75 objects. Added: the full serum chemistry panel (sodium, potassium, chloride, CO2, calcium, total protein, albumin, globulin, A/G ratio, bilirubin, ALP, AST, ALT, BUN, BUN/creatinine ratio), the full lipid panel, the complete blood count (WBC, RBC, haemoglobin, haematocrit, MCV, MCH, MCHC, RDW, platelets), urine creatinine, autorefraction sphere and cylinder, ECG chair position, stress level, calorie, tracker wrist, dominant hand, environmental sensor location, and the four PM channels split individually.

Reference ranges from Table 2 now populate `minimum_value`/`maximum_value` where the range is unconditional, with a `notes` clarifying "Minimum and maximum record the laboratory reference range, not observed values." Ranges that vary by sex or age (creatinine, troponin-T, ALP, ALT, NT-proBNP) are recorded in `notes` rather than forced into the numeric fields.

`multispectral_light_intensity` retains `data_type: array` with a `notes` recording that eleven measurements exist but the individual channel wavelengths and units are not enumerated in the bundle. The four PM variables and the other environmental variables each carry "Units are not stated in the bundle."

The MoCA object gained a `quality_notes` field carrying the bundle's stated caveats about training requirements, education and socioeconomic effects.

**Core record:** `variables` is absent from both the original and the reconciled core record. No change.

---

## 9. Format vocabulary and file collections

### 9.1 Inconsistent format vocabulary between records (partially fixed)

**Finding — low.** The paired records used `Markdown` (full) vs `MD` (core), and `DICOM`/`CSV`/`JSON` (full) vs `TXT`/`CSV`/`JSON` (core) for the same files.

**Resolution — partially fixed.** The `TXT` values were removed (see 2.2). The `Markdown`/`MD` divergence persists: the full record's `distribution_formats` uses `format: Markdown`, the core record's uses `format: MD`. This was not changed because the two records validate against different schemas whose `format` ranges may differ, and the digest supplied does not constrain `DistributionFormat.format` for either.

Both records' `distribution_formats` were expanded from four entries to six or seven, adding WFDB, the ESDS delimited-ASCII entry, and (full record only) plain text for LICENSE.txt. The full record's DICOM entry now records that the imaging directories account for 332,089 of 356,343 files.

### 9.2 Core `distribution_formats[3]` — commentary-only object (fixed)

- **Original core:** a `DistributionFormat` object carrying only a `notes` explaining that DICOM cannot be expressed in the enumeration — an entry that names no format.
- **Reconciled core:** replaced with `format: DICOM` / `media_type: application/dicom` as a first-class entry, since the audit itself confirms DICOM appears in the bundle's format list and the enumeration constraint on `DistributionFormat.format` is not established by the digest. A separate trailing commentary object remains, recording the four release formats the dataset description lists.

### 9.3 Root metadata file collection (fixed, full record)

The `#root-metadata` `FileCollection` gained "Mixed Markdown, JSON and TSV content, so no single file format applies to the collection" in its `description`, matching the disclosure the core record's `./` distribution already carried.

---

## 10. Arithmetic and totals (fixed)

**Finding — low.** `source_caveats` item 12 asserted the per-directory sizes sum to 3,815,969,360,064 bytes, which does not reconcile with the source figures.

**Resolution — fixed by omission of the derived figure.** The reconciled item 12 in both records no longer asserts any byte sum. It now states the attested API figures (3,815,969,779,678 bytes; 356,343 files), notes that the nine per-directory entries account for 356,334 files with the remaining nine being root metadata files, and states explicitly: "the per-directory byte figures are recorded individually on each file collection and no derived sum of them is asserted here."

This also resolves the internal tension the audit noted between `total_size_bytes` and the caveat: the record now asserts only the attested total and the attested per-directory figures, with no arithmetic bridging them.

---

## 11. Other changes

### 11.1 `keywords` — study keywords merged with dataset subjects (fixed)

- **Original (both records):** nine keywords — the seven FAIRhub dataset subjects plus "Data Sharing" and "Exploratory Data Collection" from `study_description.json`.
- **Reconciled (both records):** seven keywords, exactly the FAIRhub dataset `subject` list. The two study-level keywords were removed; the bundle distinguishes dataset subjects from study keywords, and merging them attributed study metadata to the dataset.

### 11.2 `license` — prose composite (fixed)

- **Original (both records):** `AI-READI custom license v2.0 (AI-READI Data License Agreement, Version 2.0)`.
- **Reconciled (both records):** `AI-READI custom license v2.0` — the `rightsName` verbatim from the dataset description. The parenthetical restated the same name from the PDF title. The `rightsURI` is now recorded in `license_and_use_terms.license_terms`, which gained a closing sentence naming both the rights name and the rights URI.

### 11.3 `data_governance.committee_members` (documented)

**Finding — low.** Omitted although sixteen PIs with ORCIDs are named in the study description.

**Resolution — documented.** The slot remains unpopulated in both records. The bundle does not state that the PIs constitute the governance committee, and asserting membership would be inference. The `source_caveats` on `data_governance` gained: "No membership of either body is recorded in the bundle, so committee_members is left unpopulated; the sixteen individuals named in the study description as Study Principal Investigators are recorded under creators."

### 11.4 `download_url` (documented)

**Finding — low.** Omitted; the RO-Crate supplies `conditionsOfAccess: https://fairhub.io/datasets/3/access`.

**Resolution — documented, slot still omitted.** An access-gated landing page is not a direct download URL, and the slot's description distinguishes the two. The access URL was surfaced more prominently: `data_governance.access_review_process` now states "The access route is https://fairhub.io/datasets/3/access", and `third_party_sharing` names it as well.

### 11.5 `notes` — placeable content (partially fixed)

**Finding — low.** The full record's `notes` carried return-of-results procedures and the biorepository description, some of which is placeable elsewhere.

**Resolution — partially fixed.** The full record's `notes` is now organized under explicit labels ("Biorepository.", "Return of results.") and expanded with detail from the bundle (PAXgene stability window, storage temperatures, referral pathways). It was not relocated: the biorepository is explicitly *not part of this dataset*, so placing it in `related_datasets` or `external_resources` would misrepresent it as a related data resource. Return-of-results is a study procedure with no fitting slot in the `Dataset` inventory. The `notes` guidance permits residual content after every fitting slot is used, which is the case here.

### 11.6 Additions beyond the audit findings

Several strengthenings were made where the reconciliation pass surfaced supported material the original records omitted:

- `preprocessing_strategies` gained an entry recording that no instances were excluded at preprocessing time (healthsheet preprocessing §4).
- `data_collectors` (full record) gained a "Research interns" entry with the inaugural cohort composition.
- `collection_mechanisms` entries gained device specifications from the healthsheet devices section (field of view, sensor resolution, scan rates, wavelength, luminance and illuminance ranges, sensor component datasheets).
- `sampling_strategies` gained the inclusion/exclusion criteria and the observational-cohort/cross-sectional design statement.
- `external_resources` gained the internship program URL and the REDCap forms PDF.
- `participant_privacy` (full record) gained the encrypted-storage protection from the IRB protocol form.
- `informed_consent.consent_documentation` gained the automatic-email-of-signed-consent detail.
- `updates` corrected "added year-two and year-three data" to the specific figure "added 1,213 further participants", matching the README change table.

---

## 12. Findings left as-is, with reason

| Finding | Severity | Reason |
|---|---|---|
| Core `distributions` slot/shape not in digest | high | Digest covers the full `Dataset` class, not the core schema's slot list; cannot establish the slot is undeclared. Block retained; the two evidence-settled defects within it were fixed. |
| Full `conforms_to_standard: CDS` | high (flagged for completeness) | `CDS` is a permitted enum value per the digest. |
| DOI-fragment subset/collection ids | low | Required by the v5 minting rule; the DOI is the only attested base. Non-resolvability is a consequence of the rule. |
| `publisher` as homepage URL | low | No registry identifier in the bundle; supplying one is prohibited. |
| `at_risk_populations.special_protections` content | low | Exclusion *is* the protection given `at_risk_groups_included: false`; criteria additionally placed in `sampling_strategies`. |
| `Markdown` vs `MD` divergence | low | The two records validate against different schemas; the digest does not constrain `DistributionFormat.format` for either. |
| `total_size_bytes` value | low | The figure is attested by the FAIRhub API; only the unreconcilable derived sum was removed. |
| `conforms_to_class` values | low | Confirmed correct by the audit (`Dataset` / `CoreDataset`). |
| `download_url` omission | low | Access-gated landing page is not a download URL; the access route is recorded in the governance and sharing slots. |
| `data_governance.committee_members` omission | low | Membership not stated in the bundle. |
| Core `citation` omission | medium | Core schema slot inventory not available; citation is surfaced as the first item in `notes` and cross-referenced from `existing_uses`. |

---

## 13. Outcome

| | Full | Core |
|---|---|---|
| Slots populated | 71 | 65 |
| Validated | Yes | Yes |

**Core ⊆ full check:** every slot present in the core record is now also present in the full record. The seven previously core-only slots (`existing_uses`, `use_repository`, `other_tasks`, `data_protection_impacts`, `extension_mechanism`, `labeling_strategies`, `regulatory_restrictions.confidentiality_level`) were added to the full record. The core record states nothing the full record does not.

**Referent consistency:** both records describe the same referent — version 3.0.0 of the *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, DOI `10.60775/fairhub.3`, as published on FAIRhub on 17 November 2025. Study-level facts (recruitment target of 4,000, follow-up plans, biorepository) are recorded as context and marked as such rather than attributed to this release.

**Provenance:** all facts derive from the declared bundle. No prior D4D record was consulted. No identifier for an external entity was supplied from outside the evidence; the two minted grant identifiers that violated this were removed.

**Residual risks, disclosed:**
1. The core `distributions` block's conformance to its declared range cannot be confirmed from the material supplied; validation passing is the only evidence.
2. `Markdown` / `MD` remains divergent between the paired records.
3. `citation` is a top-level slot in the full record and prose in the core record.
4. The Aaron Lee and Cecilia S. Lee affiliation conflicts are tier-1-vs-tier-1 and tier-1-vs-tier-3 respectively; both are recorded with the preferred value stated and the disagreement disclosed.