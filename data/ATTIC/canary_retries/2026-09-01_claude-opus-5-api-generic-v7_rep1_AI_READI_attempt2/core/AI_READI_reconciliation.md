# Phase 4 Reconciliation Report — AI_READI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-09-01_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d_core.yaml`

**Audit scope.** 30 findings were returned against the full record: 6 high, 11 medium, 13 low (one high finding — on `conforms_to_standard` — was withdrawn by the auditor on re-check and required no action). Because the core record is a projection of the full record, every change made to a projected slot was applied identically in both files.

---

## 1. Findings acted on

### 1.1 Identifier hygiene (high)

**`creators[0].affiliations[0].id` — website URL as an Organization identifier.**
The original carried `id: https://aireadi.org/` on the AI-READI Consortium affiliation. The bundle supplies no registry identifier for the Consortium; a project homepage is not an organization registry entry, and under the v5 identifier rule an identifier naming something outside this dataset must come from the evidence or be omitted. **Changed in both records:** the affiliation now carries only `name: AI-READI Consortium`, and the homepage URL is preserved in the entry's `notes` ("details of each member and their institutions are on the project website at https://aireadi.org"). It also remains in `external_resources`.

**`funders[0].grants[0].id` — session-scoped RePORTER search permalink as a Grant identifier; award number and title bundled into `name`.**
The original read `id: https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481` with `name: 'OT2OD032644: Bridge2AI: Salutogenesis Data Generation Project'`, while the two sibling grants carried bare award numbers and no id — an internally inconsistent shape. **Changed in both records:** the grant is now `name: OT2OD032644` with `description: 'Award title: Bridge2AI: Salutogenesis Data Generation Project.'`, and the id is dropped. The RePORTER links (both 10885481 and 10471118) are retained in the funder's `source_caveats` and in `external_resources`, where they are prose and locators rather than identifiers.

**`publisher` — homepage in a `uriorcurie` slot (low).**
The original had `publisher: https://fairhub.io/`. FAIRhub is named as publisher by the FAIRhub DataCite record and as "AI-READI Consortium" by the RO-Crate; neither source supplies a registry identifier for either, and both are tier 1 so the ranking does not decide. **Changed in both records:** the `publisher` slot is now absent. The publisher fact is retained in `notes`, in `distribution_formats[3].notes` ("distributed through the FAIRhub platform, which the FAIRhub DataCite record names as publisher"), and the disagreement is recorded as item (2) of `source_caveats`.

### 1.2 Entity conflation and misclassification (high)

**`creators[0].principal_investigator` — organizational creator carrying an individual.**
The original folded Aaron Lee into the AI-READI Consortium creator entry as its `principal_investigator`, conflating the sole DataCite organizational creator with a person and duplicating his role. **Changed in both records:** the Consortium entry now holds only `affiliations` and `notes`; Aaron Lee is his own Creator entry (the second in the list), with `principal_investigator: Aaron Lee`, his Washington University in St. Louis affiliation, and his ORCID and FAIRhub roles in `notes`. The list now runs one organizational creator plus sixteen named PIs.

**`creators[0].source_caveats` — list-level commentary on a per-object slot.**
The original placed commentary about the whole creators list ("The further creator entries below are…") in the first object's `source_caveats`. **Changed in both records:** that per-object `source_caveats` is gone; the descriptive content about the Consortium moved into the entry's own `notes`, and the statement about the composition of the list moved to the top-level `source_caveats` ("The creators list below records the single organizational creator named in the DataCite metadata followed by the sixteen individuals FAIRhub lists as Study Principal Investigators.").

**`funders[2]` — Microsoft AI for Good Lab recorded as a FundingMechanism.**
The bundle states only that the lab supported the cloud services needed for the project — in-kind support, not a grantor relationship, as the original entry's own `notes` conceded. **Changed in both records:** the third funder entry is removed; `funders` now has two entries (NIH, Research to Prevent Blindness). The Microsoft fact is retained in top-level `notes` and in the FAIRhub `collection_mechanisms` entry ("The Microsoft AI for Good Lab supported the cloud services needed for the project."). The second funder, Research to Prevent Blindness, gained a `notes` field naming its source.

### 1.3 Structural collapse in typed and multivalued fields (medium)

**`variables[*]` — reference ranges as prose where float slots are declared.**
The original carried two-sided numeric reference ranges in `notes` ("Reference range: 3.6-5.2") across roughly twenty laboratory variables while `minimum_value` and `maximum_value` sat empty. **Changed in the full record:** those slots are now populated wherever the bundle gives a numeric bound — two-sided ranges (potassium 3.6/5.2, sodium 135/145, platelets 150/450, MCV 79/97, C peptide, insulin, CRP-HS, glucose, BUN, calcium, chloride, CO2, total protein, albumin, bilirubin, AST, HbA1c, and the CBC panel) and one-sided bounds (total cholesterol `maximum_value: 200.0`, triglycerides 150.0, LDL 130.0, HDL `minimum_value: 39.0`, troponin-T `maximum_value: 16.0`). Where the bundle gives a sex- or age-stratified range with no single numeric interval — creatinine, alanine aminotransferase, alkaline phosphatase — the slots are left unset and the stratification is explained in `notes`. Troponin-T records the male upper bound in `maximum_value` and states in `notes` that the female bound is 11.
`variables` is not a slot in `CoreDataset`, so this change appears only in the full record.

**`variables[48].categories` — two labels in one string.**
The original had `categories: ['yes; no']`. **Changed in the full record:** now `categories: ['yes', 'no']` (two entries).

### 1.4 Inferred enum values (medium)

**`regulatory_restrictions.confidentiality_level` and `.hipaa_compliant`.**
Both were asserted (`restricted`, `compliant`) by inference from differently-coded source statements, as the original's own `source_caveats` conceded. **Changed in both records:** both slots are now absent. The underlying source statements are preserved in `regulatory_restrictions.other_compliance` (RO-Crate "HL7:2N (normal)"; FAIRhub `deIdentHIPAA: true` with a HIPAA identifiability check), and the `source_caveats` on that object now explains the omission rather than defending the inference. The RO-Crate confidentiality code also remains in `confidential_elements[0].confidentiality_details`.

**`at_risk_populations.at_risk_groups_included`.**
`false` was asserted from eligibility criteria while the same object's caveat stated the governing IRB questions were unanswered. **Changed in both records:** the boolean is now absent. The eligibility facts remain in `special_protections`, and the caveat now says the slot is left unset for want of a source statement.

### 1.5 Ranking inversion (medium)

**`license` — tier 2 title preferred over two tier 1 labels.**
The original stated `license: AI-READI Data License Agreement (Version 2.0)`, the licence document's own title (tier 2), over the FAIRhub landing page's "Health Data License" and the FAIRhub API's "AI-READI custom license v2.0" (both tier 1). **Changed in both records:** `license: Health Data License`. All three titles are now recorded together in `license_and_use_terms.license_terms` and in its `source_caveats`, and item (1) of the top-level `source_caveats` was rewritten to state which tier supplied the value.

### 1.6 Substantive content lost to omission (low)

**`extension_mechanism`.**
The bundle states plainly that "currently there is no mechanism for others to extend or augment the AI-READI dataset outside of those who are involved in the project" — a governance fact, not a bare absence. **Added to both records:** an `extension_mechanism` object with `extension_details` carrying that statement and noting that new instances arrive only through the project's own versioned releases.

**`discouraged_uses`.**
The healthsheet does answer the discouraged-use question (by reference to the licence restrictions), and the original recorded nothing. **Added to both records:** one `DiscouragedUse` entry recording what the healthsheet answers and explaining that the specific restrictions are carried in `prohibited_uses` because the licence states them as binding terms.

**`other_tasks`.**
The bundle's hypothesis-agnostic framing supports an entry beyond the originally planned tasks. **Added to both records:** one `OtherTask` entry, including the healthsheet's note that no formal guidelines exist for future researchers defining new tasks.

**`created_on`.**
The FAIRhub API supplies `created_at: 1763366400` (2025-11-17). **Added to both records:** `created_on: '2025-11-17T00:00:00Z'`.

**FAIRhub usage statistics and the mini-subset/parent status.**
The original recorded the mini subset in `notes` but not the view count, the zero citation count, or the null parent. **Changed in both records:** `notes` now states that the mini version has no DOI or identifier in the bundle, that the FAIRhub API records no parent, and that FAIRhub reports 24,636 views and 0 citations.

### 1.7 Duplication and annotation placement (medium/low)

**`instances[0].notes` — version-count history duplicated.**
The original repeated the 204 / 1,067 / 2,280 progression already carried in `version_access`. **Changed in both records:** that sentence is removed from `instances[0].notes`; the counts remain in `version_access.versions_available`.

**`instances[0]` — unannotated `data_substrate` omission.**
**Changed in both records:** a `source_caveats` was added explaining that a single Instance cannot carry a list of substrates, naming the substrates the bundle documents, and pointing to `file_collections` and `conforms_to` where they are recorded.

**`subpopulations[1].source_caveats` — mischaracterized as a cross-source tie.**
The two statements cited are both inside the FAIRhub record. **Changed in both records:** the caveat now says the conflict is internal to one source and explains the resolution (released files versus aggregate documentation).

**`collection_timeframes[0].source_caveats` — duplicated the top-level date caveat.**
**Changed in both records:** the per-object caveat is removed; the 18 vs 19 July discrepancy and the preference for the FAIRhub value remain as item (5) of the top-level `source_caveats`.

**`file_collections[*].conforms_to` — nine per-collection restatements of the top-level mapping.**
**Changed in both records:** the per-collection `conforms_to` prose strings are removed; each collection retains its `conforms_to_standard` term list, and the full mapping stays in the top-level `conforms_to`. In the core record this affects the `distributions` entries, which likewise lost their `conforms_to` strings and kept `conforms_to_standard`.

**`external_resources[*].external_resources` — "Label: URL" concatenations.**
**Changed in both records:** each entry now carries the bare URL in the multivalued `external_resources` field, with the human label moved into `notes`.

**`data_governance.committee_contact` — object in a scalar-ranged position.**
The original nested `{id, name}`. **Changed in both records:** `committee_contact: Aaron Lee`, with a new `data_governance.notes` recording his ORCID.

**Creator ORCIDs.**
With `principal_investigator` now a scalar name, each creator entry records its ORCID in `notes`.

**`distribution_dates[0].release_dates`.**
**Changed in both records:** now a list containing the release-date statement, matching the multivalued declaration.

---

## 2. Findings left as-is

**`conforms_to_standard` (high, withdrawn).** `CDS` is a permitted `DataStandardEnum` value; the auditor withdrew the finding on re-check. Unchanged in both records.

**`download_url` (low).** Still absent from both records. Access is gated behind login and licence acceptance, so no direct download URL exists; the access route remains in `distribution_formats[0].access_urls` and in `data_governance.access_review_process`. The auditor's own note asked only that the placement be confirmed deliberate — it is.

**`created_by` (low).** Still `AI-READI Consortium` in both records. Duplicative of the creator affiliation, but the slot is declared and the value is correct; no change made.

**`was_derived_from` (low).** Still absent. The version lineage is fully captured by the two `is_new_version_of` entries in `related_datasets`, which is the typed representation the schema provides.

**`existing_uses`, `use_repository`, `errata`, `data_protection_impacts`, `imputation_protocols`, `annotation_analyses`, `labeling_strategies`, `machine_annotation_tools` (low).** All still absent from both records. Each responds to an explicit "No" or "N/A" in the healthsheet, and populating a slot with an absence is the defect the rules warn against. Two related improvements were made rather than reversing the omissions: the FAIRhub view and citation counts are now in `notes`, and the pattern of three empty healthsheet responses (erratum; de-identification measures; de-identification preprocessing) is now disclosed in the top-level `source_caveats` and, for the two de-identification questions, in `is_deidentified.source_caveats`.

**`parent_datasets` and `resources` (low).** Still absent. `DatasetRelationship` requires `target_dataset`, and the bundle gives the mini subset no DOI or identifier, so no relationship object is constructible. The mini subset, and the FAIRhub API's null parent, are now stated in `notes`.

**`keywords` (low).** Unchanged — the merged list of FAIRhub dataset keywords and study-description keywords is retained in both records. Every term is attested in the bundle at tier 1; the merge is a union of two supported lists rather than a conflict, and no source is misrepresented by it.

---

## 3. Validation

Both files were validated after reconciliation:

- Full record against `data_sheets_schema_all.yaml`, class `Dataset` — passed.
- Core record against `data_sheets_schema_core_all.yaml`, class `CoreDataset` — passed.

The core header now carries `# Phase 4 reconciliation: completed`.

## 4. Referent

Unchanged: the record describes **version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project**, DOI `10.60775/fairhub.3`, as published on FAIRhub — not the AI-READI study as a whole, not the controlled-access counterpart, and not the version-agnostic dataset family. Prior versions appear only as `related_datasets` entries.