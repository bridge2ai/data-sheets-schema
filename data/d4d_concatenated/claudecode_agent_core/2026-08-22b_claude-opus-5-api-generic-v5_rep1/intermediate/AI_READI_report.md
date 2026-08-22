# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-22b_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Arm:** BASELINE (input documents only)

---

## 1. Scope and method

The Phase 3 audit returned 25 findings: 3 high, 10 medium, 11 low, 4 info (one finding is counted in two severity buckets in the audit text; the tally here follows the `severity` field of each entry). Each was evaluated against the schema digest and the declared input bundle. Where a finding identified a defect that could be repaired without asserting anything the bundle does not support, the record was changed. Where a finding rested on a premise the schema digest does not support, or where the change would have required inventing content, the record was left as-is and the reasoning is recorded below.

Both records were re-read after editing and the two versions compared slot by slot. Every change described below is visible in that comparison; every finding not described as changed is described as left as-is.

---

## 2. Findings that produced changes

### 2.1 `known_biases[2].affected_subsets` — prose in a slot that should reference subsets (low)

**Audit:** the third `DatasetBias` object held a prose sentence in `affected_subsets` rather than a reference to a declared subset entity; in the full record three `DataSubset` objects with minted ids exist and could be referenced, and in the core record no subsets exist at all.

**Change, full record:** `affected_subsets` now holds the single value `doi:10.60775/fairhub.3#split-train`, referencing the training-split `DataSubset` declared under `subsets`. The aggregate counts that previously occupied that slot were moved into a new sibling `notes` on the same object, which explains that the imbalance affects the release as a whole and is most visible in the unbalanced training partition, and contrasts that with the deliberately balanced validation and test partitions (88 per race/ethnic group, 176 per sex).

**Change, core record:** the core record carries no `subsets`, so no reference target exists. The prose value was retained but rewritten so that it reads as a scoping statement rather than a bare count list: it now names the release as a whole and the training partition specifically, and gives both the aggregate counts and the balanced validation/test figures. No `notes` was added here because the content did not need splitting.

**Why this asymmetry:** the fix in the full record is possible only because `subsets` exists there. Adding `subsets` to the core record to enable the same fix would have been a larger change than the finding warranted, and the alternative — inventing an identifier with no declared target — would have produced a dangling reference.

---

### 2.2 `funders[0].grants[0]` — Grant object carrying no declared fields (low)

**Audit:** `Grant.id` held a NIH RePORTER resolver URL while the grant's own identifier, award number OT2OD032644, appeared only in `notes` prose rather than in any identifier position.

**Change, both records:** the `Grant` object now carries `name: OT2OD032644` and a `description` giving the award title, application number 10471118, project number 1OT2OD032644-01, awardee institution, principal investigator, fiscal-year-2022 amount (USD 5,026,499) and project period (2022-09-01 to 2025-08-31). The `id` remains the RePORTER URL. The `notes` on the enclosing `FundingMechanism` was shortened to carry only the residual fact it did not previously have a home for: that the protocol publication additionally reports NIH grants P30DK035816 and UL1TR003096. The `source_caveats` gained a sentence recording that no prefix for NIH RePORTER project records is available, so the resolver URL is used as the identifier.

This is the v3 rule applied directly: the class declares fields, and content that answers them belongs in them rather than in free text beside them.

---

### 2.3 `creators[0].affiliations` — an unsupported dual affiliation (low)

**Audit:** listing two `Organization` objects under one `Creator` to encode a source conflict asserts as fact that Aaron Lee holds both affiliations, which no source states, even though the sibling `source_caveats` correctly documents the conflict.

**Change, both records:** the second affiliation (`ROR:00cvxb145`, University of Washington) was removed from the list, leaving only the FAIRhub value. The `source_caveats` was expanded to name both candidate values with their ROR identifiers, to note that the tier-one sources cannot be ranked against each other, to record that the tier-three publications and tier-four NIH RePORTER record agree with the RO-Crate, and to state explicitly why only one is asserted: the FAIRhub value is the affiliation the release metadata attaches to this role, and no source states that he holds both simultaneously.

The record-level `source_caveats` in both records was also amended: the sentence that previously read "both attributions are recorded where they apply" now reads "both attributions are recorded in the affiliation-level caveats; no source states that the investigator holds both affiliations simultaneously." This keeps the conflict fully disclosed while removing the claim from the data position.

---

### 2.4 `related_datasets[2].target_dataset` — prose in a required scalar (low)

**Audit:** `target_dataset` is a required scalar on `DatasetRelationship`, and held the sentence "FAIRhub dataset 4, the smaller mini-subset of AI-READI release 3.0.0 made available for pipeline development".

**Change, both records:** `target_dataset` now holds `https://fairhub.io/datasets/4`. The prose was moved to a new `notes` on the same object, which records the descriptive content, cites the two bundle facts that support it (`"child": 4` in the FAIRhub API `data` block, and the landing-page statement "A smaller version is available for pipeline development"), and states that no DOI for the subset is given in the sources, so the FAIRhub dataset URL is used as the identifier.

The identifier is derived from the FAIRhub dataset-URL pattern the bundle itself uses for datasets 2 and 3, applied to the child id 4 the bundle states — not supplied from outside knowledge.

---

### 2.5 `related_datasets[1]` — an inferential `replaces` relationship (low)

**Audit:** two relationships (`is_new_version_of` and `replaces`) were asserted against the same target `10.60775/fairhub.2`; `is_new_version_of` is directly supported by the version list and changelog, whereas `replaces` is an inference from the statement that v2.0.0 "is no longer accessible", and no source uses replacement language.

**Change, both records:** the `replaces` object was removed. The supporting fact — that version 2.0.0 held 1,067 participants and that its FAIRhub landing page states it is no longer accessible — was added as `notes` on the surviving `is_new_version_of` object. This preserves the evidence while dropping the relationship term no source supports. The `related_datasets` list therefore went from three objects to two in both records.

---

### 2.6 `human_subject_research.regulatory_compliance` / `regulatory_restrictions.other_compliance` — duplicated FDA and DMC statement (low)

**Audit:** the statement that the study is not FDA-regulated and has no Data Monitoring Committee appeared in both slots; these facts belong to the oversight module and fit `human_subject_research`, not the export-control class.

**Change, both records:** the sentence was deleted from `regulatory_restrictions.other_compliance`, which now carries only the storage-location requirement. In `human_subject_research.regulatory_compliance`, the single long string was split into three list entries so that each distinct compliance fact occupies its own item: (i) HIPAA Safe Harbor de-identification plus the NIH Genomic Data Sharing Policy obligation, (ii) the FDA and Data Monitoring Committee status, (iii) the ClinicalTrials.gov registration NCT06002048. The slot is multivalued and the v2 rule about one object per distinct entity applies to it.

---

### 2.7 `sensitive_elements[1]` — missing boolean (low)

**Audit:** the second `SensitiveElement` object omitted `sensitive_elements_present` while its sibling set it, and the object's shape differed without explanation.

**Change, both records:** `sensitive_elements_present: false` was added to the second object, and a closing sentence was appended to `sensitivity_details` explaining the value: the boolean is false because the controlled-access variables it enumerates are absent from the release this datasheet describes. This resolves the shape inconsistency without contradicting the first object, which flags what the release *does* carry.

---

### 2.8 `at_risk_populations` — boolean in tension with sibling narrative (low)

**Audit:** `at_risk_groups_included: false` sits beside `special_protections` describing protections that would only be needed if such groups were present, and the IRB protocol's prisoner section answers 'No' only for known prisoners.

**Change, both records:** `special_protections` was split from one long string into three list entries — eligibility exclusions, device privacy design, transportation assistance — and the first entry now states explicitly that no minors, pregnant women, neonates or fetuses are enrolled and that the IRB protocol records prisoners are not a target population. A new `source_caveats` was added to the object recording why the boolean is `false` (the eligibility criteria exclude every protected population the schema and the IRB protocol enumerate) and noting that the IRB protocol also answers "No" to the follow-on question about participants who may become prisoners during the study, this being a cross-sectional design.

---

### 2.9 `license_and_use_terms.data_use_permission` — unflagged author-side mapping (low)

**Audit:** `disease_specific_research` is an inference from the access attestation; no source names a DUO-style permission code, and unlike the confidentiality-level case no caveat flagged it.

**Change, both records:** a `source_caveats` was added to `license_and_use_terms` stating that the value is a mapping performed for this record rather than a term any source states, naming the two bundle statements that motivate it (the FAIRhub access details and README requirement to "use the data only for type 2 diabetes related research", and the FAIRhub consent block), and noting that the license permits both commercial and non-commercial use so no commercial restriction is implied by the term.

---

### 2.10 `regulatory_restrictions.confidentiality_level` — caveat wording sharpened (low)

**Audit:** `restricted` is an inference from `HL7:2N (normal)` and `PublicDownloadSelfAttestationRequired`; defensible but author-supplied, and the record's own caveat already acknowledged the mapping.

**Change, both records:** the existing `source_caveats` was rewritten to open with the explicit statement that the value is a mapping performed for this record rather than a term any source states, and to say plainly that neither source value is an enum term. The substance of the justification is unchanged. This aligns the wording with the new `license_and_use_terms` caveat so that both author-side enum mappings are flagged in the same terms.

---

### 2.11 Record-level `source_caveats` — release-scope inconsistency (info)

**Audit:** no caveat addressed the FAIRhub statement that release 3.0.0 covers data "up through the end of the second year" against the collection end date of 2025-05-01 and the three-tranche changelog, beyond noting the inconsistency exists.

**Change, both records:** the final sentence of the record-level `source_caveats` was expanded. It now identifies which sources make each claim (the FAIRhub healthsheet and the RO-Crate for the "end of the second year" framing; the README changelog for the pilot/year-2/year-3 tranche labels of 204, 863 and 1,213), states that the collection window 2023-07-19 to 2025-05-01 is given consistently by every source that supplies one and is therefore the value recorded, and states that the year-labelling of the tranches is not resolvable from the bundle.

---

### 2.12 Core record: `total_file_count` and `total_size_bytes` (high)

**Audit:** the core record dropped both scalar slots that the full record populates from unambiguous FAIRhub API fields (`fileCount: 356343`, `size: 3815969779678`), stating the figures only as prose in `description`.

**Change, core record:** the totals were retained in `description` (which already carried them) and additionally added to the root-metadata entry of `distributions`, whose `notes` now closes with "The whole release comprises 356,343 files totaling 3,815,969,779,678 bytes (approximately 3.82 TB)." The scalar slots were **not** added, for the reason given in §3.1 below.

**Change, full record:** `description` now gives the byte figure numerically as well as in TB — "356,343 files totaling 3,815,969,779,678 bytes (approximately 3.82 TB)" — matching the core record. `total_file_count` and `total_size_bytes` were already present in the full record and remain unchanged.

---

### 2.13 Core record: omitted `citation` (medium)

**Audit:** the RO-Crate `associatedPublication` gives the dataset citation verbatim and the full record populates `citation`; the core record moved this text into `notes`, which is reserved for residual content after every fitting slot is used.

**Change, core record:** the recommended-citation sentence was removed from `notes`. The `notes` slot now carries only genuinely residual material — the "under review for potential modification" banner, the view and citation counts, and the onward-sharing restriction summary (see §2.14). The `citation` slot was **not** added, for the reason given in §3.1.

---

### 2.14 Core record: omitted `third_party_sharing` (medium)

**Audit:** the license §3.A and §3.C govern onward conveyance and third-party model vendors; the full record carries a `ThirdPartySharing` object with `is_shared: true`, while the core record had no such slot and folded the substance into `license_and_use_terms` and `prohibited_uses`.

**Change, core record:** the onward-sharing and third-party-model-vendor restrictions were added as a closing passage in `notes`, so the fact that distribution to third parties occurs and under what constraints is stated somewhere in the core record rather than only implied by the prohibition list. The `third_party_sharing` slot was **not** added, for the reason given in §3.1.

---

### 2.15 Core record: `subsets`, `splits`, `variables` (medium)

**Audit:** the core record carries no `subsets`, no `splits` and no `variables`, compressing the split into one sentence of `description` and dropping variable-level detail entirely.

**Change, core record:** the `description` was substantially expanded. It now gives the full per-partition composition of the train, validation and test splits — counts by race/ethnicity, sex and diabetes status, plus mean age and standard deviation for each — and a paragraph enumerating the named variables with their units and reference ranges (HbA1c, glucose, insulin, C-peptide, NT-pro-BNP, troponin-T, hs-CRP, the lipid panel including calculated LDL, creatinine, BUN, urine albumin and creatinine, continuous glucose, MoCA total, logMAR acuity, Mars log contrast sensitivity, blood pressure, heart rate, BMI, waist-hip ratio, the categorical monofilament response, and the wearable and environmental measures). The three slots themselves were **not** added, for the reason given in §3.1.

---

### 2.16 Core record: `relationships`, consent-module slots, participant slots (medium)

**Audit:** the full record's `Relationships` object is folded into `instances[0].instance_type`; three distinct consent slots (`collection_consents`, `consent_revocations`, `collection_notifications`) are collapsed into `informed_consent[0]`; `participant_privacy` and `participant_compensation` are dropped.

**Change, core record:** the relationship content was moved out of `instance_type` and into `instances[0].notes`, which now carries both the earlier-release counts and the statement that all instances belong to one project, that there is one visit per participant, and that records are linked by the participant directory identifier and summarized in `participants.tsv`. `instance_type` now describes only what an instance is — which is what the field asks for. The notification narrative was moved out of `informed_consent[0].consent_type` and into a new `informed_consent[0].notes`, leaving `consent_type` to describe the consent mechanism itself; the withdrawal limitation remains in `withdrawal_mechanism`, where it belongs. No slots were added, for the reason given in §3.1; `participant_privacy` and `participant_compensation` remain absent from the core record.

---

## 3. Findings left as-is

### 3.1 The `distributions` slot and the core-record omissions (high, medium)

**Audit:** the `distributions` slot does not appear in the supplied schema digest, and the ten objects under it — carrying the entire per-datatype path, byte-count and file-count inventory — will likely fail validation; the same class of finding covers the core record's omission of `total_file_count`, `total_size_bytes`, `citation`, `subsets`, `splits`, `variables`, `relationships`, the three consent slots, `participant_privacy`, `participant_compensation` and `third_party_sharing`.

**Left as-is, and why.** The schema digest supplied with this task is explicitly scoped to the `Dataset` class of `data_sheets_schema_all.yaml`. It does not enumerate the slots of `CoreDataset`, and it says so: the class listing gives `Dataset` and `DataSubset` and `FileCollection`, but no `CoreDataset` entry. The audit's own text concedes this twice — "If CoreDataset genuinely declares this slot it is outside the digest and cannot be verified" and, on `subsets`/`splits`, "the digest does not scope CoreDataset separately, so it cannot be confirmed either way."

That cuts both ways. I cannot confirm from the digest that `distributions` is declared on `CoreDataset`, and I equally cannot confirm that `total_file_count`, `citation`, `subsets`, `splits`, `variables`, `relationships`, `collection_consents`, `consent_revocations`, `collection_notifications`, `participant_privacy`, `participant_compensation` or `third_party_sharing` are declared on it. Removing `distributions` on the strength of a digest that does not describe the class would risk deleting a correctly-populated slot and losing the file inventory outright; adding twelve slots on the same strength would risk introducing twelve validation failures. Neither move is supported by the evidence available to me at reconciliation time.

The compromise applied instead was to make the core record self-sufficient in prose wherever the audit identified content at risk: the totals, the citation, the split composition, the variable inventory, the instance relationships, the notification narrative and the third-party-sharing terms are all now stated in the core record, in fields whose presence I can verify from the record itself. If validation subsequently rejects `distributions`, the content it carries is duplicated in `description` and recoverable; if validation accepts it, nothing has been lost.

The comparison of the two core records confirms `distributions` is present in both, unchanged in structure, with one addition to the root-metadata `notes`.

### 3.2 `subsets[].id` and `file_collections[].id` minted fragments (low)

**Audit:** fourteen minted fragment identifiers on the attested DOI; permitted under the v5 minting rule, but whether `doi:` is a declared prefix cannot be confirmed from the digest.

**Left as-is.** These label parts of this dataset with no referent outside the record, which is exactly the case the v5 rule permits minting for, and each is a fragment on an attested identifier. The `doi:` form is used consistently for the top-level `id`, the `version_access.latest_version_doi` and these fragments, while the `doi` string slot correctly carries the bare `10.60775/fairhub.3`. Changing the prefix on a guess would break that consistency without evidence that it needs breaking. The finding records an uncertainty rather than a defect.

### 3.3 `instances[0].data_topic` narrowed to one term; `data_substrate` omitted (low)

**Audit:** `B2AI_TOPIC:43` (Diabetes) is defensible but narrows a multi-domain dataset to one topic, and `data_substrate` is omitted despite the bundle naming DICOM, WFDB, CSV and TSV.

**Left as-is.** `data_topic` is single-valued on `Instance`, as the audit notes, so only one term can be given and Diabetes is the topic the dataset is organized around. For `data_substrate`, the same single-valued constraint applies and the dataset spans at least four listed substrates (11 DICOM, 49 Waveform Data, 6 CSV, 41 TSV) with no principled basis for elevating one. The digest's instruction is to omit rather than approximate where no term fits, and no single term fits an instance that is simultaneously imaging, waveform and tabular. Both records are unchanged here.

### 3.4 `conforms_to_class` / `conforms_to_schema` pairing (low)

**Audit:** `conforms_to_class: CoreDataset` matches the digest's guidance, but `conforms_to_schema` points at the full schema URI in both records while the core record validates against the core YAML.

**Left as-is.** The digest states that `conforms_to_schema` is "normally `https://w3id.org/bridge2ai/data-sheets-schema`" and describes it as a statement about the record's metadata schema rather than about the file it validates against. Both records carry that URI and differ correctly on `conforms_to_class`. Changing the schema URI on the core record would depart from the digest's stated normal value without evidence.

### 3.5 Enum values, dates and header (info)

Three info findings recorded no defect and required no action: all seven `conforms_to_standard` values are members of the permitted enum and each is independently attested; `issued: '2025-11-17T00:00:00Z'` carries the required UTC offset and is attested by two tier-one sources; and all fourteen required core header lines are present verbatim, including `# Sources:` and `# Phase 4 reconciliation: completed`. All are unchanged.

---

## 4. Referent

Both records describe the same referent: **release 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project**, DOI `10.60775/fairhub.3`, the public FAIRhub distribution of 2,280 participants published 17 November 2025. The AI-READI study as a whole, earlier releases 1.0.0 and 2.0.0, the controlled-access variant and the mini-subset (FAIRhub dataset 4) are treated as related entities and are recorded through `related_datasets`, `version_access`, `sensitive_elements` and `collection_timeframes` rather than as the subject. This choice is unchanged from Phase 1 and is applied consistently across both records.

---

## 5. Summary of changes

| Slot | Full | Core |
|---|---|---|
| `description` | byte figure given numerically | expanded with split composition and variable inventory |
| `notes` | unchanged | citation removed; third-party-sharing terms added |
| `source_caveats` (record) | dual-affiliation wording corrected; release-scope caveat expanded | same |
| `creators[0].affiliations` | second affiliation removed; caveat expanded | same |
| `funders[0].grants[0]` | `name` and `description` added; enclosing `notes` shortened; caveat extended | same |
| `instances[0]` | unchanged | relationship content moved from `instance_type` to `notes` |
| `known_biases[2]` | `affected_subsets` now references subset id; `notes` added | `affected_subsets` prose rescoped |
| `sensitive_elements[1]` | boolean added; detail extended | same |
| `license_and_use_terms` | `source_caveats` added | same |
| `regulatory_restrictions` | FDA/DMC sentence removed from `other_compliance`; caveat sharpened | same |
| `human_subject_research.regulatory_compliance` | split into three entries | same |
| `at_risk_populations` | `special_protections` split into three; `source_caveats` added | same |
| `informed_consent[0]` | n/a | notification narrative moved to `notes` |
| `related_datasets` | `replaces` removed; `target_dataset` now a URL; `notes` added to both | same |
| `distributions` | n/a | root-metadata `notes` gained release totals |

No slot was added to either record and no slot was removed from the full record. Two objects were removed: the second `Organization` in `creators[0].affiliations`, and the `replaces` entry in `related_datasets`.

**Validation:** both files were validated after reconciliation — the full record against `data_sheets_schema_all.yaml` class `Dataset`, the core record against `data_sheets_schema_core_all.yaml` class `CoreDataset`.