# Reconciliation Report — CHoRUS

**Project:** CHORUS
**Referent:** CHoRUS dataset (https://chorus4ai.org/)
**Version label:** 2026-09-12_claude-opus-5-api-generic-v9_rep1
**Records compared:** original full / original core against reconciled full / completed core, as supplied.

---

## 1. What the audit found

The audit returned twenty-three findings: two high, nine medium, twelve low. They cluster into four groups.

**Header conformance (1 high).** The `# Temperature:` line in both headers deviates from the mandated verbatim text.

**Tense and subject discipline (2 high, 1 medium).** `splits` and `labeling_strategies` each carried a future-tense plan from the NIH RePORTER abstract — a holdout set that "will provision", an annotation environment that "will label" — stated in slots that describe the released dataset's current state. A related medium finding observed that `data_governance.access_review_process` presented the AIM-AHEAD training-program access route as the dataset's general process.

**Slot fit (6 medium).** `distribution_formats` carried data standards already recorded in `conforms_to`/`conforms_to_standard`; two `maintainers` entries were access-request contacts, not maintainers; one `known_limitations` entry reported that documentation is pending rather than stating a limitation of the data; `external_resources` entry 3 was a pointer to a pointer, and entry 1 attached the software organization's MIT License to a dataset-level resource entry; the 1.6 Billion → 1600000000 expansion was the record's own computation presented as a transcription.

**Thin, inferential, or missing values (12 low, 1 medium).** A `collection_timeframes` entry containing no timeframe; a `direct_collection` boolean the entry's own caveat admitted no source states; a single `creators` entry where six leadership members are named in the bundle but held only in `description`; Creator-level source commentary that belongs at record level; bundle-supported ethics activity (community-facing focus groups, the consortium ethics pillar) appearing nowhere in the record; and several notes recording that particular omissions were correct.

---

## 2. What was changed, and why

### 2.1 Changes I can locate in the full record

**`splits` — removed.** Present in the original full record with a single `split_details` entry whose own text reads "states, in the future tense, that the dataset will provision a holdout test set". Absent from the reconciled full record. A planned partition is not a recommended split of released data. The intention is preserved in top-level `source_caveats`, which now states that the abstract "states in the future tense that the dataset will provision a holdout test set for external validation … neither is recorded as a current split or labeling procedure."

**`labeling_strategies` — removed.** Present in the original full record with one entry beginning "The project states that a visualization and annotation environment will label data". Absent from the reconciled full record, and folded into the same `source_caveats` sentence.

**`distribution_formats` — removed.** Six entries in the original, each carrying a standard (OMOP CDM, OHNLP, DICOM, WFDB, EDF+, Persyst) in the `format` field. Absent from the reconciled full record. `source_caveats` now records the reason: "The bundle describes distribution only as a controlled-access cloud enclave, which is an access route rather than a distribution format, so distribution_formats is left empty and the applicable data standards are recorded in conforms_to, conforms_to_standard, and the subset entries."

**`collection_timeframes` — removed.** The original entry stated only that collection is retrospective and then admitted in its own caveat that no calendar range is given. Absent from the reconciled full record; the retrospective character survives in `acquisition_methods`, and the absence is recorded in `source_caveats`.

**`direct_collection` — removed.** The original carried `is_direct: false` with a caveat conceding "No source states the direct or indirect character of collection in those terms." Absent from the reconciled full record. The substance of its `collection_details` — extraction from EHRs, PACS, bedside monitor gateways and a hospital EEG database — was moved into `acquisition_methods[0].acquisition_details`, which now names those four source systems where the original did not.

**`maintainers` — changed.** Three entries reduced to one. The two access-request contacts (dbold@emory.edu, jared.houghtaling@tuftsmedicine.org) are gone from `maintainers` and now appear in `data_governance.access_review_process`. The remaining entry was trimmed from "is the contact listed on the CHoRUS project website, reachable at cmccrary@mgh.havard.edu" to the bare fact: "Ciera McCrary, Program Manager, Massachusetts General Hospital, cmccrary@mgh.havard.edu."

**`data_governance` — changed.** `access_review_process` was rewritten. It now opens with the GitHub request-access route, then scopes the registration-form/licensing-agreement/.edu-email material explicitly to "the AIM-AHEAD Bridge2AI for Clinical Care Training Program cohort 2, the route stated by the cohort 2 webinar". A new `source_caveats` was added on the object stating that the bundle gives no general access review process beyond the GitHub contacts.

**`known_limitations` — changed.** Four entries reduced to three. The entry about metadata schemas being "planned rather than available" is gone from the slot and now appears verbatim in top-level `source_caveats`.

**`external_resources` — changed.** Three entries reduced to two. The entry reading "lists www.bridge2ai.org/chorus as a project website" was dropped. The GitHub entry no longer ends with "; the project there is licensed under the MIT License" — that attribution already sits in `source_caveats`, correctly scoped to the software project.

**`instances[1].source_caveats` — changed.** Rewritten from "the count is transcribed here in full digits" to name the computation: the value "is this record's own expansion of that rounded figure into digits; no source prints the count in full digits." The source phrase is now quoted verbatim.

**`ethical_reviews` — added.** One entry, `reviewing_organization: CHoRUS consortium`, recording the consortium's evaluation of community perspectives on clinical care AI and the abstract's statement that the project will perform community-facing ethics focus groups. The future tense is preserved in the value's own wording. This answers the audit's observation that bundle-supported ethics activity appeared nowhere.

**`creators[0].source_caveats` — removed; `source_caveats` (top level) — changed.** The Creator-level caveat explaining why other leadership members are excluded is gone; that reasoning now sits in the record's top-level `source_caveats`, where it governs the roster rather than one person's entry.

**`funders[0].notes` — changed.** Reworded so the award amount reads as an attribute of the award, not of the dataset: "NIH RePORTER records a fiscal year 2022 award amount of 5,880,300 US dollars for this award."

### 2.2 Changes in the core record

The core record is a projection, and every change above propagates to the slots the core schema declares. Comparing the original core to the completed core: `labeling_strategies`, `distribution_formats` and `collection_timeframes` are absent; `maintainers` is one entry; `known_limitations` is three; `external_resources` is two; `data_governance` carries the rescoped process and its new `source_caveats`; `ethical_reviews` is present; `creators[0].source_caveats` is gone; `instances[1].source_caveats` and `funders[0].notes` carry the reconciled wording; `acquisition_methods[0]` names the four source systems; top-level `source_caveats` matches the full record. The header gained `# Phase 4 reconciliation: completed`.

`splits` and `direct_collection` are not declared in the `CoreDataset` inventory and were never in the core record, so their removal is a full-record event only.

---

## 3. What was left as-is, and why

**The `# Temperature:` header line (high).** Both the reconciled full record and the completed core still read `# Temperature: not sent (claude-opus-5 rejects the parameter; the config's value did not reach the request)`. I can confirm by comparison that this was **not** changed in either record. The finding stands unremedied. It is a conformance defect against the mandated verbatim header block and should be repaired.

**`instances[1].counts` value (medium).** The integer 1600000000 is unchanged. Only its caveat was rewritten. The figure remains the record's own expansion, now labeled as such, with the source phrase quoted; the audit's mitigation note (that the caveat discloses it) is now fully satisfied without altering the value.

**`creators` roster (low).** Still one entry. The five further leadership members named in the cohort 2 webinar remain in `description` and are now accounted for in top-level `source_caveats`, which states that the webinar "names a CHoRUS leadership team without designating those members as principal investigators, and they are therefore recorded in the dataset description rather than as creators." I judged the alternative — six Creator entries, five of them asserting a creator role the bundle does not state — worse than the documented asymmetry. The audit called this an internal inconsistency; it is now an explained one.

**`funders[0].notes` carrying award amount and period (low).** Retained in reworded form. `FundingMechanism` declares no field for either, and the facts are bundle-supported.

**`subsets[*].id` fragments (low).** All nine retained unchanged. `DataSubset` requires `id`, so they must stay while the entries stay. The audit itself concluded as much. The base (https://chorus4ai.org/) matches the record's `id` and `page`, so the labels are receipt-exempt.

**`subpopulations` (low).** Three entries retained unchanged. Thin, as the audit says, but supported by "50,000 Patient admissions from ICU, PICU, and NICU"; `distribution` stays empty because no per-unit figures exist.

**`keywords` capitalization (low).** Unchanged. The list is transcribed from the NIH RePORTER "Preferred terms" line; source spelling and case are preserved.

**`machine_annotation_tools[0]` (low).** Retained. The OHNLP toolkit does appear in three slots, but each records a distinct fact — the tool, the preprocessing step, the collection mechanism — and none is false.

**`is_deidentified.identifiable_elements_present` (low).** Still omitted, as the audit's own reading recommended.

**`collection_consents`, `human_subject_research` (low).** Still omitted; no consent mechanism, IRB approval or ethics committee is named. `ethical_reviews`, the third member of that finding, was added.

**`related_datasets` (low).** Still omitted. No typed relationship to a named dataset is stated, and both `relationship_type` and `target_dataset` are required.

**`notes` banner quotation (low).** Retained in both records as residual content.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `splits` | removed | full | Sole entry was a future-tense plan ("will provision a holdout test set"); intention moved to `source_caveats`. Not declared in `CoreDataset`. |
| `labeling_strategies` | removed | both | Sole entry described an annotation environment that "will label data"; a plan, not an applied procedure. |
| `distribution_formats` | removed | both | Entries carried data standards, not distribution formats; standards already in `conforms_to`/`conforms_to_standard`/subsets. Reason recorded in `source_caveats`. |
| `collection_timeframes` | removed | both | Entry contained no timeframe and admitted the range is unstated; retrospective character kept in `acquisition_methods`. |
| `direct_collection` | removed | full | `is_direct: false` was an inference the entry's own caveat disavowed. Not declared in `CoreDataset`. |
| `creators[0].source_caveats` | removed | both | Roster-level commentary moved to top-level `source_caveats`, where it governs the list rather than one person. |
| `maintainers` | changed | both | Three entries reduced to one; the two access-request contacts moved to `data_governance.access_review_process`; remaining entry trimmed to the fact. |
| `data_governance` | changed | both | `access_review_process` rescoped to the training-program cohort with the GitHub route named; object-level `source_caveats` added. |
| `known_limitations` | changed | both | Four entries reduced to three; the pending-documentation entry moved to `source_caveats` as source commentary. |
| `external_resources` | changed | both | Three entries reduced to two; pointer-to-a-pointer entry dropped; MIT License clause removed from the GitHub entry. |
| `instances[1].source_caveats` | changed | both | Rewritten to label 1600000000 as this record's own expansion of "1.6 Billion", with the source phrase quoted. |
| `acquisition_methods[0].acquisition_details` | changed | both | Absorbed the four source systems (EHRs, PACS, bedside monitor gateways, hospital EEG database) from the removed `direct_collection` entry. |
| `funders[0].notes` | changed | both | Reworded so the award amount reads as an attribute of the award rather than the dataset. |
| `source_caveats` | changed | both | Absorbed the removed future-tense statements, the pending-metadata note, the creators-roster reasoning, and the rationale for the empty `distribution_formats`, `collection_timeframes` and `direct_collection`. |
| `ethical_reviews` | added | both | Community-facing ethics focus groups and the consortium ethics pillar were bundle-supported and previously absent. |
| `instances[1].counts` | retained | both | Value unchanged; the audit's concern was disclosure, now met by the rewritten caveat. |
| `creators` | retained | both | Still one entry; asserting five further creator roles the bundle does not state would be worse than the now-explained asymmetry. |
| `subsets` | retained | full | Nine fragment ids required by `DataSubset`; base matches the record's `id`/`page`. Not declared in `CoreDataset`. |
| `subpopulations` | retained | both | Thin but supported by the ICU/PICU/NICU phrase; no per-unit figures exist for `distribution`. |
| `keywords` | retained | both | Mixed case inherited verbatim from the NIH RePORTER "Preferred terms" line. |
| `machine_annotation_tools` | retained | both | The three appearances of the OHNLP toolkit record three distinct facts, none false. |
| `is_deidentified` | retained | both | `identifiable_elements_present` left unpopulated, as the audit's own reading recommended. |
| `notes` | retained | both | Website banner is residual content and correctly placed. |