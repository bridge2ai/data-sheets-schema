# Phase 4 Reconciliation Report — AI_READI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-09-01_claude-opus-5-api-generic-v7_rep1/AI_READI_d4d_core.yaml`

**Audit input:** 30 findings (6 high, 11 medium, 13 low) against the declared bundle `AI_READI_preprocessed.txt` (md5 `8abd7bf5389b562b95794d656af19392`).

---

## 1. Findings acted on

### 1.1 Identifier hygiene

**`creators[0].affiliations[0].id` — high — changed.**
The original first creator carried `id: https://aireadi.org/` on the AI-READI Consortium organization object. The bundle supplies no registry identifier for the Consortium; a project homepage is not an organization registry entry. The `id` was removed, leaving `name: AI-READI Consortium`. The homepage is now recorded in that entry's `notes` ("details of each member and their institutions are on the project website at https://aireadi.org") and in `external_resources`, where a URL is the correct content.

**`funders[0].grants[0].id` — high — changed.**
The original Grant carried `id: https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481` — a session-scoped RePORTER search permalink — and bundled award number and award title into one `name` string (`'OT2OD032644: Bridge2AI: Salutogenesis Data Generation Project'`). The `id` was removed and the entry split so `name: OT2OD032644` carries the award number alone and `description` carries the award title. The other two grants (`P30DK035816`, `UL1TR003096`) already had bare award numbers as `name`, so the list is now internally consistent. The RePORTER links (both 10885481 and 10471118) are preserved in the funder's `source_caveats` and in `external_resources`.

**`publisher` — low — changed.**
The original had `publisher: https://fairhub.io/` in a `uriorcurie`-ranged slot. The bundle gives `publisherName: "FAIRhub"` with no registry identifier, and the RO-Crate gives a competing publisher value ("AI-READI Consortium"); both sources are tier 1, so the ranking cannot decide between them. The slot was removed. Both statements are now recorded in the top-level `notes`, in `source_caveats` item (2), and in `distribution_formats[3].notes`.

### 1.2 Structural collapse in typed fields

**`variables[48].categories` — medium — changed.**
`Monofilament touch perception` had `categories: ['yes; no']` — two labels in one semicolon-joined string. Now two entries: `['yes', 'no']` (quoted to prevent YAML boolean coercion).

**`variables[*]` reference ranges — medium — changed (partially).**
Roughly twenty laboratory variables carried two-sided numeric reference ranges as prose in `notes` while the declared float slots `minimum_value` / `maximum_value` sat empty. Those slots are now populated wherever the bundle gives a single unambiguous numeric range: C peptide, Insulin, CRP-HS, Glucose, BUN, Sodium, Potassium, Chloride, CO2, Calcium, Total protein, Albumin, Bilirubin, AST, HbA1c, and the ten CBC measures. One-sided ranges are recorded on the bound the source states (Total cholesterol `maximum_value: 200.0`; Triglycerides `150.0`; HDL `minimum_value: 39.0`; LDL `maximum_value: 130.0`).

Three variables were deliberately **not** given numeric bounds because the bundle's range is not a single interval: **Creatinine** and **Alanine aminotransferase** have sex- and age-stratified ranges, and **Alkaline phosphatase** and **NT-proBNP** are reported only as "varies by age". For **Troponin-T** the male upper bound (16) is recorded in `maximum_value` with the female bound (11) stated in `notes`, since a single float cannot hold both. Each of these carries an explanatory `notes` sentence. The prose form "Reference range: 3.6-5.2" was replaced throughout by "Reference range reported by the testing laboratory", so the structured slots are now the authoritative carrier.

### 1.3 Inferred enum values

**`regulatory_restrictions.confidentiality_level` — medium — changed (removed).**
The original asserted `restricted`, derived by inference from the RO-Crate's differently-coded `"HL7:2N (normal)"` and from the access workflow; the original's own `source_caveats` conceded that no source states the schema's terms. The slot was removed. The RO-Crate value is now stated verbatim in `regulatory_restrictions.other_compliance`, and the omission is explained in that object's rewritten `source_caveats`.

**`regulatory_restrictions.hipaa_compliant` — medium — changed (removed).**
Likewise `compliant` was inferred from `deIdentHIPAA: true` and the licence's BAA storage requirement. Removed. The underlying source statements are preserved in `other_compliance`.

**`at_risk_populations.at_risk_groups_included` — medium — changed (removed).**
The original asserted `false` on the basis of eligibility criteria while its own caveat stated the governing IRB questions are unanswered in the bundle. The boolean was removed; `special_protections` is retained and, as a side effect of the same edit, split from one long entry into three (eligibility criteria; Community Advisory Board; Native Biodata Consortium engagement plus the RePORTER tribal-consultation statement), one per distinct protection. The `source_caveats` was rewritten to explain why the boolean is unset.

### 1.4 Ranking inversion

**`license` — medium — changed.**
The original carried the tier 2 licence-document title, `"AI-READI Data License Agreement (Version 2.0)"`, over two tier 1 FAIRhub labels. Per the declared ranking, the slot now reads `Health Data License` (the FAIRhub landing-page label). All three titles are recorded in `license_and_use_terms.license_terms` and in that object's `source_caveats`, and the top-level `source_caveats` item (1) was rewritten to record which value was preferred and why.

### 1.5 Entity conflation and misclassification

**`creators[0].principal_investigator` — high — changed.**
Aaron Lee was embedded as `principal_investigator` inside the organizational creator entry. He is now his own Creator entry (second in the list), with his ORCID, his FAIRhub-recorded affiliation, and a `notes` field recording his three FAIRhub roles. The organizational entry now carries only `affiliations` and `notes`. The creators list grew from 16 to 17 entries.

**`creators[0].source_caveats` — high — changed.**
The original placed list-level commentary ("The further creator entries below are…") in a per-object `source_caveats`. That commentary moved to the top-level `source_caveats` (final paragraph). The organizational entry's remaining content — what the DataCite record and healthsheet say about the Consortium — moved to that entry's `notes`, which is where dataset content belongs.

**`funders[2]` (Microsoft AI for Good Lab) — high — changed (removed).**
Recorded as a FundingMechanism with `grantor: Microsoft AI for Good Lab`, though the bundle describes only in-kind support for cloud services and the entry's own `notes` conceded this. The funder entry was removed. The fact is now recorded in `collection_mechanisms` (appended to the FAIRhub/Azure mechanism, which is what the support underwrote) and in the top-level `notes`. `funders` went from 3 entries to 2; a `notes` was added to the Research to Prevent Blindness entry recording its source.

### 1.6 Substantive omission

**`extension_mechanism` — low — changed (added).**
The original omitted the slot entirely, losing the bundle's plain statement that no mechanism exists for outside contribution. `extension_mechanism.extension_details` was added carrying that statement plus the versioned-release path by which new instances actually arrive.

**`other_tasks` — low — changed (added).**
The original folded hypothesis-agnostic scope into `tasks` and `intended_uses` only. An `other_tasks` entry was added recording the hypothesis-agnostic design and the healthsheet's statement that no formal guidelines exist for defining new tasks.

**`discouraged_uses` — low — changed (added).**
The original omitted the slot while carrying seven `prohibited_uses`. A `discouraged_uses` entry was added recording that the healthsheet answers both the "discouraged applications" and "tasks it should not be used for" questions by reference to the licence, and explaining why those restrictions are routed to `prohibited_uses` instead.

**`created_on` — low — changed (added).**
`created_on: '2025-11-17T00:00:00Z'` was added from the FAIRhub API `created_at: 1763366400`. It duplicates `issued`, but the field is available in the bundle.

### 1.7 Annotation and duplication

**`instances[0].data_substrate` — medium — changed (annotated).**
Still omitted, but a `source_caveats` was added to the Instance explaining that a single Instance object cannot carry a list and that the bundle documents several distinct substrates within one instance; it points to `file_collections` and `conforms_to` where the per-datatype substrate is recorded.

**`instances[0].notes` version-count duplication — medium — changed.**
The sentence "Version 1.0.0 contained 204 participants, version 2.0.0 contained 1,067, and this version contains 2,280" was removed from the Instance `notes`; the same content is already in `version_access.versions_available`.

**`subpopulations[1].source_caveats` — medium — changed.**
The original characterized the healthsheet/README discrepancy as two sources of equal tier. Both statements are in the FAIRhub record. The caveat was rewritten to say the conflict is internal to that one source and to explain how it resolves (released files vs. aggregate documentation).

**`collection_timeframes[0].source_caveats` — low — changed (removed).**
The 2023-07-19 vs. 18 July 2023 discrepancy was stated both here and in top-level `source_caveats` item (5). The per-object caveat was removed; item (5) now carries the disclosure and adds "the FAIRhub value is used".

**`external_resources[*].external_resources` — low — changed.**
All nine entries had the form `'Label: URL'` in one string. Each now carries the bare URL in `external_resources` with the label moved to `notes`.

**`file_collections[*].conforms_to` — medium — changed (removed).**
The nine per-collection `conforms_to` prose sentences ("DICOM, within a CDS v0.1.1 directory layout") restated what the top-level `conforms_to` already maps in full. They were removed. Each collection retains its `conforms_to_standard` enum list, which is the queryable form and is not redundant. The corresponding `conforms_to` strings were removed from the ten core `distributions` entries as well.

**`existing_uses` — low — changed (annotated, not populated).**
Correctly omitted (healthsheet answers "No"), but the unrecorded FAIRhub view count is now in the top-level `notes`: "FAIRhub reports 24,636 views and 0 citations for this release."

**`errata` and de-identification blanks — low — changed (annotated).**
The three healthsheet questions with empty source responses (erratum; measures to avoid re-identification; pre-processing for de-identification) are now named in the top-level `source_caveats` and in `is_deidentified.source_caveats`, so the pattern of blanks is visible rather than silent.

**`parent_datasets` / `resources` — low — changed (annotated).**
Both remain omitted. The top-level `notes` now records that the mini version has no DOI or identifier in the bundle, and that FAIRhub records no parent.

---

## 2. Findings left as-is

**`conforms_to_standard` including `CDS` — high, self-withdrawn.** The auditor raised and then withdrew this on re-check: `CDS` is a permitted `DataStandardEnum` value in the schema digest. No change.

**`instances` as a single object — medium — left as-is.** The healthsheet states plainly that each instance represents an individual patient; one Instance is the correct modelling. The duplication complaint bundled with this finding was addressed separately (§1.7). Unchanged.

**`created_by` duplicating the Consortium name — low — left as-is.** `created_by: AI-READI Consortium` remains. It is a supported string-ranged value; the duplication with `creators[0].affiliations[0].name` is benign and removing it would lose a top-level answer.

**`download_url` — low — left as-is (omitted).** No direct download exists; access is gated. The access route remains in `distribution_formats[0].access_urls` (declared range `uri`, correctly a URL) and in `data_governance.access_review_process`.

**`was_derived_from` — low — left as-is (omitted).** The version lineage is carried by two `is_new_version_of` entries in `related_datasets`, which is the typed form.

**`use_repository`, `data_protection_impacts`, `imputation_protocols`, `annotation_analyses`, `labeling_strategies`, `machine_annotation_tools` — low — left as-is (omitted).** Each corresponds to an explicit "No" or "N/A" in the healthsheet. Populating a slot with an absence is a defect; the substance is carried where it belongs (`instances[0].label: false` and `label_description` for labeling; `missing_data_documentation[0].handling_strategy` for imputation).

**`keywords` merging two sources — low — left as-is.** Both keyword sets are tier 1 and both are in the bundle; the merged list of ten remains.

---

## 3. Cross-record consistency

Every change above was applied identically to the core record where the slot is present in `CoreDataset`. Specifically: creators split and de-identified affiliation; funders reduced to two with the grant restructured; `license` changed to `Health Data License`; `confidentiality_level`, `hipaa_compliant`, `at_risk_groups_included` removed; `created_on` added; `other_tasks`, `discouraged_uses`, `extension_mechanism` added; per-distribution `conforms_to` removed; `external_resources` reshaped; all rewritten caveats and notes carried across. `variables` is not a `CoreDataset` slot, so the reference-range and `categories` fixes appear only in the full record. `publisher` was removed from both.

The referent is unchanged in both records: version 3.0.0 of the Flagship Dataset (DOI 10.60775/fairhub.3), not the AI-READI project or the study.

**Slot counts:** full 74 top-level slots populated (was 71); core 65 (was 63).

**Validation:** both records validate — full against `Dataset`, core against `CoreDataset`.

**No fabricated facts** were introduced. Every added value traces to the declared bundle; every removed value was either unsupported, inferred rather than stated, or duplicative of a better-placed value elsewhere in the same record.