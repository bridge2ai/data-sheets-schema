# Reconciliation report — AI_READI

Version label: `2026-09-01_claude-opus-5-api-generic-v7_rep1`
Records reconciled: full (`AI_READI_d4d.yaml`) and core (`AI_READI_d4d_core.yaml`)
Audit findings received: 26 (4 high, 12 medium, 10 low)

---

## 1. What the audit found

The audit examined the full record against the declared bundle and the schema digest. Its four high-severity findings concerned unsupported attribution and identifier form: creator affiliations transplanted from the study's collaborator roster, CRediT roles assigned by no source, a bare homepage URL standing in a `uriorcurie` publisher slot while a tier-1/tier-1 conflict was resolved silently, and a grant identifier carrying a search URL while the actual award number sat in prose.

Medium findings concerned slot fit and object shape: minted subset fragments nothing referenced, a `DistributionFormat` entry holding an access route rather than a format, source commentary in `notes` where `source_caveats` belongs, an activity label in `reviewing_organization`, a team name in a `Person` object, an `at_risk_populations.special_protections` value restating its sibling boolean, and an `affected_subsets` attribution narrower than the bias described.

Low findings were largely verification notes confirming that omissions (existing uses, errata, imputation protocols, machine annotation tools, data protection impacts) were correctly grounded in explicit attestations of absence in the bundle. Two low findings identified a partial variable list presented without disclosure and reference ranges sitting in prose rather than in the declared `minimum_value`/`maximum_value` float fields.

One high-severity entry was recorded by the auditor as a verification note rather than a defect: `conforms_to_standard` membership was re-checked at top level and per file collection and all seven tokens were confirmed to be in the permitted enum set.

---

## 2. Changes made to the full record

### 2.1 `creators[0].affiliations` — removed (high)

The seven-organization affiliation list is gone from the reconciled record. The bundle attaches those ROR identifiers to the study's `sponsorCollaboratorsModule` — a lead sponsor and six collaborators on the *study* — while the FAIRhub `dataset_description` records exactly one creator, `AI-READI Consortium`, `nameType: Organizational`, with no affiliation field. Re-labelling a study roster as a creator's affiliations asserts a relation the bundle never states.

The seven organizations are not lost: they are named in prose in the entry's rewritten `source_caveats`, which now records what the source actually says about them.

### 2.2 `creators[0].credit_roles` — removed (high)

The six CRediT values (`conceptualization`, `data_curation`, `investigation`, `methodology`, `project_administration`, `supervision`) are gone. No source in the bundle assigns contributor roles to the AI-READI Consortium; they were inferred from the general character of the project. The rewritten `source_caveats` now states that no contributor roles are stated by the source.

### 2.3 `publisher` — removed (high)

The slot is no longer present in either record. The audit correctly noted that a trailing-slash homepage URL is not an identifier for a publishing organization in a `uriorcurie` slot, and that the record disclosed a tier-1/tier-1 conflict in prose while silently picking one side in the slot. Under the uniform rule, sources of the same tier cannot settle a disagreement between them, so the slot is now omitted rather than resolved.

The disagreement is disclosed twice: item (1) of the top-level `source_caveats` was rewritten to say the slot is "left unpopulated rather than resolved silently", and `notes` gained a sentence explaining the omission and naming both candidate values.

### 2.4 `funders[0].grants[0].id` — changed (high)

Was `https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481`; is now `nih:OT2OD032644`. The grant object also gained a `description` field carrying the award number in prose alongside the RePORTER URL, and the `notes` field was trimmed to the funder ROR only.

This change is partial and the record says so. The `nih:` prefix is not among the schema's declared prefixes, and the entry's `source_caveats` was extended to state this plainly: "The `nih:` prefix used on the grant identifier is not declared by the schema; the bare award number OT2OD032644 is the identifier the bundle supplies and is repeated in the grant description alongside its resolver URL." A reader can therefore see both that the award number is now in the identifier position and that the prefix is undeclared.

### 2.5 `subsets` — retained, references added (medium)

The audit found `#validation` and `#test` were minted fragments nothing pointed at. Rather than removing them, the reconciliation added the references: `known_biases[0].affected_subsets` now lists all three. This resolves both this finding and 2.6 below with one change, and it is the correct direction because the bias genuinely affects all three splits.

### 2.6 `known_biases[0].affected_subsets` — widened (medium)

Was `[#train]`; is now `[#train, #validation, #test]`. A new `source_caveats` on the entry explains the reasoning: the imbalance is a property of the enrolled cohort, and the bundle's statement that validation and test are balanced as far as possible describes the mitigation applied to those splits, not evidence they are unaffected.

### 2.7 `distribution_formats[5]` — removed (medium)

The entry whose `format` read `Azure Storage access and a smaller "mini" subset for pipeline development` is gone. It held an access route and a subset offering, neither of which is a distribution format.

Both facts were relocated rather than dropped: `data_governance.access_review_process` gained the sentence "The v3.0.0 documentation additionally describes Azure Storage access and a smaller mini-subset version of the dataset for pipeline development." The mini subset also remains in the top-level `notes`, where it was already recorded.

### 2.8 `distribution_formats[4]` — `notes` moved to `source_caveats` (medium)

The WFDB entry's commentary about why the format was added despite not appearing in the FAIRhub media-type list is trust annotation about sibling values. It now sits in `source_caveats`, with slightly tightened wording ("the file format standard that all data files within that directory follow").

### 2.9 `file_collections[*].conforms_to` — cleaned (medium)

Each collection's `conforms_to` previously read, for example, `WaveForm DataBase (WFDB), within Clinical Dataset Structure (CDS) v0.1.1`. The trailing CDS clause was commentary about the relationship between two standards; the CDS fact is already carried by the `conforms_to_standard` enum. Each `conforms_to` now names only the file-format standard, and the CDS organizational fact was moved into each collection's `description` as a sentence ("The directory and its sub-directories are named and organized following the Clinical Dataset Structure (CDS) v0.1.1, and are accompanied by a manifest.tsv metadata file"). The `root_metadata` collection is unchanged, as CDS is the only standard it follows.

### 2.10 `ethical_reviews[1].reviewing_organization` — removed (medium)

The value `AI-READI ethics review` named an activity, not an organization. The slot is now absent from that entry, and a new `source_caveats` records why: "The RO-Crate ethicalReview field names four individuals and no reviewing organization." The four names remain in `review_details`.

### 2.11 `ethical_reviews[0].contact_person` — removed (medium)

The `Person` object named `IRB Reliance Team, Human Subjects Division` — a team, not a person. It is gone. The contact information was folded into `review_details`, which now ends "The IRB Reliance Team is reachable at hsdrely@uw.edu."

### 2.12 `at_risk_populations.special_protections` — removed (medium)

The single-element list stated that at-risk populations are excluded, which restates `at_risk_groups_included: false` rather than describing protections applied. The list is gone; its content merged into `notes`, which now carries the eligibility restrictions and the transportation assistance in one paragraph.

### 2.13 `license_and_use_terms.source_caveats` — added (medium)

The audit flagged that `disease_specific_research` captures the access condition but not the license grant, which permits commercial use, and that `consentNoncommercial` is recorded as false. A new `source_caveats` on the object states this tension explicitly and notes that no single permitted enum value expresses both scopes.

### 2.14 `instances[0].source_caveats` — added (medium)

The audit asked why `data_substrate` was omitted when the bundle names tabular, imaging and waveform data. A new `source_caveats` states that no single B2AI substrate term covers that combination, so the slot is omitted rather than approximated, and explains the single-term choice for `data_topic`.

### 2.15 `variables` — reference ranges moved into declared fields; list extended (low)

Reference bounds that were prose in `notes` are now in the declared `minimum_value` and `maximum_value` float fields for HbA1c (4.0–6.0), glucose (62–125), C peptide (1.1–4.4), insulin (0.0–24.9), CRP-HS (0.0–10.0), total cholesterol (max 200), HDL (min 39), LDL (max 130), triglycerides (max 150). Each such entry's `notes` now states that these record the reference range, not observed data extremes.

Analytes whose range varies by age or sex — NT-proBNP, troponin-T, creatinine — were deliberately left without bounds, with `notes` explaining why in each case.

Five variables were added from the same source table: blood urea nitrogen, sodium, potassium, albumin, haemoglobin, platelets. The list is now 24 entries rather than 18.

### 2.16 Partial variable list disclosed (low)

The top-level `source_caveats` gained item (6): the variable list transcribes a selection of roughly forty analytes the BMJ Open protocol tabulates, and is partial rather than exhaustive.

### 2.17 `notes` — ClinicalTrials.gov registration relocated (low)

NCT06002048 remains in `notes` but was also added as a sixth `related_datasets` entry with `relationship_type: is_described_by` and the classic.clinicaltrials.gov URL, matching the audit's suggestion that it sits better as a typed relationship.

### 2.18 `created_by` — removed

Not raised in the audit; noted here for completeness of the comparison. The slot held `AI-READI Consortium` in the original full record and is absent from the reconciled one. The creator is carried by `creators[0].name`, so the fact is not lost.

---

## 3. Changes made to the core record

The core record is a projection of the full record, so every change above that touches a projected slot propagated. Specifically: `creators` lost its affiliations and credit roles and gained the rewritten caveat; `funders` carries the new grant id and description; `publisher` and `created_by` are gone; `known_biases[0].affected_subsets` lists three splits; the `distributions` entries carry cleaned `conforms_to` values and extended descriptions; `distribution_formats` lost the Azure entry and moved the WFDB note to a caveat; `ethical_reviews` lost the activity label and the team-as-person; `at_risk_populations` lost `special_protections`; `license_and_use_terms` and `instances` gained caveats; `data_governance.access_review_process` gained the Azure sentence; `related_datasets` gained the ClinicalTrials.gov entry; top-level `notes` and `source_caveats` carry the publisher explanation and the variable-list disclosure.

The `# Phase 4 reconciliation: completed` line was added to the core header block.

No change was made to the core record that was not also made to the full record.

---

## 4. Findings left as-is

**`conforms_to_standard` (high, recorded as a verification note).** The auditor re-checked and found all tokens permitted at both levels. Nothing to change; membership is identical in both versions.

**`instances[0].data_topic` (medium, partial).** `B2AI_TOPIC:43` is unchanged. The audit's substantive point — that `data_substrate` was omitted without explanation — was addressed by the new caveat (2.14), but the topic term itself was left as the auditor described it, "a lossy but defensible choice".

**`human_subject_research` single-element prose lists (medium).** `irb_approval`, `regulatory_compliance` and `special_populations` remain single-element YAML lists of paragraph prose in both versions. The audit asked to "check the declared range"; the schema digest supplied does not state the ranges of these fields, only that they are accepted keys on `HumanSubjectResearch`. Without that information I could not determine whether the list form is a defect, and the records validated as they stand. Left unchanged and recorded here as unresolved.

**`source_caveats` duplication between top level and `is_deidentified` (low).** The de-identification contradiction is still stated in both places, verbatim. The auditor judged it "redundant but not incorrect", and the object-level caveat is the one a reader of that object needs.

**`created_on`, `last_updated_on`, `was_derived_from` (low).** All three remain omitted in both versions. The auditor found each omission defensible; `created_at` duplicates `issued`, the documentation page timestamp is not the dataset's, and the release derives from primary collection rather than another dataset.

**`existing_uses`, `use_repository`, `errata`, `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols`, `data_protection_impacts`, `other_tasks`, `discouraged_uses` (low).** All remain omitted. Each is an attested absence in the bundle, and a slot recording that something does not exist is a pointer-to-absence rather than an answer to the field.

---

## 5. Outcome

All four high-severity findings were resolved, one of them (2.4) partially and with the residual limitation disclosed in the record itself. Nine of twelve medium findings were resolved by removal, relocation or the addition of a caveat; two were addressed in substance while leaving the flagged value in place; one (`human_subject_research` list shapes) was left unresolved for want of schema information and is recorded above. The low findings were largely confirmations; the two actionable ones — reference ranges in prose, and an undisclosed partial variable list — were both acted on.

Both records validated after reconciliation.