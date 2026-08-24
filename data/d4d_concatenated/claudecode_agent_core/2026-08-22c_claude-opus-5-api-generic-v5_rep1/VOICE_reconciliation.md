# VOICE — Phase 4 Reconciliation Report

## Scope

This report records the outcome of the Phase 3 provenance and source audit and the Phase 4 reconciliation applied to the paired full and core D4D records for the Voice project (the Bridge2AI Precision Public Health Grand Challenge). The audit returned 29 findings: 2 high, 9 medium, 18 low. Every finding is dispositioned below against the actual difference between the original and reconciled records.

---

## High-severity findings

### 1. Core record: undeclared `distributions` slot (high) — **fixed**

**Finding.** The core record carried a top-level `distributions` block of three objects with keys `format`, `media_type`, `path`, `notes`, `source_caveats`. The schema digest for `Dataset`/`CoreDataset` declares no `distributions` slot and no range whose required keys match those objects. The digest declares `distribution_formats` (range `DistributionFormat`) for this content, which the core record already populated separately. Two of the three objects additionally declared `format: JSON` / `media_type: application/json` for folders whose payload is Parquet — a mismatch the object's own `source_caveats` conceded.

**Change.** The entire `distributions` block was removed from the core record. Its substantive content — the nine Parquet feature files with their per-file record counts and tensor dimensions, the `features/`, `phenotype/` and `metadata/` folder paths, the phenotype subfolder inventory, and the per-recording metadata description — was folded into the `notes` fields of the three surviving `distribution_formats` entries (Apache Parquet, Tab-separated values, JSON), each entry now describing the files that genuinely carry that format. The `source_caveats` that apologised for the format mismatch is gone because the mismatch is gone.

### 2. Core record: `file_collections` content displaced (high) — **resolved, by a different route than the audit proposed**

**Finding.** The full record's three `FileCollection` objects (features, phenotype, metadata, each with `id`, `collection_type`, `path` and per-file counts) had no counterpart in the core record; that content had been relocated into the non-schema `distributions` block.

**Change.** The audit recommended porting the three `FileCollection` objects across. Reconciliation instead routed the content into `distribution_formats` notes, as described above, and left `file_collections` unpopulated in the core record. Rationale: the core record is a projection, and the file-layout detail is now present and queryable in a slot the core schema declares, without duplicating it in two slots. The full record retains `file_collections` in its structured form. This is a deliberate departure from the audit's suggested remedy; the defect it identified — content held in an undeclared slot — is resolved either way.

---

## Medium-severity findings

### 3. Both records: five-cohort enumeration substitutes controls for pediatrics (medium) — **fixed in both**

**Finding.** The core record's second `Subpopulation` object stated the five cohort categories as "voice disorders, respiratory disorders, neurological and neurodegenerative disorders, mood and psychiatric disorders, and controls." The project documentation names the fifth as pediatric voice and speech disorders, with controls a separately recruited comparison group. The full record's `subsets` block implied the same five-way framing.

**Change, core.** The `Subpopulation.identification` field now names all five consortium categories correctly, including pediatric voice and speech disorders, and states that the pediatric category is published separately so this release covers four adult disease cohorts plus separately recruited controls.

**Change, full.** The same correction was made in the corresponding `Subpopulation` object. In `subsets`, each of the four disease-cohort entries now closes with "One of the consortium's five disease cohort categories," and the Controls entry states explicitly that controls are "a separately recruited comparison group rather than one of the five disease cohort categories; the fifth category, pediatric voice and speech disorders, is published as a separate dataset." The `related_datasets` entry for the pediatric dataset now adds that it "covers the fifth of the consortium's disease cohort categories, pediatric voice and speech disorders." Top-level `description` in both records was reworded from a five-item list to "spanning voice disorders, respiratory disorders, neurological and neurodegenerative disorders, and mood and psychiatric disorders, together with control participants who do not have the conditions of interest." A paragraph explaining the cohort accounting was added to `source_caveats` in both records.

### 4. Core record: `relationships` omitted (medium) — **addressed via `notes`**

The full record's `relationships` content (healthsheet statement that instances are unrelated; participant_id/session_id/task_name linkage) is now stated in the core record's top-level `notes`. The `relationships` slot itself remains unpopulated in the core record.

### 5. Core record: `splits` omitted (medium) — **addressed via `notes`**

The statement that no recommended train/validation/test splits are provided, and that researchers should construct their own with the multivariate distribution in mind, is now in the core record's top-level `notes`. The `splits` slot remains unpopulated in the core record.

### 6. Core record: `subsets` omitted (medium) — **addressed via `notes`**

A cohort-by-cohort paragraph was added to the core record's `notes` reproducing the diagnoses and gold-standard validation methods for each of the four adult disease cohorts and the control group, with the corrected statement about controls' status. The `subsets` slot remains unpopulated in the core record; the full record retains the five structured `DataSubset` objects.

### 7. Core record: `citation` omitted (medium) — **left as-is**

Comparing the two core records, `citation` is absent from both. The full record carries the PhysioNet-supplied citation verbatim. Left unchanged: the core record's `id`, `doi` and `page` resolve to the PhysioNet landing page that publishes the citation in six styles, and the core projection is not obliged to carry every full-record slot.

### 8. Core record: `variables` omitted (medium) — **addressed via `notes`**

The six variable descriptions (participant_id, session_id, task_name, n_frames, spectrogram, mel_spectrogram) are now summarised in the core record's `notes`, including the spectrogram and Mel spectrogram dimensions. The `variables` slot remains unpopulated in the core record.

---

## Low-severity findings

### 9. Core record: `direct_collection` omitted (low) — **addressed via `acquisition_methods`**

The first `InstanceAcquisition` object in the core record now closes with "Data were collected directly from the individuals in question rather than obtained via third parties." The `direct_collection` slot remains unpopulated in the core record; the full record retains its `DirectCollection` object unchanged.

### 10. Core record: `collection_consents` omitted (low) — **addressed via `informed_consent`**

The consent-scope statement about non-restriction to commercial, geographic, disease-specific, genetic or methods-development use was appended to `informed_consent[0].consent_scope` in the core record. `collection_consents` remains unpopulated there; the full record retains both `CollectionConsent` objects.

### 11. Core record: `collection_notifications` omitted (low) — **addressed via `informed_consent`**

The IRB-approved notification procedure — explanation in detail, time for questions, teach-back confirmation, statement that participation is voluntary and does not affect medical care — was added to a new `notes` field on the core record's `informed_consent` object. The slot remains unpopulated there.

### 12. Core record: `consent_revocations` omitted (low) — **addressed via `informed_consent`**

`informed_consent[0].withdrawal_mechanism` in the core record was extended with the longitudinal-collection provision: participants may withdraw at any time, data already collected is retained, and one time-point constitutes study completion. The slot remains unpopulated there.

### 13. Core record: `participant_privacy` omitted (low) — **addressed via `is_deidentified`**

`is_deidentified.deidentification_details` in the core record was extended with the pseudonymous linkage practice, the password-protected REDCap holding of identifiable data at each institution, the controlled-access and secure-transmission techniques, the federated learning arrangement, and the consortium's residual-risk statement that voice can never be fully de-identified. The `participant_privacy` slot remains unpopulated in the core record; the full record retains the `ParticipantPrivacy` object.

### 14. Core record: `participant_compensation` omitted (low) — **addressed via `informed_consent`**

The gift-card amounts (US$40 under 90 minutes, US$80 over, three sessions maximum, US$120 cap) were added to the core record's `informed_consent[0].notes`. The slot remains unpopulated there.

### 15. Core record: `third_party_sharing` omitted (low) — **addressed via `distribution_dates`**

The distribution-and-redistribution statement — broad distribution outside the creating entity, PhysioNet and Health Data Nexus routes, Synapse controlled access, and the DTUA prohibition on onward disclosure without written consent — was appended to `distribution_dates[0].notes` in the core record. The slot remains unpopulated there.

### 16. Full record: `instances` substrate for acoustic recordings (low) — **fixed in both**

`data_substrate: B2AI_SUBSTRATE:49` (Waveform Data) was removed from the acoustic-recording `Instance` in both records. The object's `notes` now states that the underlying raw modality is waveform audio, withheld from this release, and that no substrate term is asserted because the distributed instances are derived tensors rather than waveforms.

### 17. Full record: `instances` substrate for questionnaire records (low) — **fixed in both**

`data_substrate: B2AI_SUBSTRATE:80` (Questionnaire response data) was removed from the third `Instance` in both records, and `instance_type` was changed from "questionnaire and clinical record" to "participant questionnaire and clinical record." The `notes` now records that no substrate term is asserted because the instance spans questionnaire responses, enrollment records and clinician-supplied diagnosis tables, which no single vocabulary term covers.

### 18. Both records: `id` pinned to version DOI rather than concept DOI (low) — **left as-is, caveat added**

`id` remains `doi:10.13026/8xbn-nq66` (version 3.1.0) and `version_access.latest_version_doi` remains `doi:10.13026/37yb-1t42` in both records. Both are attested. A sentence was added to `source_caveats` in both records noting that `id` is pinned to the 3.1.0 DOI and that PhysioNet additionally assigns a latest-version DOI for the series, recorded under `version_access`.

### 19. Both records: `known_biases.affected_subsets` generalizes past the sources (low) — **fixed in both**

The `affected_subsets: ['Disease cohorts recruited predominantly at a single site']` value was removed from the `measurement_bias` object in both records. No source names any cohort as predominantly single-site; the `bias_description`, which states that participants were screened for different disorders based on site and that devices differed per site, is retained unchanged.

### 20. Both records: `collection_timeframes` conflates collection window with award period (low) — **fixed in both**

`timeframe_details` in both records now states only the healthsheet's twelve-month collection period. The NIH RePORTER project period (1 September 2022 to 30 November 2026) was moved into `source_caveats` on the same object, with the explanation that it is the award period rather than a data collection window and is not recorded as one. `start_date` and `end_date` remain unpopulated.

### 21. Both records: `publisher` as bare URL (low) — **left as-is**

`publisher: https://physionet.org` is unchanged in both records. The digest declares no prefix covering PhysioNet as an organization, and the bundle attests no organization-registry identifier for it, so the URL fallback permitted by the `uriorcurie` range stands.

### 22. Both records: `human_subject_research` single-element lists holding paragraphs (low) — **partially addressed**

`irb_approval`, `regulatory_compliance` and `special_populations` remain lists in both records. In `regulatory_compliance`, the three compliance regimes were rewritten as a semicolon-delimited enumeration ("HIPAA; the Common Rule; and a Certificate of Confidentiality, which must be asserted against compulsory legal demands for identifying information about a participant"). In `special_populations`, the three previously separate elements were merged into one continuous element covering adult eligibility, the pediatric arrangement and the cognitively impaired cohorts. The list shapes themselves were not changed, since the digest neither confirms nor denies multivalued status for these fields and both records validated as written.

### 23. Both records: `at_risk_populations.at_risk_groups_included` inconsistent with cohorts (low) — **fixed in both**

The flag was changed from `false` to `true` in both records. Two `special_protections` entries were added: the neurological cohort's requirement of an existing clinical diagnosis with an age range of 44 to 85 and exclusion of those with symptom-altering surgery, and the requirement that participants be able to provide informed consent in English. `source_caveats` now explains that the adult dataset enrolls only participants 18 and over but that its recruited cohorts include participants with mild cognitive impairment and dementia, which is the basis for the `true` value. `guardian_consent` remains a single-element list; see finding 22 on list shape.

### 24. Both records: `sensitive_elements` object flagged `false` inside a list of present elements (low) — **fixed in both**

The fourth `SensitiveElement` object (`sensitive_elements_present: false`, describing removed content) was deleted from both records. Its substance — removal of raw voice recordings as biometric data, and removal of all REDCap-flagged identifier fields and highly sensitive elements — was folded into `is_deidentified.deidentification_details`, where it belongs. Three objects remain in `sensitive_elements`, all flagged `true`.

### 25. Both records: `data_governance.committee_contact` unpopulated (low) — **addressed by caveat and stewardship role**

`committee_contact` remains unpopulated in both records; its declared range is `Person`, and the bundle names no individual, only the office and its address. A `stewardship_roles` entry now reads "The Data Access Compliance Office reviews and approves controlled-access applications for raw audio, and is reached at DACO@b2ai-voice.org," and `source_caveats` on the `DataGovernance` object explains why `committee_contact` and `committee_members` are left unpopulated. `access_decision_timeframe` was also added to both records, stating that no timeframe is published and applications are reviewed on receipt.

### 26. Both records: `download_url` unpopulated (low) — **left as-is**

Unchanged. PhysioNet exposes files only after credentialing and Synapse only after institutional sign-off; neither is a direct data URL. Omission remains correct.

### 27. Both records: `total_file_count` and `total_size_bytes` unpopulated (low) — **left as-is**

Unchanged. The bundle states no file total or byte total.

### 28. Both records: `use_repository` unpopulated (low) — **left as-is**

Unchanged. The healthsheet answers the corresponding question "No."

---

## Other changes made during reconciliation

Two changes not driven by a numbered finding:

- **`Creator.principal_investigator` range.** In both records, each of the seventeen `Creator` objects previously nested a mapping under `principal_investigator` (`principal_investigator: {name: ...}`). This was flattened to a scalar (`principal_investigator: Yael Bensoussan`). The same flattening was applied to `EthicalReview.contact_person` in both records.
- **`identifiers_removed`, `privacy_techniques`, `missing_data_patterns`, `missing_data_causes`, `sampling_strategies.strategies`.** These were lists of short strings in both original records and are now single delimited strings, for consistency with how the surrounding scalar-ranged fields are written.

---

## Summary of disposition

| Disposition | Findings |
|---|---|
| Fixed as recommended | 1, 3, 16, 17, 19, 20, 23, 24 |
| Resolved by a different route | 2 |
| Content preserved in an adjacent declared slot | 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 25 |
| Partially addressed | 22 |
| Left as-is, with caveat added | 18 |
| Left as-is, no change warranted | 7, 21, 26, 27, 28 |

Both high-severity findings are resolved. The one medium factual defect present in both records — the cohort enumeration — is corrected in both, with the correction propagated to `description`, `subsets`, `subpopulations`, `related_datasets` and `source_caveats`. Every low-severity finding is either fixed, absorbed into a declared slot, or explicitly justified as left standing. No unsupported factual claim was introduced during reconciliation; every added sentence traces to the declared bundle, with tier-1 PhysioNet v3.1.0 preferred over the superseded v3.0.0 and over lower-tier sources at each point of disagreement.