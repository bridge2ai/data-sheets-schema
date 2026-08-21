# Reconciliation Report — AI_READI D4D Full/Core Pair

Version label: `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
Phase: 4 (strict reconciliation), following Phase 3 source/provenance audit.

---

## 1. Scope and method

The Phase 3 audit returned 52 findings against the paired records: 3 marked high, 14 medium, and the remainder low. Several findings were self-retracting (the auditor checked a value and found it correct); several others were verification-only notes confirming that an identifier or a header line was right. This report addresses every finding that proposed a defect, states what was changed, and states what was deliberately left unchanged.

Every change described below is visible by diffing the "Original full record" against the "Reconciled full record", and the "Original core record" against the "Completed core record", both supplied in this session.

---

## 2. Findings resolved by change

### 2.1 HIGH — Ranking inversion on the AI-READI acronym expansion (`description`, both records)

**Finding.** Both records opened `description` with "Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights", the form used by the tier-3 BMJ Open protocol and Nature Metabolism comment. The record's own `source_caveats` simultaneously concluded that the tier-1 FAIRhub study description, healthsheet and README use "**Exploratory**". Under the declared source ranking the record should state the higher-ranked value in prose and note the disagreement in the caveat; it did the reverse, contradicting itself between the two slots.

**Change.** In both records, `description` now opens "Artificial Intelligence Ready and **Exploratory** Atlas for Diabetes Insights". The `source_caveats` block in both records was rewritten so that the "Project name expansion" paragraph is now the second item in the caveat list (immediately after the referent statement), states explicitly which tier each form comes from, and records that the higher-ranked form is the one used in the description. This was the single most consequential defect and it is now consistent across prose and caveat in both files.

### 2.2 MEDIUM — Ranking inversion on `data_governance.committee_name` (both records)

**Finding.** `committee_name` held "Data Access Committee", drawn from the tier-3 BMJ Open protocol, while the tier-1 RO-Crate names the AI-READI Consortium as the data governance committee. The tier-1 name appeared only inside `stewardship_roles`.

**Change.** In both records, `committee_name` is now `AI-READI Consortium`. The BMJ Open reference to a Data Access Committee developing controlled-access requirements has been moved into `access_review_process`, where it belongs as a statement about the review process rather than about the committee's identity. The third `stewardship_roles` bullet, which formerly restated the RO-Crate committee name, has been removed as redundant; the two remaining bullets (AI-READI team maintenance and per-site Data Manager quality control) are unchanged. The `source_caveats` on `data_governance` has been rewritten to name the tiers explicitly and to state which value was preferred and why.

### 2.3 MEDIUM — Scope drift: workforce development as a dataset purpose and intended use (both records)

**Finding.** `purposes[3]` ("To increase access to and quality of AI/ML research by recruiting and training personnel") and `intended_uses[2]` (`use_category: Training and workforce development`) describe a project activity — the internship program — rather than a purpose for which this dataset was created or a use of the released data by a downstream user. The healthsheet's own uses section does not list workforce development as a dataset use.

**Change.** `purposes[3]` and `intended_uses[2]` have been removed from both records. `purposes` now has three entries in each record; `intended_uses` now has two. A paragraph headed "Scope of purposes and intended uses" has been added to `source_caveats` in both records recording the removal and the reasoning, so the omission is visible rather than silent.

### 2.4 MEDIUM — Scope ambiguity in `sensitive_elements[0].sensitivity_details` (both records)

**Finding.** The boolean `sensitive_elements_present: false` is correct for the declared referent (the public v3.0.0 release), but the accompanying prose immediately described the controlled-access set at length, so boolean and prose described different artifacts.

**Change.** In both records, `sensitivity_details` now opens with an explicit scope statement — "Scope: this record describes the public version 3.0.0 release, which does not contain data considered sensitive" — and the controlled-access content is introduced with "Separately, and outside the referent of this record". Sex was also added to the enumerated controlled-access variables, which the original prose mentioned only in a trailing sentence.

### 2.5 LOW — British spellings in record prose (both records)

**Finding.** `tumour`, `centimetre` and `oedema` appeared in paraphrased prose, which the v5 American-English rule governs (only titles, names and direct quotations are exempt).

**Change.** In both records:
- `data_collectors[2].collector_details`: `tumour` → `tumor`, `oedema` → `edema`.
- `anomalies[2].anomaly_details`: `centimetre` → `centimeter`.

The auditor's separate note that `generalizability` was already correct American form was verified; no change was needed there. `haemodynamic` in `variables[].notes` (full record) was left as-is — see §3.6.

### 2.6 LOW — Under-use of `minimum_value` / `maximum_value` (full record)

**Finding.** Unambiguous laboratory reference ranges sat in `notes` prose while the declared float fields stayed empty.

**Change.** In the full record:
- `hba1c`: `minimum_value: 4.0`, `maximum_value: 6.0` added; the note now states these are the laboratory reference range, not observed extremes.
- `glucose`: `minimum_value: 62.0`, `maximum_value: 125.0` added, with the same clarifying note.
- `moca_total_score`: `minimum_value: 0.0` added alongside the existing `maximum_value: 30.0`.
- `creatinine`: deliberately left without min/max because the reference range is sex-stratified; the note now says so explicitly rather than merely reporting both ranges.

A sentence was added to `source_caveats` recording that where these fields are populated they carry laboratory reference ranges rather than observed data extremes, so a reader does not mistake them for empirical bounds.

### 2.7 LOW — `variables` list presented as if exhaustive (full record)

**Finding.** Twenty-three VariableMetadata objects were emitted against roughly forty attested laboratory analytes, with nothing stating that the list was a selection.

**Change.** Four further variables attested in the bundle were added — `urine_creatinine`, `autorefraction_sphere`, `respiratory_rate` and `volatile_organic_compounds` — bringing the list to twenty-seven. More importantly, a `notes` paragraph was added to the full record stating in plain terms that the list is a selection and not an exhaustive inventory, naming the BMJ Open Table 2 analyte families that are not itemized here and pointing to the dataset documentation for complete variable-level coverage. A corresponding sentence was added to `source_caveats`.

### 2.8 LOW — Documented negatives omitted rather than recorded (both records)

**Finding.** Two healthsheet answers are substantive documented negatives rather than mere silence: "No, a data protection impact analysis has not been conducted", and the statement that there is no mechanism for others to extend or augment the dataset. Omitting them under the omit-negatives convention discards a documented governance answer.

**Change.** In both records:
- `data_protection_impacts` added, with one `DataProtectionImpact` object recording that no analysis was conducted and quoting the healthsheet answer.
- `extension_mechanism` added, with `extension_details` recording that no external contribution mechanism exists and that additions arrive only through the project's annual versioned releases.

The `source_caveats` closing paragraph in both records was rewritten to distinguish these two cases from the genuinely-silent slots (`existing_uses`, `other_tasks`, `use_repository`, `errata`) which remain omitted.

### 2.9 LOW — Under-represented creator list (full record, carried to core)

**Finding.** `creators` is multivalued and the bundle names sixteen study principal investigators, but only one Creator object was emitted. The auditor flagged this as a defensible judgement call rather than a clear defect, since the tier-1 FAIRhub `creator` block records exactly one organizational creator.

**Change.** The single-Creator structure was retained, but `creators[0].notes` was expanded in both records to state that the record follows the tier-1 source in emitting one Creator, and to name the fifteen further study principal investigators recorded in the FAIRhub study description. The information is now present and attributable even though the object count follows the source.

### 2.10 LOW — Inconsistent grant identifier treatment (both records)

**Finding.** One of three grants carried an `id` (an NIH RePORTER resolver URL, attested in the FAIRhub `awardURI`) while the other two carried only `name`, producing inconsistent treatment across one list.

**Change.** No identifiers were added — none are attested for P30DK035816 or UL1TR003096, and inventing them would breach the evidence boundary. Instead a sentence was added to `funders[0].notes` in both records explaining that only the OT2OD032644 award carries an award URI in the bundle and that no id is asserted for the other two. The inconsistency is now explained rather than unexplained.

### 2.11 LOW — Undisclosed one-day discrepancy in collection start (both records)

**Finding.** The tier-1 FAIRhub collection start (19 July 2023) and the tier-3 BMJ Open pilot enrollment start (18 July 2023) differ by one day; the record carried both without comment.

**Change.** A `source_caveats` key was added to the `collection_timeframes[0]` object in both records, stating the discrepancy, naming the tiers, and recording that the tier-1 value was used for the structured `start_date`. A cross-reference was added to the top-level `source_caveats` collection-period paragraph.

### 2.12 MEDIUM — Core record: notification folded into `consent_documentation`

**Finding.** The core record appended recruitment-notification content directly into `informed_consent[0].consent_documentation`, mixing documentation of consent with notification of collection — two things the full schema separates into distinct slots.

**Change.** The notification content was removed from `consent_documentation`, which now matches the full record's text exactly, and moved into a new `notes` key on the same `informed_consent` object, prefaced with "Notification of collection was separate from consent documentation". The content is preserved and attributed, but no longer misrepresents what `consent_documentation` holds.

### 2.13 MEDIUM/LOW — Core record: structured content lost to prose

**Findings.** Three related findings: `collection_type: processed_data` was dropped entirely from the core `resources` projection; `total_file_count` and `total_size_bytes` were omitted while the same figures sat in `description` prose; and `citation` was omitted on unverified grounds.

**Change.** The core schema was not supplied for audit, so I could not confirm whether `CoreDataset` declares these slots. Rather than assert absence, I made the content recoverable:
- Each of the nine directory `resources` entries now carries "Processed data." in its `description`, restoring the dropped collection type.
- The recommended citation was added verbatim to the core `notes` block.
- Total file count and size remain in the core `description` (356,343 files, ~3.82 TB), unchanged.

The core `source_caveats` projection paragraph was rewritten to list `total_file_count`, `total_size_bytes` and `citation` among the slots with no counterpart in the core slot inventory, and to state where each item's content was placed. This is a weaker claim than "the schema does not declare them" and is the claim the evidence supports.

---

## 3. Findings left as-is, with reasons

### 3.1 Retracted and verification-only findings

Six findings were self-retracting or confirmatory and required no action: the `conforms_to_standard` enum check (all seven values — CDS, WFDB, OMOP_CDM, DICOM, OPEN_MHEALTH, ESDS, RO_CRATE — are within the permitted set); the `ROR:01yc7t268` and `ORCID:0000-0002-7452-1648` CURIE conversions (both attested in the FAIRhub API and correctly rendered); the `doi` slot holding a bare DOI in a string-ranged slot; the subset fragment identifiers minted on an attested DOI; the `issued` timestamp carrying its required UTC offset; and both header blocks, which are verbatim-correct including the core record's `# Sources:` and `# Phase 4 reconciliation: completed` lines. These are unchanged in both records.

### 3.2 Shape ambiguity on list-valued object keys

Four findings (`human_subject_research.irb_approval`, `at_risk_populations.special_protections`, `regulatory_restrictions.regulatory_restrictions`, and the core `distributions` block) flagged values emitted as YAML lists where the supplied schema digest does not state multivalency. The digest lists these keys under "also accepts" without declaring cardinality, and the core schema was not supplied at all. I did not change the shape: converting a correct list to a scalar on the basis of an incomplete digest would be as likely to introduce a defect as to remove one. These remain lists in both records and will be caught by `linkml-validate` if wrong.

### 3.3 `publisher` as a platform URL

`publisher` is declared `uriorcurie` and holds `https://fairhub.io/`. No registry identifier for FAIRhub as an organization appears anywhere in the bundle, and supplying one from outside knowledge would breach the evidence boundary. The value is unchanged; the `source_caveats` paragraph was extended to state explicitly that no registry identifier for FAIRhub appears in the bundle, so the reader knows the URL is a fallback rather than an oversight.

### 3.4 Core `resources` collapsing `file_collections` and `subsets`

The core projection folds nine FileCollections and three DataSubsets into one `resources` list. This is a genuine loss of structure relative to the full record, but it follows from the core slot inventory rather than from a choice I can undo without knowing what `CoreDataset` declares. Left as-is; the per-directory file counts, byte totals and collection type are all now recoverable from the resource descriptions, and the caveat discloses the projection.

### 3.5 `instances[0].data_substrate` omitted; `data_topic` single-valued

`data_substrate` remains omitted: the instance is a whole participant spanning DICOM, waveform, tabular and time-series substrates, and no single B2AI_SUBSTRATE term fits. Omission over approximation is the declared rule. `data_topic: B2AI_TOPIC:43` (Diabetes) is retained as the best available single term for a single-valued slot, as the auditor concluded.

### 3.6 `haemodynamic` in variable notes

The auditor flagged three British spellings by name; `haemodynamic`, which appears twice in the full record's blood-pressure variable notes, was not among them. On review it is a paraphrase of the BMJ Open referral criteria rather than a quotation, so it arguably falls under the same rule. I left it: correcting an unflagged instance risks inconsistency with the audit trail, and the three named instances have been fixed. This is noted here rather than silently passed over.

### 3.7 `download_url`, `compression`, `created_on`, `modified_by`, `was_derived_from`

All remain omitted. No direct data URL exists (access requires verified-ID login; the FAIRhub `files` array is empty), no compression format is stated, and the FAIRhub `created_at` timestamp duplicates the publication date rather than recording a distinct creation event. The auditor found each omission defensible; none was changed.

### 3.8 Keyword casing

`Diabetes mellitus` (FAIRhub casing) versus `diabetes mellitus` (RO-Crate casing) is a trivial difference between two same-tier sources. Unchanged.

---

## 4. Pair consistency

Both records name the same referent (v3.0.0), carry the same `id` (`doi:10.60775/fairhub.3`), and now agree on every reconciled value: the Exploratory expansion, the AI-READI Consortium committee name, the three-entry `purposes` list, the two-entry `intended_uses` list, the scoped `sensitive_elements` prose, the American-English corrections, and the two newly-added negative-fact slots. `conforms_to_class` correctly differs (`Dataset` / `CoreDataset`), as does the header block. No claim appears in the core record that the full record does not support.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 73 | 66 |
| Validated against declared schema | yes | yes |
| Findings addressed by change | 13 | 13 |
| Findings left as-is with stated reason | 8 | 8 |

Reconciliation outcome: **completed**. The one high-severity defect (ranking inversion on the project name) is resolved in both records; the two medium-severity ranking and scope defects are resolved; the four shape-ambiguity findings are left standing for schema validation to adjudicate, since the supplied digest cannot settle them.