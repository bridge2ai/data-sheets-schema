# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-19_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Audit input:** Phase 3 source/provenance audit, 52 findings (high/medium/low)

---

## 1. Summary of outcome

The audit found no fabricated dataset facts. Every substantive claim in both records traces to the declared bundle. The defects were structural and interpretive: schema-shape errors, identifier-form errors, false identity bindings, absence-recording values in slots that should have been omitted, collapsed multivalued lists, and two boolean assertions that contradicted their own notes.

Changes were made in four families:

1. **Identity integrity** — removal of email addresses used as `uriorcurie` identifiers, and removal of a shared project mailbox bound as the identity of a named individual.
2. **Boolean/enum truthfulness** — two flags flipped and one enum changed where the asserted value contradicted the record's own evidence or was reasoned rather than stated.
3. **Slot discipline** — absence-recording objects dropped, misfiled content moved to the slot it answers, collapsed lists split.
4. **Core/full parity** — the core record's `distributions` entries corrected to list-valued `conforms_to_standard`, and the six slots the core had folded into a single `informed_consent.notes` blob accounted for explicitly.

Nine findings were left as-is; each is listed in §4 with the reason.

---

## 2. Changes made — full record

### 2.1 Identifiers and identity (audit findings: `ethical_reviews[0].contact_person.id`, `data_governance.committee_contact`, `license_and_use_terms.contact_person`, `regulatory_restrictions.governance_committee_contact`, `funders[1..2].grants[0].id`)

Four `Person` objects carried bare email addresses as `id`, which is not a valid `uriorcurie`. Three of those four bound `contact@aireadi.org` — a shared project mailbox — as the identity of **Aaron Y. Lee**, a named individual for whom the bundle supplies an ORCID. That is a false identity claim, not merely a form error.

In all four cases the object was replaced with the scalar name, because the containing slots (`contact_person`, `committee_contact`, `governance_committee_contact`) accept a string in the reconciled shape used here, and the identifying detail was moved to the sibling `notes`:

- `ethical_reviews[0].contact_person` — was a `Person` with `id: hsdrely@uw.edu`; now the scalar `IRB Reliance Team, Human Subjects Division, University of Washington`, with `mailto:hsdrely@uw.edu` and the postal address moved to `ethical_reviews[0].notes`.
- `data_governance.committee_contact` — was a `Person` with `id: contact@aireadi.org`, `name: Aaron Y. Lee`; now the scalar `Aaron Y. Lee`, with the ORCID and mailbox moved to `data_governance.notes`.
- `license_and_use_terms.contact_person` — same treatment; ORCID and mailbox moved to `license_and_use_terms.notes`.
- `regulatory_restrictions.governance_committee_contact` — same treatment; a new `regulatory_restrictions.notes` added to hold the ORCID and mailbox.

`creators[0].principal_investigator` was likewise reduced from a `Person` object to the scalar `Aaron Y. Lee`, with the ORCID and role description moved to `creators[0].notes`. The audit's separate complaint that this object's `description` carried source commentary about the two conflicting affiliations was resolved by moving that commentary into `creators[0].source_caveats`, which now states explicitly that FAIRhub and the RO-Crate disagree and that neither outranks the other (both are tier 1).

Two grant `id` values were bare award numbers (`P30DK035816`, `UL1TR003096`), which are neither URIs nor CURIEs. Both are now resolvable NIH RePORTER search URLs constructed from the stated award numbers, with a `notes` on each funder recording that no award-specific URL appears in the bundle and that the identifier is a constructed search reference. The award numbers themselves are also preserved verbatim in each grant's `description`, so nothing is lost if the constructed URL is judged unsatisfactory.

### 2.2 Booleans and enums contradicting their own evidence

**`is_deidentified.identifiable_elements_present`: `false` → `true`.** The record's `id` denotes the whole dataset, which per the healthsheet includes a controlled tier retaining 5-digit zip code, genetic sequencing data, race/ethnicity and motor vehicle records. `false` contradicted `sensitive_elements`, which correctly emits one `false` object (public) and one `true` object (controlled). The flag now reads `true` for the dataset as a whole, and `method`, `identifiers_removed` and `deidentification_details` were rewritten to scope the Safe Harbor treatment explicitly to the public subset and to state that for the public subset alone the flag would be `false`.

**`subpopulations[0].subpopulation_elements_present`: `true` → `false`.** The object's own note conceded that the tier-1 healthsheet answers "No" to whether the dataset identifies demographic sub-populations. The boolean now follows the tier-1 answer. `identification` was rewritten to say the cohort is stratified on these axes but the public release carries no per-instance labels; `distribution` now states that the counts come from the README split table, which describes the cohort rather than released labels.

**`regulatory_restrictions.hipaa_compliant`: `compliant` → `not_applicable`.** No source asserts HIPAA compliance as a status. FAIRhub states only that the team checked no HIPAA-identifiable data were present; Nature Metabolism states the public set is Safe-Harbor-stripped. Released public data are therefore not PHI, and HIPAA does not attach. `source_caveats` was expanded to set out this reasoning.

**`regulatory_restrictions.confidentiality_level`: left at `restricted`,** but see §4.

### 2.3 Absence-recording values removed

Seven slots held values whose content was a statement that the thing does not exist. Per the v2 rule, such a value has not answered the field. The following top-level slots were **removed entirely** from the full record:

- `existing_uses` (was: "the dataset had not yet been used for any tasks")
- `use_repository` (was: "No repository ... exists beyond Google Scholar")
- `imputation_protocols` (was: "No imputation protocol is described")
- `annotation_analyses` (was: "Not applicable: no labels were provided")
- `data_protection_impacts` (was: "No data protection impact analysis has been conducted")
- `errata` (was: "No erratum exists")
- `machine_annotation_tools` (see §2.4)

`labeling_strategies` was **retained**: unlike the others, its value describes a positive methodological choice — that the dataset is deliberately hypothesis-agnostic and unlabeled — rather than merely recording an absence.

### 2.4 Content moved to the slot it answers

**`machine_annotation_tools` → `cleaning_strategies`.** The single entry was the OMOP CDM Data Quality Dashboard, which is a data-quality checking tool, not an annotation tool; the object's own `tool_descriptions` opened by saying no annotation tools were used. The slot was removed and a new `cleaning_strategies` entry added carrying the DQD, using the `used_software` field (available on every object per the digest) with `id: https://ohdsi.github.io/DataQualityDashboard/`.

**`distribution_formats[6]` removed.** The entry `format: Cloud object storage access` was an access route (Azure Storage), not a format. The remaining six entries now each carry a `notes` distinguishing the four media types listed in the FAIRhub `format` array (DICOM, CSV, JSON, Markdown) from the two evidenced only in the dataset structure description (TSV, WFDB).

**`acquisition_methods[3]` → `collection_mechanisms`.** The EHR ICD-10 screening entry conflated recruitment with instance acquisition; no released instance data derive from it. It was removed from `acquisition_methods` and re-expressed as a final `collection_mechanisms` entry that states explicitly it served recruitment rather than acquisition. `direct_collection[1]` retains the EHR-screening fact with `is_direct: false`, so the recruitment pathway is still recorded.

### 2.5 Collapsed multivalued lists split

- **`known_biases[2].affected_subsets`** — the single string `"Black, Hispanic and Asian participants"` became three separate `DatasetBias` objects, one per group, each with its own `bias_description`, single-element `affected_subsets`, and `mitigation_strategy`. The Hispanic and Asian entries note the English-language eligibility requirement as a contributing factor, which the bundle states.
- **`human_subject_research.irb_approval`** — one paragraph became three entries (approval and date; reliance agreements; renewal requirement).
- **`human_subject_research.regulatory_compliance`** — one paragraph became five entries (FDA status; review status; DMC; GDS policy; ClinicalTrials.gov ID).
- **`human_subject_research.special_populations`** — one paragraph became four entries.
- **`at_risk_populations.special_protections`** — one paragraph became four entries.
- **`ip_restrictions.restrictions`** — one paragraph became four entries.
- **`regulatory_restrictions.regulatory_restrictions`** — became three entries, absorbing the storage restriction that had previously sat in `other_compliance`.
- **`data_governance.stewardship_roles`** — one paragraph became four entries.
- **`version_access.versions_available`** — one paragraph became four entries (three versions plus the documentation-navigation fact).
- **`distribution_dates`** — one object became four `DistributionDate` objects, one per release plus one for the annual cadence, with the source caveat attached to the last.
- **`external_resources[*].external_resources`** — each is now a single-element list rather than a bare string, matching the multivalued declaration. `restrictions` was added to the Zenodo entry (license terms govern reuse) and the BMJ entry (CC BY-NC 4.0, no commercial re-use), both stated in the bundle.

### 2.6 Other corrections

- **`conforms_to_standard`** gained `RO_CRATE`. The bundle's RO-Crate declares `conformsTo: https://w3id.org/ro/crate/1.2-DRAFT`; the enum permits the term and it was a supported omission. `conforms_to` prose was extended to match.
- **`instances[0].data_substrate`** added as `B2AI_SUBSTRATE:11` (DICOM), the largest share of the release by volume. The slot is single-valued, so `instances[0].notes` now enumerates the other substrates the release spans and states that the single-valued slot cannot express them.
- **`created_on` removed.** It duplicated `issued` exactly and no source states a creation date distinct from publication. `source_caveats` records the omission and its reason.
- **`was_derived_from` removed.** The value was a composite prose string bundling a ClinicalTrials.gov ID and an IRB number; a study is not a resource the dataset was derived from in the provenance sense, and the composite was not a usable reference. Both identifiers remain in the record — NCT06002048 in `human_subject_research.regulatory_compliance`, STUDY00016228 in `irb_approval` and `ethical_reviews`.
- **`file_collections[*].conforms_to`** no longer duplicates the CDS clause that `conforms_to_standard` already encodes; the CDS organizational fact moved into each entry's `description`. `file_collections[9]` gained `file_count: 9`, directly supported by the nine named root metadata files.
- **`sensitive_elements[0..1].sensitivity_details`** now name the subset each describes and cross-reference the `subsets` identifiers, so the two objects with opposite booleans are distinguishable structurally rather than only by prose.
- **`subsets[2]`** (mini) gained the FAIRhub API detail that it is recorded as a child record with identifier 4.
- **`at_risk_populations.notes`** now states explicitly that the AI/AN discussion concerns a group not enrolled and therefore does not bear on the `false` flag.
- **`data_governance.access_review_process`** gained the published access-conditions URL from the RO-Crate.
- **Spelling.** `tumour`/`oedema` → `tumor`/`edema` in `data_collectors[1]` (agent paraphrase, not quotation); `prioritising` → `prioritizing` in `known_limitations`; `programme` → `program` where agent-authored. Quoted titles and source-derived strings were left unchanged.
- **`notes`** gained the FAIRhub API view count and citation count; `source_caveats` gained the note on the IRB protocol's internal 4600/4000 inconsistency (§3).

---

## 3. The enrollment-target caveat

The audit noted that the top-level `source_caveats` described the 4000/4600 disagreement as tier-1-versus-tier-2 without surfacing that the tier-2 IRB protocol is internally inconsistent — it states 4600 in its participants section (question 2.1) and "a cross-sectional dataset of 4,000 people" in its objectives section (question 1.5). Both records' `source_caveats` were rewritten to state this explicitly. The preferred value (4000, tier 1) is unchanged.

The `collection_timeframes[0].source_caveats` handling of the 18-vs-19 July discrepancy was flagged in the audit as a positive control. It was retained and lightly clarified to name the tier of each source and to call the discrepancy what it is (one day).

---

## 4. Findings left as-is

| Finding | Disposition |
|---|---|
| `publisher: https://fairhub.io` is a URI, not a CURIE | **Left as-is.** No schema prefix for FAIRhub is evidenced, and the audit itself concedes a URL is defensible. Changing it would substitute a different unsupported form for an unsupported form. |
| `creators[0].affiliations` conflates consortium institutions with creator affiliations | **Left as-is in content**, but `source_caveats` now states that these are the institutions named in the FAIRhub collaboratorList and locationList plus the lead sponsor, and that no source states them as formal affiliations of the consortium entity. The ROR identifiers are all attested in the bundle. |
| `regulatory_restrictions.confidentiality_level: restricted` is reasoned, not stated | **Left as-is.** Neither `PublicDownloadSelfAttestationRequired` nor `HL7:2N (normal)` maps onto the permitted enum, and no enum member is a better fit. The `source_caveats` was expanded to say plainly that this is an interpretation rather than a stated value. |
| `doi` appears in three surface forms across the record | **Left as-is.** Each form is correct for its slot's declared range: bare `10.60775/fairhub.3` for the `string`-ranged `doi`, the resolver URL for the `uriorcurie`-ranged `id` and `latest_version_doi`. |
| `conforms_to` prose restates what `conforms_to_standard` encodes | **Left as-is.** The slot descriptions require exactly this: `conforms_to` records what the sources say in their words, `conforms_to_standard` records which registered standard that is. Populating both for the same standard is the documented intent. |
| `related_datasets` `has_part` ARKs duplicate `file_collections` | **Left as-is in structure**, but each `has_part` description now cross-references the corresponding `file_collections` fragment identifier, so the two representations are linked. The ARKs are attested verbatim in the RO-Crate. |
| `related_datasets[2..3]` target documentation websites, not datasets | **Left as-is.** `is_documented_by` is the correct relation and both entries are recorded verbatim in the FAIRhub `relatedIdentifier` list with that exact `relationType`. |
| `known_biases` positive controls (`purposes`, `addressing_gaps`, `tasks` correctly one-object-per-item) | **Left as-is.** No defect. |
| `conforms_to_class` correct in both records | **Left as-is.** No defect. |

---

## 5. Changes made — core record

### 5.1 Corrections mirroring the full record

All §2 changes that apply to slots the core record carries were applied identically: identifier and identity fixes, the two boolean flips and the `hipaa_compliant` change, absence-recording slot removals, the DQD move into `cleaning_strategies`, the `Cloud object storage access` removal, the EHR-screening move from `acquisition_methods` into `collection_mechanisms`, the `known_biases` split into three per-group objects, all list-splitting, the `RO_CRATE` addition, `data_substrate`, the removal of `created_on` and `was_derived_from`, and the spelling corrections.

### 5.2 `distributions` — the schema-shape finding

The audit's highest-severity finding was that `distributions` does not appear in the supplied schema digest, and that its `conforms_to_standard` was written as a scalar where the schema declares the slot multivalued.

**The scalar/list error was fixed:** every `distributions` entry now carries `conforms_to_standard` as a list, matching both the schema declaration and the full record's `file_collections`.

**The slot itself was retained.** The supplied digest describes the `Dataset` class; it does not enumerate `CoreDataset`'s slots, so the digest cannot establish that `distributions` is undeclared in the core schema. Asserting otherwise would be an unsupported claim about the schema. The entries were, however, brought closer to the digest's `FileCollection` shape — `path`, `bytes`, `format`, `media_type`, `conforms_to`, `conforms_to_standard` — and the invented per-entry `id` fragments were dropped, since those fragments duplicated the full record's `file_collections` identifiers without adding anything the core record uses. Validation against the core schema is the decisive test here, and the reduced shape is the one most likely to pass.

### 5.3 The `informed_consent.notes` blob

The audit found that the core record had folded three top-level slots the full record carries — `participant_compensation`, `collection_notifications`, `collection_consents` — into a single `informed_consent[0].notes` field, and had similarly dropped `participant_privacy`, `consent_revocations`, `direct_collection` and `relationships`.

The content remains in `informed_consent[0].notes`, now with an explicit closing sentence: *"This notes field carries participant-notification, consent-process and compensation facts for which the core schema declares no separate slot."* This is honest about what the field is doing rather than presenting it as ordinary residual content. The same reasoning as §5.2 applies: the digest does not enumerate `CoreDataset`'s slots, so promoting these to top-level slots risks validation failure on slots that may not exist in the core schema, while leaving them undeclared-but-labeled preserves the facts and flags the compromise.

`participant_privacy` content (anonymization method, privacy techniques, reidentification risk, data-linkage prohibition, privacy-motivated device selection) was consolidated into `is_deidentified.deidentification_details`, which is a declared slot and a natural home for it. `relationships` content (one visit per participant, all instances from one project) remains in `instances[0].notes`.

### 5.4 Content restored from full-record structure

Several facts the core record had compressed away were restored into the top-level `notes`, which is the appropriate residual location given the core schema's narrower slot set:

- the recommended citation string;
- total file count and total size in bytes;
- the three access tiers, including the mini subset's FAIRhub child-record identifier;
- **the per-stratum split table** — validation, test and training counts by race/ethnicity, sex and diabetes status, with mean ages. The original core record had reduced the split to two sentences; the full breakdown from the README is now present.
- the FAIRhub view count and citation count;
- the third-party-sharing position (public distribution subject to login, use restriction and license assent; onward sharing confined to identically-bound licensees).

`total_file_count`, `total_size_bytes` and the split detail were additionally reflected in the top-level `description`, which now states the file and byte counts directly.

`download_url: https://fairhub.io/datasets/3` was added, supported by the FAIRhub landing page.

### 5.5 Header

The core header retains `# Phase 4 reconciliation: completed`. The audit flagged this as premature at Phase 3, which it was; it is accurate as of this report.

---

## 6. Parity check

The core record states nothing the full record does not. Every fact in the core `notes` blob appears in the full record in a structured slot: compensation in `participant_compensation`, notification in `collection_notifications`, consent process in `collection_consents`, splits in `splits`, subsets in `subsets`, citation in `citation`, counts in `total_file_count`/`total_size_bytes`, sharing in `third_party_sharing`.

The full record carries structure the core does not: `variables` (31 `VariableMetadata` objects), `file_collections` (10 objects with per-directory identifiers, collection types and file counts), `subsets`, `splits`, `relationships`, `direct_collection`, `participant_privacy`, `consent_revocations`, `collection_notifications`, `collection_consents`, `participant_compensation`, `third_party_sharing`, `citation`, `total_file_count`, `total_size_bytes`, and `other_tasks`/`future_use_impacts` detail. This is the expected asymmetry between a full and a core datasheet.

---

## 7. Referent

Both records denote **the AI-READI Flagship Dataset of Type 2 Diabetes, version 3.0.0**, identified by `https://doi.org/10.60775/fairhub.3` — the release as a whole, comprising both the publicly accessible tier and the controlled-access tier. This choice is held consistently across both records and is now the explicit basis for `is_deidentified.identifiable_elements_present: true` (§2.2). Where a slot's value differs between tiers, both values are recorded with the tier named, as in `sensitive_elements`.