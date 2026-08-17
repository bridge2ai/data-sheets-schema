# Phase 4 Reconciliation — CHORUS

**Full record:** `data/d4d_concatenated/claudecode_agent/gate_test/CHORUS_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/gate_test/CHORUS_d4d_core.yaml`
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar deck; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14)

---

## 1. Referent

`Dataset` admits one referent. The referent held across both records is **the CHoRUS multimodal critical-care dataset itself** — the controlled-access, multi-site collection of OMOP-standardized EHR, waveform, imaging, EEG and tokenized-note data described in the webinar deck's modality table and in the chorus4ai.org dataset snapshot.

It is **not** the CHoRUS project or consortium, and **not** the AIM-AHEAD Bridge2AI for Clinical Care Training Program. Three of the four bundle files are substantially about the project or the training program rather than the dataset; several audit findings (6, 3, 14) turn on material from those files being read as dataset facts. The referent choice was re-confirmed during reconciliation and applied as the test for each disputed slot.

---

## 2. Audit outcome

19 findings: 0 high, 6 medium, 13 low. No finding alleged reuse of a prior D4D record, and none alleged a fact drawn from outside the declared bundle other than by expansion of bundle strings (findings 2, 8, 9). Both records validated before reconciliation and were re-validated after.

**Disposition:** 16 accepted in full, 2 accepted in part, 1 declined.

---

## 3. Changes made

### 3.1 Evidence-boundary corrections

**Finding 2 — `CTP-deid` expansion (accepted).**
`is_deidentified.deidentification_details` and the `preprocessing-image-deid` entry in `preprocessing_strategies` asserted "CTP-based image de-identification." The bundle lists `CTP-deid` as a repository name with no description, no language and no expansion of the acronym. Both mentions were removed. What survives is what the deck states: 1,000 images currently available, with de-identification in process for a larger cohort. The `privacy_scan_tool` repository was retained where cited, because the bundle supplies its own description ("A Privacy Scan tools for medical records").

**Finding 8 — institution inferred from email domain (accepted).**
`maintainers` carried "Access requests are handled at Emory University," derived from `dbold@emory.edu`. The institution name was removed; the maintainer object now records the access-request address as the bundle states it, with no name or affiliation asserted. For Jared Houghtaling, "Tufts Medicine" (derived from `tuftsmedicine.org`) was replaced with "Tufts," which the webinar deck states directly in the curriculum host column, with a `source_caveats` noting that the deck gives the host institution only as "Tufts" while the contact address is a Tufts Medicine domain.

**Finding 9 — `media_type: application/dicom` (accepted).**
Removed from the full record. The value came from general knowledge of the DICOM IANA registration, not from the bundle, and it was the only object-level disagreement between the two records. Full and core now agree on `distribution_formats`.

**Finding 14 — repository existence read as applied procedure (accepted in part).**
`preprocessing-geocoding` was removed outright: `UF-Geocoding` is a fork of an external lab repository, and the bundle establishes only that the code sits in the organization, not that it was run over the released data. `cleaning-characterization-reports` was retained, because the `CHoRUSReports` repository carries its own description of an active practice ("producing characterization reports to return to sites following their data submissions"), but the inferred consequence clause — "allowing data quality issues to be identified and resolved at source" — was deleted and a `source_caveats` added recording that the bundle evidences the reporting practice, not its effect on the released extract.

### 3.2 Field-fit corrections

**Finding 1 — `principal_investigator` for five non-PIs (accepted).**
Only ROSENTHAL, ERIC S. is named principal investigator in the bundle (NIH RePORTER, application 10472824, core project OT2OD032701). The remaining five names appear solely under "Bridge2AI CHoRUS Leadership Team" in the webinar deck.

`Creator` declares no person-bearing field other than `principal_investigator`, so removing the field would discard the names entirely. The resolution taken: the five objects retain `principal_investigator` as the only structurally available carrier for a named person, and each now carries an explicit `source_caveats` stating that the bundle lists the individual as a CHoRUS leadership team member and does not identify them as a principal investigator. Rosenthal's object carries no such caveat. This records the distinction the evidence makes while keeping the names in a declared field rather than in prose.

**Finding 3 — community ethics work as `EthicalReview` (accepted).**
`ethical_reviews` was removed. The class documents IRB approvals, ethics committee reviews and compliance certifications; the bundle describes community-facing ethics focus groups and analysis of the legal and regulatory landscape — activities the project performs, not a review of this dataset by a reviewing body. `reviewing_organization: "CHoRUS Ethics pillar (Ethical and Trustworthy AI)"` named a project workstream, not a reviewing organization. The substantive content (the Ethics pillar, focus groups to determine what data is appropriate for public sharing, the legal framework for collecting data at scale) already sits in `purposes` and `tasks`, where the abstract's framing supports it. No IRB approval, ethics board or protocol number appears anywhere in the bundle, so the slot is now correctly empty.

**Finding 6 — training-program access rules as dataset governance (accepted).**
`data_governance.access_review_process` described the registration form, licensing agreement, compute provisioning and `.edu` email requirement as the dataset's access-review process. Every one of those comes from AIM-AHEAD training-program eligibility slides and governs access for that program's trainees. The field was rewritten to scope the description explicitly to the AIM-AHEAD Bridge2AI for Clinical Care Training Program cohort, and to state separately the only general route the bundle gives: access requests directed to the two addresses on the GitHub README. The disclosure previously buried in `notes` is now in the process text itself.

**Finding 7 — `committee_contact` with no committee (accepted).**
Removed. The bundle names no access committee, no committee membership and no review body; Houghtaling appears only as one of two "Request access" contacts. Both contacts are carried in `maintainers`, which is where the bundle's evidence actually fits. `committee_name`, `committee_members` and `appeal_process` remain unpopulated, as before.

**Finding 5 — metadata-schema strings used as distribution formats (accepted).**
`distribution_formats[].format` values such as "Yes (OMOP schema with extensions)" and "Yes (PhysioNet schema extended)" were taken from the deck's *Published metadata schema* column and repurposed as statements about the data's own encoding. Each `format` was reduced to the value in the *Data standard* column, which the deck states directly: OMOP, OHNLP, DICOM, WFDB, EDF+ and Persyst. The metadata-schema publication status is no longer asserted at `distribution_formats`; it is carried once, at the `limitation-metadata-pending` entry in `known_limitations`, under the caveat described next.

**Finding 15 — `status` holding narrative (accepted).**
Reduced to `released`, supported by the chorus4ai.org heading "Current Released Dataset." The two sentences of release-state narrative were deleted as duplicative; the same content is already in `description`, `known_limitations` and `updates`.

**Finding 19 — `notes` restating structured content (accepted).**
The sentence restating award OT2OD032701 was removed; the award is carried in `funders`. `notes` now holds only the two items no structured slot or the description can carry: the chorus4ai.org banner stating the repository is under review for potential modification in compliance with Administration directives, and the NIH disclaimer.

### 3.3 Accuracy and consistency corrections

**Finding 4 — garbled modality table (accepted).**
In the preprocessed bundle the deck's table is flattened: the *Access control*, *Metadata* and *Published metadata schema* columns arrive as free-floating cell values interleaved with the row labels, so the row-to-cell alignment is reconstructed rather than read. A `source_caveats` recording this was added at three places that depend on the reconstruction: `instances`, `distribution_formats`, and `known_limitations[limitation-metadata-pending]`. The reconstructed alignment was retained — it is the reading the column ordering and cell sequence best support — but it is now flagged as reconstructed rather than presented as read.

**Finding 12 — description contradicting `confidential_elements` (accepted).**
The description implied clinical notes fall outside controlled access. The deck lists clinical notes as Controlled; the stated exception concerns storage location, not access control ("OMOP and telemetry in enclave except: Clinical notes – stored locally except tokens"). The description was rewritten so that all nine modalities are controlled-access, with clinical notes stored locally and only tokens moving into the enclave. This matches `confidential_elements`, which was already correct.

**Finding 13 — count unit mismatched to instance type (accepted).**
`instances[instance-imaging-study].instance_type` was changed from "Radiology imaging study" to "Admission with radiology data," so the declared type matches the 7,642 figure the bundle actually reports. The existing `source_caveats` was kept and extended to note the separate 1,000-image figure from the webinar deck, which the record already reports as a source conflict.

**Finding 11 / 18 — holdout test set stated in future tense (accepted).**
The NIH abstract is prospective throughout: "The dataset will also provision a holdout test set," "sequestering holdout datasets for external validation." Nothing in the bundle indicates the holdout set exists or is accessible. The subset object was removed from the full record's `subsets` and from the core record's `resources`; the holdout provision is retained as a `Purpose` entry, which is where the abstract's forward-looking statements belong. This also resolves finding 18: there is no longer an asymmetric holdout object, and no orphaned `#subset-` identifier in the core record.

**Finding 10 — `at_risk_populations` (accepted).**
Removed. The object carried one inferred boolean and a caveat conceding the inference. Inclusion of at-risk groups was deduced from the presence of PICU and NICU admissions; the bundle documents no special protections, no assent procedures and no guardian consent. Under the omission-over-inference rule the correct value is an absent slot.

### 3.4 Additions

**Finding 16 — `machine_annotation_tools` (accepted in part).**
Added, with one tool: the OHNLP toolkit, which the deck states is used to extract and tokenize clinical notes, with the OHNLP open-source schema recorded in `tool_descriptions`. The audit also proposed `privacy_scan_tool`; that was declined within an otherwise accepted finding, because scanning medical records for privacy exposure is not annotation, and adding it would repeat the field-fit error the audit flags elsewhere. The tool remains cited where it fits, in `preprocessing_strategies`.

**Finding 17 — `external_resources` (accepted).**
Added, one object per distinct resource: the chorus-ai GitHub organization (28 repositories, MIT-licensed); the Chorus_SOP centralized SOP documentation site; the chorus-mapping repository holding pooled tabular semantic mappings and the clinical validation SOP; the CHoRUS package status page; and `www.bridge2ai.org/chorus`. `archival` and `future_guarantees` were left unpopulated — the bundle says nothing about archival status or persistence guarantees for any of them. `extension_mechanism.contribution_url` was left in place; it answers a different question (where to contribute) and its retention is not duplication of the resource listing.

---

## 4. Left as-is

**Finding 1, partially.** The five leadership-team members remain in `principal_investigator` fields. The schema offers no alternative person-bearing field on `Creator`, and dropping the field would lose the names. The correction is carried by per-object `source_caveats` rather than by relocation. This is recorded here as a known imprecision forced by the class shape, not as an evidence claim.

**Finding 4, partially.** The reconstructed table alignment was kept rather than dissolved into "not determinable." The cell ordering in the flattened text supports one reading, and discarding it would remove substantive, evidenced content about nine modalities. The reconstruction is now disclosed at every slot that depends on it.

**Finding 14, partially.** `cleaning-characterization-reports` was retained; only `preprocessing-geocoding` was removed. The distinction is that the `CHoRUSReports` repository description states an ongoing practice in its own words, whereas `UF-Geocoding` is a fork with a description of what the upstream code does, not of what CHoRUS did with it.

**Finding 16, partially.** `privacy_scan_tool` was not added to `machine_annotation_tools`, for the reason given in §3.4.

**Reported source conflicts left standing.** The two cohort-size conflicts (100,000 anticipated admissions in the NIH abstract and chorus4ai.org "Anticipated Final Dataset" versus 50,000 in "Current Released Dataset" versus "over 45K unique admissions" as of August 2025 in the webinar deck) and the imaging conflict (1,000 images versus 7,642 admissions with radiology data) remain represented as conflicts rather than resolved to a single figure. The audit confirms this handling as correct and it was not changed.

**Slots left empty and confirmed empty.** `doi`, `citation`, `version`, `informed_consent`, `collection_consents`, `consent_revocations`, `retention_limit`, `human_subject_research.irb_approval`, `participant_compensation`, `annotation_analyses`, `splits`. The bundle addresses none of these for the dataset. Note that the webinar deck's $8,000 trainee stipend is compensation to *training-program participants*, not to human research subjects, and was not — and is not now — placed in `participant_compensation`.

---

## 5. Post-reconciliation state

| | Before | After |
|---|---|---|
| Full record, populated top-level slots | 49 | 47 |
| Core record, populated top-level slots | 32 | 30 |

Full-record net change: removed `ethical_reviews`, `at_risk_populations`, `subsets` (its only member was the holdout set); added `machine_annotation_tools`, `external_resources`.

The core record was re-projected from the amended full record rather than patched independently, so no core-only content exists. Every fact in the core record appears in the full record. The intentional projection drops are unchanged: `direct_collection`, `participant_privacy`, `third_party_sharing`, and object-level detail the core classes do not declare. The `subsets`-to-`resources` remapping noted at finding 18 no longer arises, since the holdout object is gone from both records.

`# Phase 4 reconciliation: completed` was written to the core header only after the changes above were applied.

**Validation:** both records re-validated after amendment.

- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → pass
- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → pass

**Provenance:** live record written via `d4d provenance record --project CHORUS --method claudecode_agent --label gate_test --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt`.

No prior D4D record was read, opened or consulted at any phase.