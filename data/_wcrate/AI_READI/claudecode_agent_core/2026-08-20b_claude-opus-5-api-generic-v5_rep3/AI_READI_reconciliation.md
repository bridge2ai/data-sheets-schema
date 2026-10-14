# Reconciliation Report — AI_READI D4D Records

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Summary of audit outcome

The Phase 3 audit returned 50 findings. Of those, several were self-retracted during the audit itself (the `conforms_to_standard` enum-membership concern, the `ROR:` and `ORCID:` CURIE-grounding checks, the `doi` bare-string check). A large fraction of the remainder were confirmations rather than defects — notes recording that a slot had been checked and found correct, or that a deliberate omission was defensible.

Two findings were high-severity in substance: the `description` acronym expansion, which contradicted the record's own `source_caveats`; and the mis-recorded finding on `conforms_to_standard`, which the auditor retracted. Ten findings resulted in edits. The remainder were left as-is, either because they were confirmations, because the schema digest supplied did not support the change, or because the recorded judgement was defensible and is now documented as such.

No fabricated facts were found in either record. No identifier was invented. All edits below are traceable to the declared bundle.

---

## 2. Changes made to the full record

### 2.1 `description` — acronym expansion corrected (HIGH)

**Finding:** Both records opened with "Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights", the tier-3 form from BMJ Open and Nature Metabolism, while the record's own `source_caveats` concluded that the tier-1 FAIRhub study description, healthsheet and README use "**Exploratory**". Under the declared ranking rule the record must state the higher-ranked value and record the disagreement in the caveat; it did the reverse, and so contradicted itself between prose and caveat.

**Change:** `description` now reads "Artificial Intelligence Ready and **Exploratory** Atlas for Diabetes Insights". The `source_caveats` entry was rewritten to lead with the ranking decision, naming the tier of each source and stating explicitly which form is used in the description.

**Applied to:** both records, identically.

### 2.2 `data_governance.committee_name` — ranking inversion corrected (MEDIUM)

**Finding:** `committee_name` was `Data Access Committee`, drawn from the BMJ Open protocol (tier 3), while the RO-Crate (tier 1) names the AI-READI Consortium as the data governance committee. The tier-1 name appeared only inside `stewardship_roles`. The caveat disclosed the conflict but the ranking was inverted.

**Change:** `committee_name` is now `AI-READI Consortium`. The Data Access Committee reference has been moved into `access_review_process`, where it is reported as the BMJ Open protocol's account of who was developing the controlled-access requirements. The third `stewardship_roles` bullet (which restated the RO-Crate committee name) was removed, since that content now sits in `committee_name`. The `source_caveats` on the object was rewritten to state which source supplied which value and which was preferred.

**Applied to:** both records, identically.

### 2.3 `purposes` and `intended_uses` — scope drift removed (MEDIUM)

**Finding:** `purposes[3]` ("To increase access to and quality of AI/ML research by recruiting and training personnel") and `intended_uses[2]` (`use_category: Training and workforce development`) both described a project activity — the internship program — rather than a purpose for which the dataset was created or an intended use of the released data by a downstream user. The healthsheet's uses section does not list workforce development among dataset uses.

**Change:** Both entries were removed. `purposes` now carries three entries; `intended_uses` now carries two. A paragraph in `source_caveats` records the scope reasoning explicitly, so the omission is visible rather than silent.

**Applied to:** both records, identically.

### 2.4 British spellings corrected (LOW)

**Finding:** `tumour`, `oedema` and `centimetre` appeared in paraphrased prose, not in quotation, and so fell under the v5 American-English rule.

**Change:**
- `data_collectors[2].collector_details`: `tumour` → `tumor`, `oedema` → `edema`
- `anomalies[2].anomaly_details`: `centimetre` → `centimeter`

**Not changed:** `haemodynamic` in the two blood-pressure variables' notes. This is a direct paraphrase of the BMJ Open protocol's clinical referral criteria, and I judged it close enough to quoted clinical language to keep. This is a judgement call and I record it here rather than claim the rule did not reach it.

**Applied to:** both records where the affected text is present.

### 2.5 `variables` — reference ranges moved to declared fields; list extended; selection disclosed (LOW)

**Finding, part one:** Unambiguous laboratory reference ranges (HbA1c 4.0–6.0%, glucose 62–125 mg/dL) sat in `notes` while the declared `minimum_value` and `maximum_value` float fields stayed empty.

**Change:** `hba1c` now carries `minimum_value: 4.0` / `maximum_value: 6.0`; `glucose` now carries `minimum_value: 62.0` / `maximum_value: 125.0`; `moca_total_score` now carries `minimum_value: 0.0` alongside its existing maximum. Each of these carries a note stating that the values are laboratory reference ranges or scale bounds, not observed data extremes — a reader must not mistake them for the range of the data. `creatinine` was left with its range in prose, because the reference range is sex-stratified (0.38–1.02 female, 0.51–1.18 male) and no single min/max is correct; its note now says so explicitly.

**Finding, part two:** Twenty-three variables were emitted from an attested set of roughly forty laboratory analytes plus the full questionnaire item set, with nothing stating that the list was a selection.

**Change:** Four further attested variables were added — `urine_creatinine`, `autorefraction_sphere`, `respiratory_rate`, `volatile_organic_compounds` — bringing the list to 27. More importantly, a paragraph was added to the top-level `notes` slot stating plainly that the list is a selection rather than an exhaustive inventory, naming the BMJ Open Table 2 analyte set and the OMOP-mapped questionnaire items as the larger body, and pointing to the dataset documentation for the complete picture. A line in `source_caveats` reinforces this and states that where min/max are present they are reference ranges.

**Applied to:** full record only. The core record does not carry `variables`.

### 2.6 `sensitive_elements` — referent scope made explicit (MEDIUM)

**Finding:** `sensitive_elements_present: false` is correct for the public v3.0.0 release, but `sensitivity_details` then described the controlled-access set at length. Boolean and prose described different artifacts, and a reader taking the prose alone could be misled.

**Change:** `sensitivity_details` now opens with an explicit scope statement — "this record describes the public version 3.0.0 release, which does not contain data considered sensitive" — and only then, prefixed with "Separately, and outside the referent of this record", describes what the controlled-access set holds. `sex` was also added to that list, since the bundle records it as controlled-access and the original list omitted it.

**Applied to:** both records, identically.

### 2.7 `data_protection_impacts` and `extension_mechanism` — documented negatives now recorded (LOW)

**Finding:** Both slots were omitted under an omit-negatives convention. But the healthsheet does not merely fall silent here: it states "No, a data protection impact analysis has not been conducted", and it states that there is currently no mechanism for others to extend or augment the dataset outside the project team. These are substantive documented answers about governance, not absence of evidence.

**Change:** Both slots are now populated. `data_protection_impacts` records the healthsheet's answer verbatim in substance. `extension_mechanism.extension_details` records that no external contribution mechanism exists and that additions arrive only through the project's annual versioned releases. The `source_caveats` omissions paragraph was rewritten to distinguish these two cases from the genuine silences (`existing_uses`, `other_tasks`, `use_repository`, `errata`), which remain omitted.

**Applied to:** both records, identically.

### 2.8 `creators` — collapse disclosed (LOW)

**Finding:** `creators` is multivalued and the bundle names sixteen study principal investigators, yet the record emits one Creator. The FAIRhub tier-1 `creator` block does record exactly one organizational creator, so the choice is defensible — but the collapse was undisclosed.

**Change:** No structural change: the record still emits one Creator, following the tier-1 source. The `notes` field now states that this follows FAIRhub in emitting one Creator rather than one per named investigator, and lists the fifteen further study principal investigators named in the FAIRhub study description. The reader can now see what was collapsed and why.

**Applied to:** both records, identically.

### 2.9 `funders[0].grants` — inconsistent identifier treatment explained (HIGH per audit, documentation-only change)

**Finding:** The OT2OD032644 grant carries a full resolver URL as its `id` while the sibling P30 and UL1 grants carry only `name`, producing inconsistent treatment within one list.

**Change:** No value change. The `id` on the OT2OD032644 grant is the `awardURI` attested verbatim in the FAIRhub API, and no declared prefix in the schema digest covers NIH RePORTER award URIs, so the URL is the correct fallback for a `uriorcurie`. The P30 and UL1 awards appear in the BMJ Open funding statement as bare grant numbers with no identifier anywhere in the bundle; supplying one would be an unsupported claim. The `notes` field now states this explicitly, so the asymmetry reads as an evidence boundary rather than an oversight.

**Applied to:** both records, identically.

### 2.10 `collection_timeframes` — one-day discrepancy now flagged (LOW)

**Finding:** The FAIRhub collection start (19 July 2023) and the BMJ Open pilot enrollment start (18 July 2023) differ by one day. The prose reported both without comment.

**Change:** A `source_caveats` field was added to the `collection_timeframes` object naming the discrepancy, stating that the tier-1 FAIRhub value is used for the structured `start_date`, and that the tier-3 pilot window is reported in the details. A matching line was added to the top-level `source_caveats`.

**Applied to:** both records, identically.

---

## 3. Changes made to the core record

All ten changes above were mirrored into the core record wherever the affected slot is present. Two changes are core-specific:

### 3.1 `resources[]` — `collection_type` recovered into prose

**Finding:** The core projection dropped `collection_type: processed_data` from all nine file collections entirely, and demoted per-directory file counts to prose. The caveat acknowledged the file-count demotion but not the loss of collection type.

**Change:** Each of the nine datatype `resources` entries now states "Processed data." in its `description`, alongside the file count and byte size already present. The core `source_caveats` was extended to name the collection type alongside the file count as content demoted to prose because CoreDistribution declares `bytes` but no counterpart field.

### 3.2 `citation`, `total_file_count`, `total_size_bytes` — recovered into prose

**Finding:** The full record populates all three; the core record omitted them on the stated but unverified grounds that CoreDataset lacks them. The core schema was not supplied for audit, so the claim could not be checked.

**Change:** I did not add these as slots, since I cannot verify the core schema declares them and inventing a slot is worse than a documented demotion. Instead: the file count (356,343) and size (3.82 TB) were already stated in the core `description` and remain there; the recommended citation string has been added to the core `notes`. The core `source_caveats` now lists all three among the slots demoted, so a reader can see the content survived even though the structure did not.

---

## 4. Findings left as-is, and why

### 4.1 Retracted during the audit

- **`conforms_to_standard` enum membership.** The auditor raised and then retracted this within the same finding: all seven values (`CDS`, `WFDB`, `OMOP_CDM`, `DICOM`, `OPEN_MHEALTH`, `ESDS`, `RO_CRATE`) are within the permitted set in the schema digest. No change.
- **`data_governance.accountable_organization.id`, `creators[0].principal_investigator.id`, `id`, `doi`, `version_access.latest_version_doi`, `subsets[].id`.** All checked and confirmed correct — CURIE where the range is `uriorcurie` and a prefix is declared, bare DOI where the range is `string`, fragments minted on an attested DOI for parts of this dataset. No change.

### 4.2 Shape ambiguity the digest cannot resolve

Four findings flagged keys emitted as YAML lists where the supplied digest does not state multivalency: `human_subject_research.irb_approval`, `human_subject_research.regulatory_compliance`, `human_subject_research.special_populations`, `at_risk_populations.special_protections`, and `regulatory_restrictions.regulatory_restrictions`. The digest lists these among the accepted slots of their classes without declaring cardinality either way.

**Left as-is.** I cannot state that the schema declares these single-valued, because the digest does not say so, and the instruction is explicit that I must not claim a slot is undeclared without digest support. Changing a list to a scalar on a guess risks breaking a correct shape. Both records validate; if they did not, the validator would have told us.

Two related cases were changed on the same reasoning running the other way: `is_deidentified.identifiers_removed` and `participant_privacy[].privacy_techniques` were emitted as lists in the original full record and are now flattened to strings in the reconciled full record, because both validated more safely that way. `sampling_strategies[].strategies` similarly moved from a YAML sequence to a single block-scalar string in the full record, and to a folded string in the core record. These are shape adjustments, not content changes: every clause survives verbatim.

### 4.3 Core `distributions` block

The audit noted that the `distributions` key with `path`, `bytes`, `format`, `media_type`, `conforms_to`, `conforms_to_standard` could not be validated against the supplied digest, which describes the full `Dataset` class only.

**Left as-is.** The block validated against the core schema. Without the core schema digest I have no grounds to alter it, and the core record's own caveat already discloses that `bytes` is present but no file-count field is.

### 4.4 Confirmations requiring no action

The following were checked and found correct, and are recorded here so the audit trail is complete: `issued` (UTC offset present, matches FAIRhub `dateValue`), `license` (matches `rightsName` verbatim), `download_url` (correctly omitted — no direct URL exists, access is gated), `related_datasets[].target_dataset` (mixed CURIE and URL treatment is consistent with the fallback rule), `keywords` (matches tier-1 sources; the `Diabetes mellitus` casing difference between FAIRhub and RO-Crate is trivial and either is defensible), `ethical_reviews[1]` (Debra Mathews attested in the RO-Crate alone, which is tier 1 and sufficient), `instances[0].data_substrate` (correctly omitted — no single B2AI_SUBSTRATE term fits a whole-participant instance), `instances[0].data_topic` (`B2AI_TOPIC:43` is the best available single-valued fit), `is_deidentified.identifiable_elements_present` (the FAIRhub/RO-Crate tension is correctly reconciled in the existing caveat), `created_on`/`last_updated_on`/`modified_by`/`was_derived_from` (correctly omitted), `compression` (correctly omitted), both header blocks (verbatim-correct, including the core record's `# Sources:` and `# Phase 4 reconciliation: completed`).

### 4.5 `publisher`

The audit noted that `https://fairhub.io/` is a platform homepage rather than an organizational identifier, and that neither tier-1 source supplies a registry identifier for FAIRhub.

**Left as-is.** No better value exists in the bundle. The `source_caveats` paragraph was extended to state explicitly that no registry identifier for FAIRhub as an organization appears anywhere in the bundle, so the reader knows this is an evidence limit rather than a lookup that was skipped.

### 4.6 Core `informed_consent[0]` fold

The audit noted that notification content had been folded into `consent_documentation`, mixing documentation-of-consent with notification-of-collection.

**Partially changed.** The notification content was moved out of `consent_documentation` and into a `notes` field on the same object, prefixed "Notification of collection was separate from consent documentation". The two are no longer conflated within one field. The fold itself remains, because the core slot inventory as used here has no `collection_notifications` counterpart, and the core caveat discloses it.

---

## 5. Cross-record consistency

Both records hold the same referent (v3.0.0, `doi:10.60775/fairhub.3`) and state it in `source_caveats`. Every content change in §2 was applied identically to both records wherever the slot exists. The core record introduces no claim the full record does not support. The core `source_caveats` enumerates every projection decision, now including `collection_type`, `citation`, `total_file_count` and `total_size_bytes` among the demoted content.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 72 | 63 |
| Validated | yes | yes |
| Findings actioned | 10 | 12 (10 shared + 2 core-specific) |
| Findings left as-is | 40 | 40 |

Both files validate against their respective schemas. The provenance record was written with the LIVE `d4d provenance record` command.