# Reconciliation Report — AI_READI

**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation
**Findings received:** 31 (2 high, 8 medium, 21 low)
**Disposition:** 22 changed, 9 left as-is

---

## 1. What the audit found

The audit found no factual claim unsupported by the declared bundle. Source disagreements were already surfaced rather than silently resolved — Washington University in St. Louis vs. University of Washington as managing organization; 4,000 (FAIRhub/Nature/NIH) vs. 4,600 (IRB protocol) target enrollment; 10.5% (BMJ Open) vs. >6% (Nature Metabolism) global prevalence; 2023-07-18 (BMJ Open pilot) vs. 2023-07-19 (FAIRhub collection start) — and superseded v1.0.0/v2.0.0 facts were kept distinct from the v3.0.0 referent.

The defect class was structural, and it clustered in three patterns:

1. **Slot demotion in the core record.** Content the schema declares dedicated slots for had been written as prose in `notes` — aggregate file counts and sizes, the recommended 70/15/15 split, participant compensation, participant privacy, and inter-instance relationships. Because the full record carried the same evidence as populated objects, the paired records diverged on identical evidence.
2. **One undeclared slot.** The core record emitted a `distributions` block whose slot name and member keys (`path`, `format`, `media_type`) do not appear in the schema digest.
3. **Values that point rather than answer**, and **URIs and role descriptors embedded in name-shaped strings**.

---

## 2. Changes to the core record

### 2.1 Removed the undeclared `distributions` block (high)

`distributions` is not a declared `CoreDataset` slot, and none of its member keys is declared. The block was removed. Its content was migrated to `file_collections`, the declared slot whose `FileCollection` range carries `path`, `file_count`, `total_bytes` and `collection_type`. Retaining an undeclared slot would have failed validation and would have carried the file inventory in a shape the schema does not admit.

### 2.2 Promoted aggregate size and file count out of `notes` (high)

`total_file_count: 356343` and `total_size_bytes: 3815969779678` were populated from the FAIRhub API (`data.fileCount`, `data.size`), corroborated by the README and the v3 HTML capture. Both are declared integer slots; the figures had been stated in prose at the head of `notes`. The prose statement was deleted so the fact is asserted once, in the field that declares it.

### 2.3 Populated `splits` and `subsets` (medium)

The recommended partition (70% train / 15% validation / 15% test, with validation and test balanced for sex, race/ethnicity and diabetes status) and the per-stratum counts from the README split table were moved from `notes` into `splits` and `subsets`. The bundle answers these directly at healthsheet *labeling* Q7 and in the README table. The full record already carried both; the core record now matches.

### 2.4 Populated `participant_compensation` (medium)

`HumanSubjectCompensation` was populated with `compensation_provided`, `compensation_amount` ($200), `compensation_type` and `compensation_rationale`, from healthsheet *collection* Q4 and IRB protocol §4.4. The travel-cost coverage was retained on the object's `notes`, where it qualifies the compensation rather than duplicating a declared field. The corresponding `notes` item (11) was deleted.

### 2.5 Populated `participant_privacy` (medium)

`ParticipantPrivacy` was populated with `anonymization_method`, `privacy_techniques`, `reidentification_risk` and `data_linkage`, drawn from healthsheet *composition* Q13–14, *uses* Q4 (the acknowledged theoretical re-identification risk), the Nature Metabolism watermarking passage, and IRB §9.6. The corresponding `notes` item (12) was deleted.

### 2.6 Populated `relationships` (medium)

Healthsheet *composition* Q8 states that all instances belong to one prospective data-generation project with one visit per participant. This was moved from `instances[0].notes` into the declared `Relationships` object, matching the full record.

### 2.7 Split consent content into its three declared slots (medium)

`collection_notifications`, `collection_consents` and `consent_revocations` were populated separately from healthsheet *collection* Q8, Q9 and Q10 respectively. Previously all three answers had been compressed into `informed_consent[0].notes` and `withdrawal_mechanism`. `informed_consent` was retained for the consent type, documentation and scope, which is what that class declares; the withdrawal mechanism remains there and is not duplicated in `consent_revocations`, which carries the revocation procedure and its stated limit (data already shared or used remains in the dataset).

### 2.8 Populated `third_party_sharing` (medium)

Two `ThirdPartySharing` objects were added: `is_shared: true` for public distribution (healthsheet *distribution* Q1), and `is_shared: false` for onward conveyance by licensees, which license §2 prohibits except to Other Licensees bound by identical terms. Emitting both preserves the distinction the evidence draws; collapsing them would misstate either the release or the restriction.

### 2.9 Replaced the bare-URI resource list with typed `related_datasets` (medium)

Eight `DatasetRelationship` objects were populated with `relationship_type` and `target_dataset`, covering the two prior versions (`is_new_version_of`, `has_version` as the evidence supports), the mini-version child record (FAIRhub API `data.child`: 4), and the describing publications and documentation sites carried in the API `relatedIdentifier` entries with `relationType: IsDocumentedBy`. The previous catch-all `external_resources` entry listing these as bare URIs was reduced to the resources that are not datasets and not documentation relationships.

### 2.10 Populated `variables` (medium)

Twenty-three `VariableMetadata` objects were added, aligned with the full record. Evidence: BMJ Open Table 2 (analyte name, unit, reference range, rationale), Table 4 (device, scan type, data format), healthsheet *devices* Q1 (measurement technique for vision, contrast sensitivity, monofilament, MoCA), and the README split-table categories (diabetes-status ordinal, sex, race/ethnicity). Omission here was a gap against available evidence, not an abstention.

### 2.11 Removed `extension_mechanism.contribution_url` (low)

The core record had populated `https://github.com/AI-READI`. The bundle presents that organization as hosting project tooling and FAIR guidelines, not as a dataset-contribution route; healthsheet *maintenance* Q7 states plainly that no contribution mechanism exists. The URL was removed, leaving `extension_details` to record the negative answer. The paired records now agree.

---

## 3. Changes to the full record

### 3.1 Removed the empty `use_repository` list (low)

An empty list neither asserts nor omits. Healthsheet *uses* Q3 answers "No"; that answer is already recorded in `notes` item (2). The slot was omitted.

### 3.2 Populated `instances[0].data_substrate` and `data_topic` (low)

Healthsheet *composition* Q5 enumerates tabular, imaging, and physiological signal/waveform substrates across named domains. Both fields are declared on `Instance` and were already populated in the core record; the full record had carried the same content only in `notes`. The fields were populated and the duplicated prose trimmed from `notes`.

---

## 4. Changes applied to both records

### 4.1 Stripped the URI from the `license` value (low)

`license` now reads `AI-READI custom license v2.0`. The Zenodo DOI is preserved in `license_and_use_terms.license_terms`, which is where a resolvable identifier belongs; carrying it inside the name string duplicated it and made the name value non-atomic.

### 4.2 Reduced `license_and_use_terms.contact_person` to a person name (low)

The value now reads `Aaron Lee`. The email address (`contact@aireadi.org`) was moved to the object's `notes`, where it qualifies the contact rather than being packed into a name-shaped field. The role descriptor "central study contact" was dropped as redundant with the slot's own semantics.

### 4.3 Reduced `human_subject_research.irb_approval` to the approval identifier (low)

The field now carries `STUDY00016228`. The approval date (2022-12-20), reviewing body, and annual-renewal requirement remain in `ethical_reviews[0].review_details` and `reviewing_organization`, which is where the narrative belongs. The identifier is now asserted once.

### 4.4 Corrected `is_deidentified.method` (low)

The record had asserted `HIPAA Safe Harbor` while its own `deidentification_details` quoted the source as `deIdentType: NoDeIdentification` with the explanation that no identifiers were collected, so no active de-identification was necessary, and that the data were checked against US HIPAA identifiers. `method` was changed to state the source's own determination — no active de-identification performed, with HIPAA-identifier verification applied — and `identifiable_elements_present: false` was retained, since the bundle asserts it directly. The Safe Harbor characterisation, which the Nature Metabolism comment applies to the public set, is retained in `deidentification_details` and attributed there.

### 4.5 Removed the pointer value from `regulatory_restrictions.regulatory_restrictions` (low)

The value recorded only that the project refers users to the license. Healthsheet *distribution* Q6 gives no substantive export-control answer. The sub-field was omitted; `other_compliance` retains the substantive obligation — compliance with NIH Genomic Data Sharing security best practices under license §4 — and `confidentiality_level` and `hipaa_compliant` are unchanged.

### 4.6 Removed `ip_restrictions.notes` (low)

Same pointer pattern. The substantive answer — title and IP rights remain with the Licensor, no rights beyond those granted, restrictions on redistribution of Data and derivative works — is already in `restrictions`.

### 4.7 Removed `discouraged_uses` (low)

The single object stated that the license imposes restrictions and that the healthsheet directs users to them rather than naming additional discouraged tasks. That describes where an answer would be found. The substantive prohibitions — clinical treatment decisions, re-identification or contact of Data Subjects, inference of group membership, redistribution outside the licensee chain — are enumerated under `prohibited_uses`, which is the stronger and correct slot. The slot was omitted rather than retained as a pointer.

### 4.8 Populated `at_risk_populations.at_risk_groups_included` (low)

The object had carried only `notes`. The bundle answers the declared field: pregnancy, gestational diabetes and type 1 diabetes are exclusion criteria; the age floor of 40 excludes minors; IRB §2.3–2.4 answer "No" to prisoner involvement. `at_risk_groups_included` was populated with that determination. The transportation-assistance detail (IRB §4.5/§4.4) was retained in `notes`, since it is an accessibility accommodation rather than a special protection and does not answer `special_protections`. `guardian_consent` and `assent_procedures` remain unpopulated: no minors or decisionally impaired subjects are enrolled, so the bundle gives no answer.

### 4.9 Trimmed the top-level `notes` (low)

Core `notes` items (10)–(12) were deleted, their content having moved to `splits`/`subsets`, `participant_compensation` and `participant_privacy`. The full record's duplicated instance-substrate prose was trimmed. What remains in `notes` in both records is source-disagreement documentation and superseded-version context — the managing-organization conflict, the 4,000/4,600 enrollment conflict, the prevalence conflict, the v1.0.0/v2.0.0 participant counts, the grant figures, and the FAIRhub static-capture caveat — which is what the slot's description admits.

---

## 5. Left as-is, with reasons

### 5.1 `creators[0]` populated only through `notes` (full and core)

The organizational creator is recorded in the bundle as `creatorName: "AI-READI Consortium"`, `nameType: "Organizational"`. The `Creator` class in the schema digest declares no name field — only `affiliations`, `credit_roles`, `notes` and `principal_investigator`. There is therefore no declared field the organizational name can occupy. The name is carried at top level in `created_by`, and the object was retained to hold the consortium's role context. **Left as-is: schema limitation, not a generation defect.** The alternative — deleting the object — would remove the only place the consortium's collective authorship is represented as a creator.

### 5.2 ORCIDs, degrees and PI roles in `creators[*].notes`

`Creator` declares no identifier field, and `credit_roles` is a closed enum that does not include principal investigator or study PI. The bundle supplies sixteen ORCID identifiers as structured values in `overallOfficialList`. **Left as-is:** the choice is between recording them as prose and discarding them; prose preserves the evidence.

### 5.3 URIs inside `conforms_to` and `file_collections[*].conforms_to`

`conforms_to` is a plain string, and the versioned specification URIs (CDS v0.1.1, DICOM, OMOP CDM, WFDB, Open mHealth, the NASA ASCII guidelines) have no other declared home in these records. Stripping them would discard resolvable evidence the bundle supplies as `standardRelatedIdentifier` and `standardIdentifier` values. **Left as-is,** and noted here as a schema limitation. This is a deliberate departure from the treatment of `license` (§4.1), where the URI *does* have a declared home.

### 5.4 The 2023-07-18 / 2023-07-19 start-date discrepancy

`collection_timeframes` carries two entries: the FAIRhub-declared collection window opening 2023-07-19, and the BMJ Open pilot-enrolment window opening 2023-07-18. The one-day discrepancy is already flagged in the adjacent `timeframe_details`. **Left as-is:** representing what each source states, with the conflict marked, is the correct handling under the disagreement rule; selecting one would suppress evidence.

### 5.5 Uniform `collection_type: processed_data` across the nine data directories

The CDS layout is uniformly post-conversion — device-native exports (`.fda`, `.sdt`, `.FIT`) are converted to DICOM, WFDB, OMOP CDM or Open mHealth before release, and healthsheet *preprocessing* Q3 states the raw data are not shared. `processed_data` is therefore accurate for all nine. **Left as-is:** the uniformity reflects the release, not a failure to discriminate. `metadata` remains correctly assigned to the root metadata collection.

### 5.6 `publisher: https://fairhub.io/`

The bundle's structured metadata gives `publisherName: "FAIRhub"`, a name; the slot's declared range is `uriorcurie`. The URI form satisfies the range and identifies the same entity. The distinct `managingOrganization` with ROR `https://ror.org/01yc7t268` has no declared slot and is retained as a documented disagreement in `notes` item (4). **Left as-is.**

### 5.7 Omission of `citation`

FAIRhub and the license both redirect to `docs.aireadi.org` for citation instructions; the bundle contains no formatted citation string for the dataset. Emitting a pointer to where the citation lives would not answer the field. **Omission confirmed as deliberate and evidence-backed.**

### 5.8 Omission of `download_url`

Access is gated: verified-ID login, attestation of T2DM-related research use, and license acceptance. No direct data URL exists in the bundle. The landing page is carried in `page`. **Omission confirmed as deliberate.**

### 5.9 Referent

Both records resolve `Dataset` to **Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0** (DOI `10.60775/fairhub.3`, released 2025-11-17, 2,280 participants, 356,343 files, 3.82 TB). This was chosen over v2.0.0 — which the input sheet selects but which FAIRhub marks as no longer accessible — and over the AI-READI *study*, which the IRB protocol and NIH RePORTER describe. The v2.0.0 and v1.0.0 records are represented as `related_datasets` and their distinguishing facts confined to `notes`. The choice is held consistently across both records. **Unchanged from Phases 1–2.**

---

## 6. Residual notes

- No factual content was added during reconciliation that was not already present in the declared bundle; every promotion moved existing, sourced content from prose into the field that declares it.
- Two schema limitations are recorded above and are not defects in these records: `Creator` has no name or identifier field (§5.1, §5.2), and `conforms_to` has no companion field for a specification URI (§5.3).
- Full and core now agree on every slot where both are populated. The remaining divergence is scope only: the full record carries `variables`, `file_collections` and `instances` at greater granularity than the core record's reduced profile admits.