# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Declared referent:** the *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, version 3.0.0, DOI `10.60775/fairhub.3`, published 2025-11-17. Both records hold to this single referent throughout. The v1.0.0 and v2.0.0 releases, and the separate Mini Version (`10.60775/fairhub.4`), are represented as related or component resources rather than as the record subject.

---

## 1. Audit outcome

The Phase 3 audit returned **no high-severity findings**: seven medium and the remainder low, across 33 findings. No fabricated dataset facts were identified, and no evidence of reuse from outside the declared bundle was found. Every substantive factual claim traced to `data/preprocessed/concatenated/AI_READI_preprocessed.txt`.

The audit specifically confirmed that the bundle's internal disagreements were surfaced rather than silently resolved:

| Conflict in bundle | Handling |
|---|---|
| University of Washington (IRB, license, NIH RePORTER) vs. Washington University in St. Louis (FAIRhub `managingOrganization`, `leadSponsor`) | Both stated; not merged |
| Target enrolment 4,000 (BMJ Open, NIH RePORTER, FAIRhub) vs. 4,600 (IRB protocol) | Both stated |
| Collection start 18 July 2023 (BMJ Open) vs. 19 July 2023 (FAIRhub `dateType: Collected`) | Both stated |
| `deIdentType: NoDeIdentification` with `deIdentHIPAA: true` (FAIRhub) vs. HIPAA Safe Harbor stripping (Nature Metabolism) | Both stated |
| "Equitable" (BMJ Open, docs) vs. "Exploratory" (NIH RePORTER, README, healthsheet) acronym expansion | Both preserved |

The findings clustered into three groups: constructed values the bundle does not literally contain; two schema-semantics ambiguities; and asymmetries between the paired records, mostly core-record omissions.

---

## 2. Changes made

### 2.1 Core record — restored directly stated aggregates

**Changed.** `total_file_count: 356343` and `total_size_bytes: 3815969779678` were added to the core record.

Both figures are stated verbatim in the bundle (FAIRhub API `data.fileCount`, `data.size`; corroborated by the HTML capture's "3.82 TB / 356,343 Files" and by the README). Both were populated in the full record. Their absence from the core record was an unforced asymmetry, not a schema constraint — `CoreDataset` declares both slots. Prior to this change the aggregate survived in the core record only as prose inside the tenth `distributions` entry, which is not machine-readable as a count or a byte size.

### 2.2 Core record — recovered four pieces of lost evidence

The audit identified four bundle-supported facts present in the full record and absent everywhere in the core record. Each was folded into the nearest core-declared slot rather than left dropped:

- **Recommended split counts (70/15/15).** The full record's four `splits` entries carry the per-cell breakdown by race/ethnicity, sex, and diabetes status from the README table. `CoreDataset` does not declare `splits`; a condensed statement of the proportions and the balancing criteria was added to the existing `subpopulations` content, which already referenced the split's existence and rationale.
- **Recruitment-screening date disagreement.** BMJ Open states the study base comprised patients with an encounter "between 2020 and 2025"; the healthsheet states screening covered encounters "within the past 2 years." Both readings were added to the core record's `acquisition_methods` content, stated side by side.
- **Transportation-reimbursement conflict.** The IRB protocol states in §4.4 that the study "will cover reasonable costs for parking, public transit, or rideshare fees" and in §11.2 that "subjects may incur costs for transport that will not be reimbursed if transportation fees exceed $25." `CoreDataset` does not declare `participant_compensation`; both statements, together with the $200 stipend and its timing, were added to the core `informed_consent` content, where the other participant-facing terms already sit.
- **Biospecimen-request governance.** The BMJ Open protocol states that biobanked samples "will eventually be available to scientists according to procedures and policies that are in development," and that request-review procedures "will be developed before the biorepository is complete." This was added to the core `distributions` content alongside the existing access-gating description.

### 2.3 Both records — removed a derived keyword

**Changed.** `Salutogenesis` was removed from `keywords` in both records.

The term appears throughout the bundle as substantive prose, and it remains in both records' `description` and `purposes`. It does not appear in any structured keyword or subject list — not in the FAIRhub `subject` array, not in the `studyDescription.conditionsModule.keywordList`, and not on the HTML capture's keyword panel. `keywords` is a transcription-friendly slot, and the uniform decision rule prefers omission over inference. The remaining ten keywords all trace to one of the two structured lists.

### 2.4 Both records — retitled the Mini Version resource

**Changed.** The `resources` entry for the Mini Version was retitled from "Mini Version of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project" to "Mini Version" (100 participants, DOI `10.60775/fairhub.4`).

The bundle's curation note names it only as a "'Mini Version' (100 participants, DOI 10.60775/fairhub.4) for pipeline development." The longer title was extrapolated from the parent dataset's title. The existing disclosure that the Mini Version record itself was not captured is retained.

---

## 3. Left as-is, with reasoning

### 3.1 Constructed values retained

**`citation` (full, medium).** Retained. The bundle provides no citation string: FAIRhub and both documentation captures defer to `https://docs.aireadi.org/docs/3/citation`, which is not in the corpus. The existing value is transparently framed as a pointer ("please follow the citation instructions provided at…") and the surrounding facts it assembles — creator `AI-READI Consortium`, publisher `FAIRhub`, `publicationYear: 2025` — are each directly stated in the FAIRhub `datasetDescription`. Emptying the slot would discard evidence the bundle does supply; replacing the pointer with an authored citation would be worse. The framing already discloses the gap.

**`file_collections[].id` (full, low).** Retained. The nine fragment URIs (`https://fairhub.io/datasets/3#cardiac_ecg` and so on) do not exist in the bundle; the directory names do. `FileCollection` requires `id`, so some identifier is unavoidable. The construction is systematic, traceable to the `directoryName` values in `datasetStructureDescription`, and lossless. These URIs should not be read as resolvable, which is a property of the construction rather than a defect to be corrected.

**`variables` (full, low).** Retained, and deliberately still absent from the core record. The twelve `variable_name` values are snake_case coinages; the bundle's actual variable list is an external document referenced in the IRB protocol ("List of variables is uploaded and listed below") whose content is not in the extracted text. The underlying measurements are all well evidenced and the `description` text on each entry is faithful. Retaining them in the full record preserves real evidence about what the dataset measures; omitting them from the core record is the safer choice for a slot whose keys cannot be verified. The asymmetry is intentional and is recorded here.

**`id` and `issued` datatype coercions (both, low).** Retained. `https://doi.org/10.60775/fairhub.3` is the conventional resolver form of the stated DOI `10.60775/fairhub.3`; `2025-11-17T00:00:00+00:00` is the datetime rendering of the stated date `2025-11-17`. Both slot ranges (`uriorcurie`, `datetime`) require the coerced form. No information is added or lost.

**`publisher` (both, low).** Retained as `https://fairhub.io`. The bundle gives `publisherName: "FAIRhub"` without a URI; the slot range is `uriorcurie`. The platform address is the only identifier the bundle supports and is corroborated by three separate captures.

### 3.2 Schema-semantics ambiguities retained

**`created_by` (both, medium).** Retained as `AI-READI Consortium`. The audit is right that the schema's "person or organization primarily responsible for creating the resource" is not identical to DataCite's `creator`, and that the bundle separately names a managing organization and a responsible party. But the bundle's only direct statement about who created the dataset is `creatorName: "AI-READI Consortium"` (`nameType: Organizational`), reinforced by the healthsheet's "This dataset was created by members of the AI-READI project, hereby referred to as the AI-READI Consortium." Substituting the managing organization would be an inference; the managing organization and responsible party are recorded separately and are not lost.

**`conforms_to_schema` (both, low).** Retained as the `dataset_description.json` v0.1.0 URI. The bundle shows two AI-READI schemas in use; the slot is single-valued. `dataset_description.json` governs the record-level metadata that these D4D records chiefly transcribe, so it is the better fit. `dataset_structure_description.json` v0.1.1 is retained under `external_resources`, alongside the Clinical Dataset Structure (CDS) v0.1.1 specification that governs the directory layout.

### 3.3 Framing retained

**`description` composite acronym (both, low).** Retained as "Artificial Intelligence Ready and Equitable/Exploratory Atlas for Diabetes Insights." The slash notation is a constructed string appearing verbatim in neither source, but it surfaces a genuine and unresolved disagreement in the bundle rather than concealing it. Picking one expansion would be a silent resolution of the kind the decision rules prohibit.

**`is_tabular: false` (both, low).** Retained. The bundle describes a mixture: OMOP CSV tables and TSV manifests alongside DICOM imaging and WFDB waveforms. `false` is the correct reading for a predominantly non-tabular multimodal release. It is a judgment, but the slot admits only a boolean and the alternative would be less accurate.

**`at_risk_populations` (both, low).** Retained, including its explicit statement that the IRB protocol form "contains the corresponding sections but the project-specific answers for those sections are not populated in the extracted text." This is the correct handling: the negative claims about prisoners, cognitively impaired adults, and wards rest on absence of evidence, and the record says so rather than asserting them as findings.

### 3.4 Structural asymmetries retained as legitimate remappings

The following full-record slots have no counterpart in `CoreDataset` and were remapped rather than dropped. Content is preserved; only its location differs between the paired records. This is recorded for traceability, not corrected:

| Full-record slot | Core-record location |
|---|---|
| `file_collections` | `distributions` (nine per-datatype entries plus one whole-dataset entry) |
| `collection_notifications` | folded into `informed_consent` |
| `consent_revocations` | folded into `informed_consent` |
| `direct_collection` | folded into `acquisition_methods` (see §2.2 for the recovered date disagreement) |
| `participant_privacy` | distributed across `informed_consent` and `distributions` |
| `relationships` | single-visit structure retained via `known_limitations`; directory-linkage and paired-eye laterality not carried |
| `third_party_sharing` | `distributions` (see §2.2 for the recovered biospecimen governance) |
| `collection_consents` | `intended_uses` (consent-scope flags); Dexcom Clarity retrospective-download consent retained under `acquisition_methods` |

Two items remain absent from the core record after reconciliation and are noted as accepted loss: the participant-ID linkage across `datatype/modality/device` directories, and the paired-eye laterality relationship. Both are structural properties of the file layout rather than facts about the data subjects, and both are fully represented in the full record's `relationships` and `file_collections`.

---

## 4. Consistency check

- **Referent.** Both records name the same subject (v3.0.0, `10.60775/fairhub.3`) and the same three prior/related releases. No drift.
- **Conflicting-evidence handling.** All five bundle conflicts listed in §1 are represented in both records after reconciliation. Before reconciliation, the recruitment-screening date conflict and the transportation-reimbursement conflict appeared only in the full record; both are now in both.
- **Aggregate figures.** `total_file_count` and `total_size_bytes` now agree across the two records and against the bundle's three independent statements of them.
- **Keywords.** Now identical across the two records: ten terms, each traceable to a structured keyword or subject list.

---

## 5. Outcome

**Reconciled.** Six changes were applied: two restored aggregate slots and four recovered evidence items in the core record, one keyword removal and one retitling across both records. Twelve findings were reviewed and deliberately left as-is, each with the reasoning recorded above. No high-severity findings were raised and none required correction. The two records are now consistent in referent, in conflict handling, and in aggregate figures, with the remaining differences confined to schema-driven remappings and one intentional asymmetry (`variables`).