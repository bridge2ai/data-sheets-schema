# Reconciliation Report — AI_READI

Version label: `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
Records: full (`Dataset`) and core (`CoreDataset`)
Phase 3 audit findings: 23 (0 high, 4 medium, 15 low, 4 info)

---

## 1. Audit summary

The Phase 3 audit found **no fabricated dataset facts**. Participant counts, per-directory file counts and byte totals, split tables, laboratory reference ranges, device inventories, dates, DOIs, and all ROR/ORCID local parts were traced to the declared bundle and were internally consistent.

The findings fell into four groups:

1. **Declared-rule violations** (4 medium): a core-only assertion absent from the full record; an acronym expansion taken from a lower-ranked source; a source-ranking caveat that misstated the ranking; and a collapsed multivalued slot.
2. **Slot-placement and shape defects** (low): content in the wrong field, categories collapsed into one string, prose in a reference-valued slot, a documentation URL used as a data access point, an identifier reused across two nodes.
3. **Supported omissions** (low): two healthsheet answers and one dataset relationship that the records did not carry in their declared slots.
4. **Interpretation flags and conformance questions** (low/info): two enum values that are the record's own mapping rather than transcribed text, and four items that cannot be settled from the supplied `Dataset` digest.

---

## 2. Changes made

### 2.1 Medium findings

**`sampling_strategies[0].is_sample` — removed from the core record.**
The core record asserted `is_sample: true`. This value appears nowhere in the full record, and it contradicts prose present in both records ("all enrolled participants for the covered period are included rather than a further sample of them") and the tier-1 healthsheet ("The dataset contains all possible instances"). Comparing the two core versions, the line is present in the original and absent in the reconciled record; `is_random: false` and `is_representative: false` are retained in both, as they are carried from the full record and supported.

**Acronym expansion — `Exploratory` substituted for `Equitable` in both records.**
The `description` slot in both records read "Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights". That expansion appears only in the tier-3 BMJ Open protocol and Nature Metabolism comment. The tier-1 FAIRhub study description gives "AI Ready and Exploratory Atlas for Diabetes Insights", and the tier-1 README and tier-2 healthsheet give "Artificial Intelligence Ready and Exploratory Atlas for Diabetes Insights". The declared ranking requires the higher-ranked value. Both reconciled records now read "Exploratory", and a new numbered item (5) was added to `source_caveats` in both records recording the conflict, both readings, and the basis for the choice. The BMJ Open title quoted under `external_resources` retains "Equitable" in both versions, since that is a quoted publication title.

**IRB naming caveat — ranking rule correctly applied in both records.**
The original caveat under `ethical_reviews[0]` stated "Both are tier-1 or supporting sources and the ranking does not settle the discrepancy" and then recorded `reviewing_organization: University of Washington Institutional Review Board`. This misstated the declared ranking: the RO-Crate is tier 1, the healthsheet/documentation tier 2, and BMJ Open tier 3, so the ranking does settle it. In the reconciled records, `reviewing_organization` reads `Washington University IRB`, the caveat states the tiers correctly and identifies the preferred source, and it notes that the RO-Crate's own address, contact and protocol number support the lower-ranked reading. `human_subject_research.ethics_review_board` was rewritten in both records to lead with the preferred value and record both namings. The postal address and IRB Reliance Team contact from the RO-Crate were added to `review_details` in both records. A new caveat item (4) in the top-level `source_caveats` cross-references this.

**`funders` — expanded from one object to six in both records.**
The original emitted a single `FundingMechanism` for OT2OD032644, with P30DK035816, UL1TR003096, Research to Prevent Blindness, the Microsoft AI for Good Lab, and the device manufacturers described in `notes` prose. The reconciled records emit six objects: three NIH grants (each with its own `grants` entry), Research to Prevent Blindness, the Microsoft AI for Good Lab, and a combined device-manufacturer object listing the seven companies named in the Nature Metabolism acknowledgements. The in-kind entries are flagged as such in their `notes`.

**`funders[0].grants[0].name` — award number separated from award title.**
The original merged them as `"OT2OD032644: Bridge2AI: Salutogenesis Data Generation Project"`. The reconciled `name` is `"Bridge2AI: Salutogenesis Data Generation Project"`, with the award number OT2OD032644 stated in the object's `notes`. The `Grant` class is not in the supplied digest's required-keys listing, so a dedicated award-number field could not be confirmed; the number was moved to `notes` rather than invented as a key.

### 2.2 Low findings — placement and shape

**`distribution_formats` — access route removed from `format`.**
The original fifth entry had `format: "FAIRhub portal with Azure Storage access"`, an access route rather than a format. In the reconciled full record that entry carries no `format`; the access conditions moved into `data_governance.access_review_process` (which now names the access URL) and `license_and_use_terms.notes`, and the remaining text in the entry's `notes` covers software availability and Azure Storage. Two additional format entries were added in both records — TSV (for `participants.tsv` and the per-directory `manifest.tsv` files) and WFDB (for the ECG waveform files) — which the original omitted. The duplicate `https://fairhub.io/datasets/3/access` URL was removed from the DICOM entry's `access_urls` in both records.

**`variables[monofilament_test_response].categories` — split into two items.**
The original had a single list item `"yes; no"`. The reconciled full record emits `"yes"` and `"no"` as separate category values.

**`known_biases[2].affected_subsets` — prose replaced with subset references.**
The original value was the sentence `"All splits and all modalities."`. In both reconciled records, `affected_subsets` lists the three minted split identifiers (`#split-train`, `#split-validation`, `#split-test`), and the explanatory sentence moved to the object's `notes`.

**`raw_sources[0].access_url` — removed.**
The original set `access_url: https://docs.aireadi.org` on an object whose own text states the raw data are not shared. The reconciled full record omits `access_url`; `raw_data_details` now states explicitly that no access point is offered and that the documentation describes the processing.

**`creators[0]` — duplicated identifier resolved.**
The original used `https://aireadi.org` as both the `Creator` node's `id` and the `id` of its first affiliation (`AI-READI Consortium`), giving two nodes one identity. In both reconciled records the affiliations list begins with Washington University in St. Louis; the Consortium's name and its project URL are stated in the object's `notes`. The `Creator` `id` remains `https://aireadi.org`.

**`external_resources` — RO-Crate entry added, documentation URL relocated.**
Both reconciled records add an `ExternalResource` describing the RO-Crate metadata (RO-Crate 1.2-DRAFT, FAIRscape profile 0.1, nine subcrates), with a `notes` field recording that it is a separate description of the release rather than a file inside the distributed dataset. In the first entry, the documentation URL moved from `future_guarantees` into the resource description.

**`ip_restrictions.restrictions` — split into two items.**
The original held title/ownership and the publication limit in a single list entry. The reconciled records emit them as two.

**`human_subject_research.regulatory_compliance` and `at_risk_populations.special_protections` — split into multiple items.**
Each was a single list entry combining several distinct statements; the reconciled records emit five and three items respectively.

**`data_governance.stewardship_roles` — split into three items.**
The original combined maintenance, hosting, the RO-Crate committee naming, and Washington University's roles in one entry. The reconciled records emit three items and move the RO-Crate/Data-Access-Committee observation into `data_governance.notes`.

**`version_access.versions_available` — split into three items, one per version.**

**Reference ranges added as `minimum_value` / `maximum_value`.**
For five laboratory variables with two-sided reference ranges (HbA1c, glucose, insulin, C-peptide, hs-CRP), the reconciled full record populates `minimum_value` and `maximum_value`, with each `notes` field stating that these are the laboratory reference range and not observed data limits. One-sided ranges (cholesterol, triglycerides, HDL, LDL) and sex-stratified ranges (creatinine, troponin-T) were left in `notes` only, since a single min/max pair cannot represent them.

### 2.3 Low findings — supported omissions now populated

**`extension_mechanism`** added to both records, carrying the healthsheet answer that no mechanism exists for outside contributors.

**`data_protection_impacts`** added to both records, carrying the healthsheet answer that no DPIA has been conducted.

**`related_datasets`** gains a third entry in both records: an `is_source_of` relationship to `https://fairhub.io/datasets/4`, the mini-subset the FAIRhub API records as `"child": 4`. The corresponding prose was removed from the full record's `notes`.

### 2.4 Low findings — keywords and citation

**`keywords`** — `Salutogenesis` replaced with `Exploratory Data Collection` in both records. The former appears in no source keyword list; the latter is in the FAIRhub study `keywordList`.

**Core `notes`** — the recommended citation now opens the field rather than trailing it, and is labelled as the recommended citation. It remains in `notes` because `citation` could not be confirmed as a declared `CoreDataset` slot (see §3).

### 2.5 Low finding — internal inconsistency

**Device count corrected.**
`acquisition_methods[0].acquisition_details` said "retinal imaging on six devices" while `collection_mechanisms` listed seven. Both records now say seven in the acquisition entry, and the mechanisms entry states "seven in total" explicitly.

### 2.6 Low finding — unrecorded source conflict

**Study base encounter window.**
The original `sampling_strategies[0].strategies` asserted the BMJ Open (tier 3) window "between 2020 and 2025" without noting that the healthsheet and IRB protocol (both tier 2) say "within the past 2 years". In both reconciled records the specific window is dropped from `strategies`, the conflict is recorded in that object's `source_caveats` as the first of two conflicts, and a new item (6) in the top-level `source_caveats` cross-references it.

### 2.7 Core `distributions` — format consistency

The `environment` entry now carries `format: CSV` and `media_type: text/csv`, matching the record's own statement in `distribution_formats` that CSV is used for environmental sensor data. The four DICOM directories carry `conforms_to_standard: DICOM` and now state the media type `application/dicom` in `notes`; a `format` key was not added to them, since `format` is not a key the supplied digest declares for `distributions`.

### 2.8 Core `distributions` — split detail consolidated

The three split subsets that the full record carries as `DataSubset` objects have no `subsets` counterpart in the core record. The original core folded only the 70/15/15 headline into the root-metadata entry's `notes`; the reconciled core carries the full per-partition composition figures there, so the split table survives the projection.

---

## 3. Findings left as-is

**`conforms_to_standard: RO_CRATE` — removed rather than retained, but note the scope.**
The audit flagged this as an interpretation issue. Both reconciled records drop `RO_CRATE` from `conforms_to_standard` and remove the RO-Crate sentence from `conforms_to`, on the audit's reasoning that `ro-crate-metadata.json` is not among the nine root metadata files the README lists. The RO-Crate is instead recorded as an `external_resources` entry. This is a change, not a retention; it is listed here because the audit item was framed as a question about interpretation rather than a defect.

**`regulatory_restrictions.confidentiality_level: restricted` — retained.**
No source states a value from this slot's enumeration. `HL7:2N (normal)` has no enum counterpart, so either the slot is omitted or a mapping is made. The value is retained; the `notes` field was rewritten in both records to open with "No source states a value from this slot's enumeration" and to identify the value explicitly as this record's own mapping. A new item (12) in the full record's `source_caveats` flags both this and the `conforms_to_standard` terms as record-level interpretations.

**`data_governance.committee_name` — changed to the tier-1 value.**
The original coinage `AI-READI Data Access Committee` was replaced with `AI-READI Consortium`, the value the tier-1 RO-Crate states. The Data Access Committee, which the tier-3 BMJ Open protocol names, is now recorded in `access_review_process`, `stewardship_roles`, and `data_governance.notes` as a distinct body. Listed here because it is the one finding where the fix required choosing between two attested names rather than correcting a defect.

**Multivalued-versus-scalar conformance items (info).**
The audit flagged `at_risk_populations.special_protections`, `human_subject_research.irb_approval` / `regulatory_compliance` / `special_populations`, `ip_restrictions.restrictions`, `data_governance.stewardship_roles`, `version_access.versions_available`, and `external_resources[*].restrictions` as emitted in list form where the supplied digest does not declare multivalency. All remain lists in both reconciled records. The digest states these are "also accepts" keys without declaring their range or cardinality, so no basis exists in the supplied material for converting them to scalars; validation against the full schema is the correct arbiter. Where a list was retained, it was split into one item per distinct statement (§2.2) so that if the slot is multivalued the entries are correct, and if scalar the failure is visible rather than hidden inside a run-on string.

**`distributions` slot and its keys (info).**
`distributions`, `path`, `bytes`, `format`, and `media_type` do not appear in the supplied `Dataset` digest. They are retained in the core record because the core schema was not supplied and cannot be checked; the same limitation applies to whether `CoreDataset` declares `citation`, `total_file_count`, and `total_size_bytes`. The citation was therefore left in core `notes` rather than moved to a `citation` slot that may not exist, and the two size slots remain populated in the full record and absent from the core.

**ROR/ORCID CURIE usage (info).**
`ROR:` and `ORCID:` CURIEs in `uriorcurie` slots are retained unchanged in both records. All local parts are evidence-backed. The supplied digest declares only `B2AI_SUBSTRATE` and `B2AI_TOPIC` prefixes, so prefix declaration cannot be verified from it; the v5 rule directs CURIE form where a prefix is declared, and validation will surface any undeclared prefix.

**Target-enrollment discrepancy (4,000 vs 4,600).**
Neither figure is asserted in either record, which describes the 2,280 participants actually released. The caveat text was tightened to say so explicitly. No change of substance.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Findings addressed by a change | 18 | 17 |
| Findings retained with rationale | 5 | 5 |
| Fabricated facts found | 0 | 0 |
| Fabricated facts introduced | 0 | 0 |

Both records name the same referent throughout: version 3.0.0 of the AI-READI flagship dataset, `doi:10.60775/fairhub.3`. The core record remains a projection of the full record; where a full-record slot has no core counterpart (the variable inventory, the split subsets as separate objects, third-party sharing, direct collection, collection consents and notifications, consent revocations, participant privacy, participant compensation), the content is folded into the nearest declared core slot or omitted, and the core `source_caveats` records which.