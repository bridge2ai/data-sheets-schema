# Reconciliation Report — CHORUS

**Version label:** `2026-07-29_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Cohort 2 informational webinar; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14 historical supplement)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-29_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-29_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The bundle describes at least three candidate entities: (a) the CHoRUS **clinical care dataset** (patient admissions, OMOP/waveform/imaging/text modalities), (b) the CHoRUS **data generation project** funded under OT2OD032701, and (c) the CHoRUS **GitHub software organization** (28 repositories, MIT/Apache-2.0 licensed).

**Chosen referent: (a), the CHoRUS clinical care dataset.** Both records are held to this choice consistently. Project-level facts (award number, PI, period of performance, pillar structure) are retained only where they document the dataset's provenance, funding, or purpose. Software-repository facts are retained only where a tool acts on the data itself; repository licenses are *not* attributed to the dataset. This decision drove several of the corrections below.

---

## 2. What the audit found

No high-severity finding. The audit returned **25 findings** (2 medium, 12 low, 11 informational) across both records.

No fabricated numeric value, date, name, identifier, or contact string was found. Specifically verified as faithful to the bundle: award amount and number, project start/end dates, 14 contributing hospitals, 20 institutions, 60+ consortium members, 100,000 anticipated / 50,000 released admissions, 1.6 billion OMOP rows, 7,642 radiology admissions, 23 Tb waveform data, 1000 images, 9 modalities, the modality/standard/access-control table, the program contacts, and the source typo `cmccrary@mgh.havard.edu` (preserved verbatim, not silently corrected). The 45,000 (August 2025 webinar) versus 50,000 (website) admission-count discrepancy was surfaced rather than resolved in favour of one source.

The dominant defect class was **slot fit, not invented content** — evidenced facts placed in slots whose semantics they do not satisfy — followed by a small set of unstated qualifiers and categorical claims that outran the evidence.

---

## 3. Changes applied

### 3.1 `machine_annotation_tools` — both records (medium)

**Removed** `privacy_scan_tool`, `CTP-deid`, and `UF-Geocoding` from this slot. The slot's range is automated annotation tools; the bundle describes these respectively as a privacy scanner for medical records, a repository with **no description whatsoever**, and geocoding code for OMOP Location entities. None annotates data. The `CTP-deid` entry additionally carried a description ("a de-identification repository") derived from the repository *name* rather than from any bundle text — the single clearest instance of inference presented as fact in either record, and removed on that basis.

**Retained:** the OHNLP toolkit, which the bundle explicitly credits with extracting and tokenizing clinical notes — an automated annotation operation.

**Relocated:** the privacy scan and geocoding tools to `preprocessing_strategies`, described in the bundle's own terms. `CTP-deid` is now carried in `external_resources` as a named repository only, with no functional claim.

### 3.2 `ethical_reviews` — both records (low)

**Removed** the fourth entry ("Drawing on expertise across team science, law, ethics, health services, biomedical science, engineering, and scientific journal publications"), which describes project disciplinary composition and is not a review of any kind.

**Retained but re-worded** the remaining three entries so that they no longer imply a completed formal review. The bundle reports no IRB approval, ethics committee determination, or compliance certification anywhere; it reports ethics *activity* — the Ethics pillar, community-facing focus groups to determine what data is appropriate for public sharing, and analysis of the legal and regulatory landscape. The entries now state that activity literally. This is consistent with `human_subject_research`, which already recorded that no IRB determination is reported in the bundle.

### 3.3 "Adult" ICU qualifier — both records, `subpopulations` and `sampling_strategies` (low)

**Removed** the word "adult." The bundle says only "Patient admissions from ICU, PICU, and NICU." It never qualifies the ICU population as adult; the qualifier was supplied by contrast with PICU/NICU, which is inference. All four occurrences (two slots × two records) now use the bundle's wording.

### 3.4 `direct_collection` — full record (low)

**Replaced** the categorical assertion "Data are not collected directly from individuals" with the evidenced statement that collection is retrospective from hospital clinical systems across 14 contributing sites. The bundle establishes retrospective institutional collection; it makes no statement about direct-versus-third-party acquisition from individuals. The original conclusion was reasonable but unstated.

### 3.5 `maintainers` — both records (low)

**Re-scoped.** `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org` appear in the bundle under "Request access" / general inquiries, and Ciera McCrary appears as Program Manager under "Contact Us." None is described as a dataset maintainer. The entries are retained — a named contact channel is genuine and useful — but their stated role is now "access request and inquiry contact" / "program manager contact" as the bundle has it, rather than "maintenance contact."

### 3.6 `preprocessing_strategies` geocoding entry — both records (low)

**Decoupled.** The geocoding entry no longer asserts that UF-Geocoding/DeGauss produces the "geographic distance to the nearest hospital" element. The bundle states these as two independent facts, in two different source documents (GitHub repository description; NIH abstract). The entry now records the geocoding of OMOP Location entities via DeGauss on its own terms; the distance-to-nearest-hospital contextual factor is recorded separately under the project's stated data-element goals.

### 3.7 `regulatory_restrictions` — both records (low)

**Narrowed substantially.** Removed the HIPAA/GDPR references, which in the bundle occur only inside an AIM-AHEAD curriculum *topic title* ("HIPAA/GDPR compliance for OMOP/FHIR data") and impose no stated obligation on this dataset. **Relocated** the U.S. citizenship / permanent residency / W-9 / `.edu`-address requirements to the access-terms slots (`third_party_sharing` in the full record, mirrored in core), where they belong: these are eligibility criteria for the AIM-AHEAD Bridge2AI for Clinical Care Training Program, one route of access, not export-control or regulatory restrictions on the data. What remains under `regulatory_restrictions` is only the bundle-supported statement that the repository is under review for potential modification in compliance with Administration directives.

### 3.8 `publisher` — both records (low)

**Removed.** The slot had been populated with the project website URL. The bundle names no publishing entity for the dataset. Under the omission-over-inference rule an absent slot is the correct answer here. The website is retained in `page`, where it belongs.

### 3.9 `is_tabular` — both records (informational)

**Removed.** The dataset is irreducibly mixed: 1.6 billion rows of tabular OMOP data alongside DICOM imaging, WFDB/EDF+ waveform, and tokenized text. A single boolean cannot represent this, and `false` was a judgment call rather than a bundle statement. The modality-by-modality composition is already fully documented in `file_collections` and `instances`, so no information is lost.

### 3.10 `funders` award amount — both records (informational)

**Changed** "5,880,300 USD" to the literal bundle value with the currency noted as unstated in source. USD is near-certain for an NIH award but is not written anywhere in the bundle.

### 3.11 `instances` hedging — full record (informational)

**Aligned.** The `instances` entry now carries the same hedge already present in `description` and `known_limitations`, attributing 50,000 to the project website and noting the webinar's "over 45K unique admissions" as of August 2025. The substance was already consistent; only the hedging was uneven.

### 3.12 Cross-record placement alignment (informational)

Two paired-record divergences were resolved in favour of the full record's placement, so that both records tell the same story in the same slots:

- The holdout test set's external-validation purpose now sits in `purposes`/`splits` in both records, with `subsets`/`resources` carrying only the partition itself.
- Registration, licensing-agreement, and access-request detail now sits in `third_party_sharing` in both records; `version_access` in the core record no longer duplicates it.

---

## 4. What was left as-is, and why

**`relationships` (full record).** Retained. The inference that modalities link to a common admission-level entity rests on the bundle's own phrasing "7,642 Admissions with Radiology Data," which does presuppose admission-level linkage. The entry is retained with that phrasing cited as its basis and is marked as apparent rather than as a documented linkage model, since the bundle describes no explicit instance-linkage schema.

**`known_biases` — omitted, deliberately.** The bundle twice gestures at bias ("manage privacy and bias"; "sampling methods to ensure a balanced and diverse cohort") but never names a bias present in the data. Naming one would be invention. The omission is recorded here so it reads as a decision rather than an oversight. The related evidenced facts — the ambition of diversity, and the acknowledgement that bias management is an open work item — are captured in `purposes` and `known_limitations`.

**`license` — omitted at top level, deliberately.** The bundle's MIT and Apache-2.0 statements attach to `chorus-ai` software repositories, not to the data. Attributing MIT to a controlled-access clinical dataset would be a material error. `license_and_use_terms` states the actual position: controlled access, signed licensing agreement required, license text not present in the bundle.

**`doi`, `version`, `download_url`, `citation`, all consent slots (`collection_consents`, `consent_revocations`, `collection_notifications`), `errata`, `retention_limit` — omitted.** No bundle support. The dataset is controlled-access with no direct download endpoint disclosed, and the bundle contains no patient-facing consent documentation despite describing community focus groups on data-sharing appropriateness.

**The 45K/50K discrepancy — preserved, not resolved.** Two sources in the declared bundle disagree. Both figures are stated with their source and date rather than one being selected. This is the correct handling under the disagreement rule.

**The `cmccrary@mgh.havard.edu` typo — preserved verbatim.** Correcting it to `harvard.edu` would substitute an inferred value for the declared one.

**Project-level provenance facts — retained despite the dataset referent.** Award number OT2OD032701, application ID 10472824, PI Eric S. Rosenthal, Massachusetts General Hospital, the 2022-09-01 to 2026-11-30 period, and the named leadership across MGH, University of Florida, UTHealth Houston, and Tufts are retained in `funders`, `creators`, and `collection_timeframes`. These document the dataset's provenance and are within scope for the chosen referent.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Slots populated before reconciliation | 49 | 27 |
| Slots removed | 3 (`publisher`, `is_tabular`, one merged) | 3 (`publisher`, `is_tabular`, `version_access` deduplicated) |
| Slots edited in place | 9 | 7 |
| Slots populated after reconciliation | **46** | **24** |

**Schema validation:** both records validate.

- Full — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → PASS
- Core — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → PASS

All required keys are present on every object-ranged entry (`id` on `Dataset`, `DataSubset`, `FileCollection`; `relationship_type` and `target_dataset` on `DatasetRelationship`; `source_description` on `RawDataSource`; `variable_name` on `VariableMetadata`). All enum-ranged values are drawn from their permitted sets.

**Provenance:** no previously generated D4D record was read, opened, grepped, or consulted at any phase. The declared bundle and the two schema files were the only inputs. The live provenance record was written after this reconciliation completed.

**Reconciliation outcome: RECONCILED.** The paired records are mutually consistent in substance and in slot placement, and no claim remains that the declared bundle does not support.