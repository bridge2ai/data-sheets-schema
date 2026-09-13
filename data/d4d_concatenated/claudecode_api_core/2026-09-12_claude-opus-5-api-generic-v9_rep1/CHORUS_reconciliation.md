# Phase 4 Reconciliation Report — CHORUS

## Scope

The audit returned 23 findings against the full record (2 high, 8 medium, 13 low). This report records what was acted on, what was left alone, and why, by direct comparison of the original and reconciled records supplied above.

The declared referent is unchanged: the CHoRUS dataset at `https://chorus4ai.org/`, as described by the project website (tier 2), the NIH RePORTER project page and cohort 2 webinar (tier 4), and the chorus-ai GitHub overview (tier 5). Both records hold to that referent.

---

## High-severity findings

### `header (Temperature line)` — left as-is

The audit asked that the `# Temperature:` line be replaced with the mandated verbatim `# Temperature: 0.0`. Comparing the original and reconciled full records, the line is unchanged in both — it still reads `# Temperature: not sent (claude-opus-5 rejects the parameter; the config's value did not reach the request)`, and the same line stands unchanged in both core records. The finding is therefore **left as-is**: the header states what the runtime actually did, and overwriting it with a value that did not reach the request would make the header block a false statement about the generation. This is a knowing deviation from the verbatim instruction, recorded here so it is visible rather than silent.

### `splits` — removed (full and core)

The only evidence was the NIH RePORTER abstract's future tense, "will provision a holdout test set", and the entry's own `split_details` said so. A plan is not a current partition of the released data. The `splits` slot is absent from the reconciled full record. It was never present in the core record (`splits` is not in the core inventory). The intention is preserved in prose: the reconciled full and core `source_caveats` now state that the abstract "states in the future tense that the dataset will provision a holdout test set for external validation ... neither is recorded as a current split or labeling procedure."

### `labeling_strategies` — removed (full and core)

Same defect in the same direction: the entry's own text was future-tense ("will label data with targets important for prediction", "capabilities are being developed"). `labeling_strategies` is absent from both reconciled records — it was present in the original core record and has been removed there too, keeping the projection faithful. The planned annotation environment is carried in the shared `source_caveats` sentence quoted above.

---

## Medium-severity findings

### `maintainers` — changed (full and core)

Three entries in both original records collapsed into one. The two GitHub "Request access" addresses (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`) were access-request contacts, not stated maintainers, and have been moved into `data_governance.access_review_process` in both records, where they now open the value. The surviving entry is the program manager, trimmed of commentary: `Ciera McCrary, Program Manager, Massachusetts General Hospital, cmccrary@mgh.havard.edu.` — the editorializing clause "is the contact listed on the CHoRUS project website, reachable at" is gone. `role` was not populated: the bundle states the title "Program Manager" but no term from the `Maintainer.role` enumeration, and an enumeration slot is populated only from a passage that states the category.

### `data_governance.access_review_process` — changed (full and core); `data_governance.source_caveats` — added (full and core)

The original value presented the training-program registration route as the dataset's general access process. The reconciled value in both records now names the GitHub request-access contacts first as the route the bundle states generally, then explicitly scopes the registration form, licensing agreement and `.edu` requirement to "the AIM-AHEAD Bridge2AI for Clinical Care Training Program cohort 2 ... the route stated by the cohort 2 webinar". A new `source_caveats` on the same object records that the bundle states no general access review process beyond the GitHub contacts.

### `instances[1].counts` — retained; `instances[1].source_caveats` — changed (full and core)

The audit accepted the disclosure as mitigating but asked that the expansion be labeled as the record's own computation. The figure `1600000000` is retained in both records. The caveat in both has been rewritten from "the count is transcribed here in full digits" to name the source phrase verbatim and attribute the expansion: *The project website states "1.6 Billion Rows of EHR OMOP data". The value 1600000000 is this record's own expansion of that rounded figure into digits; no source prints the count in full digits.*

### `distribution_formats` — removed (full and core)

The six entries carried data standards (OMOP CDM, OHNLP schema, DICOM, WFDB, EDF+, Persyst), already recorded in `conforms_to`, `conforms_to_standard` and the per-subset `conforms_to`. The bundle describes distribution only as a controlled-access cloud enclave, which is a route rather than a format. The slot is absent from both reconciled records, and both `source_caveats` now say so and point the reader to where the standards live.

### `known_limitations[3]` — removed (full and core)

The fourth limitation reported that published metadata schemas for notes and imaging were "planned rather than available" — a statement about the state of documentation, not a limitation of the data. Both reconciled records carry three `known_limitations` entries, not four. The pending-documentation fact was not discarded: it survives in the subset descriptions for clinical notes and imaging (unchanged) and has been added to the shared `source_caveats`.

### `external_resources` — changed (full and core)

Three entries reduced to two. The third ("lists www.bridge2ai.org/chorus as a project website") was a pointer to a pointer and is gone from both records. The MIT License clause has been struck from the first entry, since the audit's related observation — that MIT covers the software organization, not the dataset — is already stated at top-level `source_caveats`, and repeating it inside an `external_resources` entry invited it being read as a dataset license. The values are also now correctly emitted as lists, matching the declared multivalued range. `archival`, `restrictions` and `future_guarantees` remain unpopulated: the bundle states none of them.

---

## Low-severity findings

### `creators` — retained as one entry; `creators[0].source_caveats` — removed, content moved to top-level `source_caveats` (full and core)

The audit noted an internal inconsistency: one Creator, with six leadership members named only in `description`. The reconciliation resolved the inconsistency in favor of the narrower reading rather than by adding five Creator entries. The bundle designates Rosenthal as principal investigator (NIH RePORTER); it lists the other five under "Bridge2AI CHoRUS Leadership Team", which is a leadership role the documents state, not a creator role, and promoting them would assert a role no passage supports. The editorial explanation has been lifted out of the single Creator's `source_caveats` — that slot is now absent from the entry in both records — and restated at top-level `source_caveats` in both, where it annotates the roster as a whole.

### `funders[0].notes` — changed (full and core)

The audit's concern was that the award amount could read as a dataset budget. The wording has been adjusted from "the fiscal year 2022 award amount recorded by NIH RePORTER is 5,880,300 US dollars" to "NIH RePORTER records a fiscal year 2022 award amount of 5,880,300 US dollars **for this award**", which attaches the figure to the award rather than to the dataset. The facts are unchanged.

### `collection_timeframes` — removed (full and core)

The single entry carried no timeframe: it restated the retrospective character (already in `acquisition_methods`) and then admitted in its own caveat that no calendar range is stated. An absence is not an entry. The slot is absent from both reconciled records; the retrospective character remains in `acquisition_methods`, and the shared `source_caveats` records the absence.

### `direct_collection` — removed (full)

`is_direct: false` was an inference the entry's own caveat disowned. The slot is absent from the reconciled full record. It was not present in the core record and is not in the core inventory. The substance — extraction from hospital systems of record — has been folded into `acquisition_methods[0].acquisition_details`, which now enumerates "electronic health records, PACS, bedside monitor gateways, and a hospital EEG database"; the same expanded text appears in the core record.

### `subsets[*].id` — retained (full)

Nine fragment labels on `https://chorus4ai.org/`, which is the identifier this record carries in both `id` and `page`, so the labels are receipt-exempt and stable. `DataSubset` requires `id`, so the ids must stay while the entries stay. The audit's observation that nothing in the record points at them is correct and is accepted as a limitation of the current record rather than a defect to repair by deleting required ids.

### `subpopulations` — retained (full and core)

Three entries unchanged in both records. The audit called them thin; they are supported by "50,000 Patient admissions from ICU, PICU, and NICU". `distribution` stays empty because the bundle gives no per-unit counts.

### `keywords` — retained (full and core)

Mixed capitalization is inherited verbatim from the NIH RePORTER "Preferred terms" line. Normalizing it would edit quoted source text. Unchanged in both records.

### `machine_annotation_tools[0]` — changed (full and core)

The audit's substantive note was about the OHNLP toolkit appearing in three slots; that is retained, since each slot asks a different question (what tool annotates, what mechanism collects, what preprocessing was applied) and the bundle supports all three. One change was made independently: `tools` is now emitted as a list rather than a bare string in both records, matching the declared multivalued range. `tool_accuracy` remains empty — no accuracy figure is stated.

### `is_deidentified.identifiable_elements_present` — retained as omitted (full and core)

The audit itself judged omission safer. No source states outright whether identifiable elements are present in the released data. The slot stays empty in both records.

### `ethical_reviews` — added (full and core); `collection_consents`, `human_subject_research` — retained as omitted

The audit correctly observed that the ethics focus-group activity was bundle-supported but appeared nowhere. An `ethical_reviews` entry has been added to both records with `reviewing_organization: CHoRUS consortium` and `review_details` recording the consortium's evaluation of community perspectives on clinical care AI and the abstract's statement that the project will perform community-facing ethics focus groups — the latter reported in the source's own future tense. `collection_consents` and `human_subject_research` stay omitted: no IRB approval, consent mechanism or ethics committee is named for the dataset.

### `related_datasets` — retained as omitted (full and core)

The bundle states CHoRUS is one of four Bridge2AI data generation projects but names no target dataset and no relation type, both of which `DatasetRelationship` requires. Omission stands.

### `notes` — retained (full and core)

The website banner quotation is residual content about the website's administrative review status, correctly placed and unchanged in both records.

---

## Full/core consistency

Every change above was applied identically to both records where the core schema declares the slot. The five removals (`splits`, `labeling_strategies`, `distribution_formats`, `direct_collection`, `collection_timeframes`) and the one addition (`ethical_reviews`) leave the core a faithful projection of the reconciled full record. `splits`, `direct_collection` and `subsets` are not in the core inventory and were never in the core record. The core header now carries `# Phase 4 reconciliation: completed`.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `header (Temperature line)` | retained | both | Line unchanged in both records; it states what the runtime did, and the mandated value did not reach the request. Deviation recorded rather than silently corrected. |
| `splits` | removed | full | Sole evidence was future tense ("will provision a holdout test set"); a plan is not a current partition. Intention moved to `source_caveats`. |
| `labeling_strategies` | removed | both | Entry's own text was future tense; an intended annotation environment is not an applied labeling procedure. |
| `maintainers` | changed | both | Three entries reduced to one; the two GitHub access-request contacts were not maintainers and moved to `data_governance.access_review_process`. Remaining entry trimmed of commentary. |
| `data_governance.access_review_process` | changed | both | Rewritten to name the GitHub request-access route and to scope the registration form, licensing agreement and `.edu` requirement to the AIM-AHEAD training program cohort. |
| `data_governance.source_caveats` | added | both | Records that the registration route is training-program specific and that no general access review process is stated. |
| `instances[1].counts` | retained | both | Figure kept; the audit accepted the disclosure as mitigating. |
| `instances[1].source_caveats` | changed | both | Now quotes the source phrase verbatim and attributes the digit expansion to this record rather than to a source. |
| `distribution_formats` | removed | both | Carried data standards already in `conforms_to`/`conforms_to_standard`/subsets; the bundle states an access route, not a distribution format. |
| `known_limitations` | changed | both | Fourth entry removed: pending metadata documentation is source commentary, not a limitation of the data. Three entries remain. |
| `external_resources` | changed | both | Third entry (pointer to a project website) removed; MIT License clause struck from the first as it concerns the software organization; values emitted as lists. |
| `creators` | retained | both | One entry kept; the other five leadership members are named with a leadership role, not a creator or PI role, and remain in `description`. |
| `creators[0].source_caveats` | removed | both | Roster-level editorial reasoning moved to top-level `source_caveats`, where it annotates the roster rather than one person. |
| `funders[0].notes` | changed | both | Award amount now explicitly attached to the award rather than readable as a dataset budget. |
| `collection_timeframes` | removed | both | Entry contained no timeframe; the retrospective character duplicates `acquisition_methods` and the absence is recorded in `source_caveats`. |
| `direct_collection` | removed | full | `is_direct: false` was an inference the entry's own caveat disowned. |
| `acquisition_methods[0].acquisition_details` | changed | both | Expanded to name the hospital systems of record, absorbing the substance of the removed `direct_collection` entry. |
| `subsets` | retained | full | Nine entries and their required fragment ids kept; ids are minted on the record's own `id`, which it also carries as `page`. |
| `subpopulations` | retained | both | Thin but supported by "50,000 Patient admissions from ICU, PICU, and NICU"; `distribution` stays empty for want of per-unit counts. |
| `keywords` | retained | both | Mixed capitalization inherited verbatim from the NIH RePORTER "Preferred terms" line; normalizing would edit quoted text. |
| `machine_annotation_tools` | changed | both | `tools` emitted as a list, matching the declared multivalued range; the OHNLP toolkit's appearance in three slots retained as each answers a different question. |
| `is_deidentified` | retained | both | `identifiable_elements_present` left empty; no source states it outright. |
| `ethical_reviews` | added | both | Bundle-supported ethics activity (community perspectives evaluation; community-facing ethics focus groups) was previously absent from the record. |
| `source_caveats` | changed | both | Absorbed the creator-roster explanation, the pending metadata schemas, the future-tense holdout and labeling statements, and the rationale for the empty `distribution_formats`, `collection_timeframes` and `direct_collection`. |
| `notes` | retained | both | Website banner quotation is correctly placed residual content, unchanged. |