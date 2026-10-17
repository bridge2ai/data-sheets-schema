# AI-READI D4D Reconciliation Report

**Project:** AI_READI
**Label:** 2026-08-16_claude-opus-5-api-generic-v5_rep1
**Arm:** BASELINE (input documents only)
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-16_claude-opus-5-api-generic-v5_rep1/AI_READI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-16_claude-opus-5-api-generic-v5_rep1/AI_READI_d4d_core.yaml`

---

## 1. Scope of the audit

Phase 3 audited both records against the declared bundle (`data/preprocessed/concatenated/AI_READI_preprocessed.txt`, 11 source files) and against the supplied schema digests. The audit checked four things: whether every factual claim traces to the bundle; whether values sit in the slots whose descriptions they answer; whether object-ranged slots populate their declared fields rather than dumping content into free text; and whether enum-ranged slots draw only from permitted terms.

The audit returned 23 findings, one of which the auditor withdrew as a false positive on review (the `conforms_to_standard` enum check — `DICOM`, `CDS` and `RO_CRATE` are all permitted terms and no violation exists).

**No fabricated dataset facts were found in either record.** No prior D4D content is evident. Source conflicts are surfaced in `source_caveats` rather than silently resolved. The defect class is structural, not factual, and it concentrates in the core record.

---

## 2. Findings and dispositions

### 2.1 High severity — core `distributions`

**Finding.** The core record introduced a `distributions` slot that the supplied core schema digest does not define, populated with keys drawn from two different classes: `path` and `total_bytes` belong to `FileCollection`, while `format` and `media_type` belong to `DistributionFormat`. The record also wrote `bytes` where `FileCollection` declares `total_bytes`.

**Disposition: left as-is, with one qualification.** The reconciled core record still carries `distributions` with ten entries. The task supplied a digest for the *full* schema (`Dataset`) only; no digest for `data_sheets_schema_core_all.yaml` was provided, so I cannot state that `distributions` is undeclared in the core schema — only that I cannot confirm it is declared. Removing a slot on the strength of an absent digest would be as unsupported as adding one. The content itself (per-directory paths, byte counts, file counts, per-directory standards) is directly stated in the bundle's `dataset_structure_description` and is the same content the full record carries in `file_collections`.

This is the one finding I could not resolve. It should be settled by reading the core schema directly before this record is trusted; if `distributions` is undeclared there, the entries belong in `file_collections` with `total_bytes` and `file_count` restored to their declared names.

### 2.2 Medium severity — core placement defects

Four findings shared a single cause: content from slots the core projection dropped had been absorbed into unrelated sibling objects rather than relocated to record-level `notes` or omitted.

| Content | Was placed in | Now in reconciled core |
|---|---|---|
| Cross-instance relationships (single visit per participant; 10% follow-up in year 4) | `instances[9].notes` | Record-level `notes` |
| Participant compensation ($200 stipend, transport costs) | `data_collectors[4].role` | Record-level `notes` |
| Re-identification risk and privacy techniques | `is_deidentified.deidentification_details` | Record-level `notes` |
| Consent revocation terms | `informed_consent[0].withdrawal_mechanism` | **Left in place** |

**Changed.** The first three are now in the record-level `notes` block, which the schema describes as holding residual content that no fitting slot can take. The relationship prose is no longer attached to the continuous-glucose-monitoring instance, where it made a false claim about that instance's scope. Participant compensation is no longer a property of a `DataCollector` — the core record's `data_collectors` list is now four entries (coordinators, data managers, imaging technicians, laboratory personnel), all of which genuinely describe who collected data. `is_deidentified.deidentification_details` now carries only de-identification method and audit status; the re-identification risk statement has moved out.

**Left as-is.** `informed_consent[0].withdrawal_mechanism` retains the revocation text. Unlike the other three, this is a placement the slot's own name invites: a withdrawal mechanism *is* what a consent revocation describes. The full record keeps the separate `consent_revocations` entry; the core record folds it into the field that asks for it. Nothing is lost and nothing is misattributed.

Also folded into `informed_consent[0].consent_scope` in the core record: the sentence that informed consent was required before any part of the protocol including questionnaires, which the full record carries in `collection_consents`. Same reasoning.

### 2.3 Medium severity — instance substrate assignments

**Finding.** `instances[3].data_substrate` was `B2AI_SUBSTRATE:69` (Time-series data) for the environmental sensor. The bundle states these files follow the NASA ASCII File Format Guidelines for Earth Science Data — that is, delimited ASCII text. "Time-series" describes the content's shape, which is an inference; the substrate the bundle names is delimited text.

**Changed in both records.** Now `B2AI_SUBSTRATE:10` (Delimited Text), with a `notes` value recording the ASCII/ESDS basis. The `data_topic` (`B2AI_TOPIC:11`, Environment) is unchanged and supported.

**Finding.** `instances[0].data_topic` was `B2AI_TOPIC:43` (Diabetes) on the participant-level instance. A participant is a person, not a topic-bearing artifact, and the bundle does not assign a topic to the participant record.

**Changed in both records.** The slot is now omitted. The instance retains `instance_type`, `counts: 2280`, `label: false` and the label description — all directly stated. Per the enum guidance, omitting is correct where no term fits rather than approximating.

The ECG instance (`B2AI_SUBSTRATE:49` Waveform Data, `B2AI_TOPIC:10` EKG) was flagged only for a noted alternative; both terms are supported by the bundle's WFDB statement and no change was made.

### 2.4 Low severity — constructed identifiers

**Finding.** Three identifiers hung non-part entities off the dataset DOI as URI fragments: `#creator-ai-readi-consortium` for the AI-READI Consortium, and `#grant-p30dk035816` and `#grant-ul1tr003096` for two NIH grants. The v5 rule permits a fragment on a supplied identifier where the evidence gives none, but a fragment asserts a part-whole relation: the consortium is an organization and the grants are awards, neither of which is part of the dataset. The audit noted that `Creator` and `Grant` do not require `id`, so omission was available and preferable.

**Changed in both records.**

- `creators[0]` no longer carries an `id`. The `notes` value now states explicitly that FAIRhub records `creatorName: "AI-READI Consortium"` with `nameType: Organizational` and supplies no registry identifier, so none is asserted. The eight affiliation ROR identifiers and the PI's ORCID are unchanged — those *are* stated in the bundle.
- `funders[0].grants` is now a single entry: OT2OD032644, identified by its NIH RePORTER URL, which the bundle supplies. Grants P30DK035816 and UL1TR003096 are recorded in the `notes` prose with their source attribution (BMJ Open, Nature Metabolism) rather than as separately identified `Grant` objects, because the bundle gives no persistent identifier for either.

**Left as-is.** The `#split-train` / `#split-validation` / `#split-test` fragments on the full record's `subsets`, and the `#cardiac_ecg` etc. fragments on `file_collections`, are unchanged. These *are* parts of the dataset — a split is a partition of it and a directory is a component of it — so the part-whole relation the fragment asserts is true.

### 2.5 Low severity — publisher and license

**Finding.** `publisher: https://fairhub.io/` uses a homepage URL in a `uriorcurie` slot; the bundle states `publisherName: FAIRhub` with no registry identifier. Separately, the license URI (`https://doi.org/10.5281/zenodo.17555036`) appears only inside `license_and_use_terms.license_terms` prose.

**Left as-is in both records.** The publisher URL is the only publisher identifier the bundle offers, and the alternative — omitting `publisher` entirely — loses information the bundle does state. On the license URI: the schema digest exposes `license` as a plain string and no URI-ranged license slot exists, so the DOI's placement inside the terms prose is a schema limitation rather than a record defect. `license: AI-READI custom license v2.0` is the `rightsName` verbatim from FAIRhub metadata.

### 2.6 Low severity — full-record `subsets` structure

**Finding.** The three split subsets placed their entire composition in `description` prose while `DataSubset` accepts the full `Dataset` slot inventory, including `instances` (with `counts`) and `subpopulations`.

**Changed in the full record.** Each of the three subsets now carries an `instances` entry with the participant count (1576 / 352 / 352) and a `subpopulations` list giving the race-and-ethnicity, sex, and diabetes-status distributions as declared fields. The `description` retains only the count and mean age. The per-split figures are read from the README split table.

### 2.7 Low severity — core omissions relative to full

**Finding.** The core record omits `variables` (36 entries), `subsets`, `splits`, `total_file_count`, `total_size_bytes`, `citation`, `relationships`, `participant_privacy`, `participant_compensation`, `collection_consents`, `collection_notifications`, `consent_revocations` and `direct_collection`, without stating whether the core schema defines them.

**Partially changed.** Because no core schema digest was supplied, I cannot assert which of these the core schema declares, and so cannot report them as legitimately dropped. What I could do is ensure that none of the underlying *evidence* is lost:

- Split composition, file count, total bytes, citation, relationships, privacy and compensation content are all now recoverable from the core record's `notes` block, which was substantially expanded during reconciliation.
- `variables` remains absent from the core record with its content not restated. This is the one substantive information loss between the two records. The 36 variable descriptions (reference ranges, units, measurement techniques) are large and fully present in the full record; reproducing them in `notes` prose would defeat the purpose of a core projection. If the core schema declares `variables`, they should be restored.

`is_deidentified`, `human_subject_research`, `ethical_reviews`, `at_risk_populations`, `data_governance`, `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`, `distribution_formats`, `distribution_dates`, `external_resources`, `related_datasets`, `maintainers`, `updates`, `version_access`, `retention_limit`, `extension_mechanism` and all Composition/Collection/Preprocessing slots are present in both records with identical content.

### 2.8 Informational findings

Three findings were raised for the record without recommending change:

- **`description` acronym expansion.** The description previously read "Artificial Intelligence Ready and Equitable/Exploratory Atlas for Diabetes Insights", a slashed conflation of two source variants. **Changed:** the expansion is now omitted from the description body entirely; the variance remains documented in `source_caveats`, which names both forms and their sources.
- **`collection_timeframes[0]`** — enrollment-until and completion dates are supported (BMJ Open; FAIRhub `completionDateStruct`); the 18-vs-19 July 2023 start-date discrepancy is in `source_caveats`. No change.
- **Full-record `notes`** — carries mini-subset availability, manufacturer in-kind support, return-of-results procedures and the biorepository description. The auditor noted these are substantive rather than residual, but no fitting slot exists for return-of-results or the biorepository, and manufacturer *in-kind device loans* are not funding in the `FundingMechanism` sense. No change.

### 2.9 Enum compliance

All enum-ranged values in both records were checked against the permitted sets in the digest and all draw from them: `conforms_to_standard` (CDS, WFDB, OMOP_CDM, DICOM, OPEN_MHEALTH, ESDS, RO_CRATE), `credit_roles`, `bias_type`, `limitation_type`, `relationship_type`, `collection_type`, `data_use_permission` (`disease_specific_research`), `confidentiality_level` (`restricted`), `hipaa_compliant` (`compliant`), and `Maintainer.role` (`academic_institution`, `other`). No violations. No changes.

---

## 3. Referent

Both records describe **version 3.0.0 of the AI-READI flagship dataset**, DOI `10.60775/fairhub.3`, released 17 November 2025, comprising 2,280 participants. Versions 1.0.0 and 2.0.0 are represented as `related_datasets` targets rather than as the record subject. This choice is held consistently across both records and is stated here as required.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Findings addressed by change | 5 | 6 |
| Findings left as-is with reason | 4 | 5 |
| Findings unresolved | 0 | 1 (`distributions` schema status) |

**Factual integrity:** clean. Every claim in both records traces to the declared bundle. Three unsupported identifiers were removed. One inferred substrate term and one inferred topic term were corrected or omitted.

**Structural integrity:** improved. Three misplaced content blocks relocated in the core record; three split subsets restructured into declared fields in the full record.

**Remaining risk:** the core `distributions` slot cannot be confirmed as schema-declared from the materials supplied. This should be checked against `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` directly. The absence of `variables` from the core record is a known and deliberate information reduction, not an oversight.