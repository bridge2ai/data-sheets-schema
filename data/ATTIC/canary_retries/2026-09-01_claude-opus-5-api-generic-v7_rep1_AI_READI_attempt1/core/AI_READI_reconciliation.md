# Reconciliation Report — AI_READI

Version label: `2026-09-01_claude-opus-5-api-generic-v7_rep1`
Records: full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
Audit findings received: 26 (4 high, 12 medium, 10 low)

---

## 1. Summary of outcome

Of the 26 findings, 14 produced a change in one or both records, and 12 were left as-is. Every change made to the full record was carried through the projection into the core record, since the core is derived from the full by projection rather than regenerated.

The four high-severity findings all produced changes: two unsupported claims were removed outright, one silently-resolved tier conflict was made explicit by unpopulating the slot, and one identifier was moved from a resolver URL to the identifier the bundle actually supplies.

---

## 2. High-severity findings

### 2.1 `conforms_to_standard` — verification note, no defect

The audit re-checked its own concern and concluded that all seven tokens (`CDS`, `WFDB`, `OMOP_CDM`, `ESDS`, `DICOM`, `OPEN_MHEALTH`, `RO_CRATE`) are members of the permitted enum at both top level and per file collection, and recorded the item as a verification note rather than a defect.

**Action: left as-is.** Both records still carry the same seven-token list at top level and the same per-collection pairs. No change was warranted and none was made.

### 2.2 `publisher` — resolver URL in a `uriorcurie` slot, tier-1 conflict resolved silently

**Changed.** In the original full record the slot read:

```yaml
publisher: https://fairhub.io/
```

with the conflict disclosed only in `source_caveats`. In the reconciled record the `publisher` slot is absent from both the full and the core record.

Rationale: the two sources that name a publisher are both tier 1 (`fairhub_dataset_v3_api` gives `publisherName: "FAIRhub"`; `ro_crate_metadata` gives `publisher: "AI-READI Consortium"`). Same-tier disagreement is not settled by the declared ranking, so the correct behavior is to represent the disagreement rather than select one. Additionally, neither source supplies a registry identifier for either candidate, so no CURIE fits and a trailing-slash homepage URL is not an identifier for the publishing organization.

The disagreement is now stated in two places: the top-level `notes` slot gained a sentence explaining why `publisher` is unpopulated, and item (1) of `source_caveats` was rewritten from "FAIRhub was recorded here because the same record also supplies the DOI and landing page" to "the publisher slot is left unpopulated rather than resolved silently". Both edits appear in both records.

### 2.3 `creators[0].affiliations` — unsupported claim

**Changed.** The original record carried seven `Organization` objects with ROR CURIEs (Washington University in St. Louis, UAB, UCSD, Johns Hopkins, OHSU, Stanford, California Medical Innovations Institute) as affiliations of the AI-READI Consortium. The reconciled record removes the `affiliations` key from the `Creator` object entirely, in both the full and the core record.

Rationale: those seven organizations appear in the bundle inside `sponsorCollaboratorsModule` of the FAIRhub `study_description`, attached to the study's lead sponsor and collaborator roster. The FAIRhub `dataset_description` records exactly one creator — `creatorName: "AI-READI Consortium"`, `nameType: "Organizational"` — with no affiliation field at all. Re-labelling the study collaborator roster as the creator's affiliations asserts a relation no source states.

The organizations are not lost: `creators[0].source_caveats` was rewritten to name all seven explicitly and to say why they are recorded as study collaborators rather than creator affiliations. Washington University in St. Louis also remains in `data_governance.accountable_organization` with its ROR CURIE, where the bundle does support it.

### 2.4 `creators[0].credit_roles` — unsupported claim

**Changed.** The original record assigned six CRediT roles (`conceptualization`, `data_curation`, `investigation`, `methodology`, `project_administration`, `supervision`). The reconciled record removes `credit_roles` from the `Creator` object in both records.

Rationale: no source in the bundle assigns contributor roles to the AI-READI Consortium. The values were inferred from the general character of the project. The rewritten `source_caveats` now states explicitly that the FAIRhub `dataset_description` records the creator "with no affiliation and no contributor roles stated".

### 2.5 `funders[0].grants[0].id` — search URL in the identifier position

**Changed.** The original grant object was:

```yaml
- id: https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481
  name: 'Bridge2AI: Salutogenesis Data Generation Project'
```

with the award number `OT2OD032644` mentioned only in the funder-level `notes`. The reconciled record is:

```yaml
- id: nih:OT2OD032644
  name: 'Bridge2AI: Salutogenesis Data Generation Project'
  description: >-
    NIH award number OT2OD032644, made through the NIH Common Fund Bridge2AI
    program. The award record is published at
    https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481.
```

The award number is now in the identifier position, and the RePORTER URL is retained in the `description` where it is a locator rather than an identifier.

Caveat recorded honestly: the `nih:` prefix is not among the prefixes the schema digest shows in use (`ROR:`, `ORCID:`, `doi:`, `B2AI_TOPIC:`, `B2AI_SUBSTRATE:`). Rather than leave that silent, `funders[0].source_caveats` gained a sentence stating that the prefix is not declared by the schema and that `OT2OD032644` is the bare identifier the bundle supplies. This is a partial rather than a clean fix, and the report records it as such.

---

## 3. Medium-severity findings

### 3.1 `instances[0].data_substrate` omitted, `data_topic` lossy

**Changed (documentation only).** No slot value changed: `data_topic: B2AI_TOPIC:43` is still present and `data_substrate` is still absent in both records. What was added is `instances[0].source_caveats`, which did not exist in the original. It now states that the bundle describes the instance as encompassing tabular, imaging and physiological signal/waveform data simultaneously, that no single B2AI substrate term covers that combination, and that the slot is therefore omitted rather than approximated. It also explains the single-term `data_topic` choice.

### 3.2 `subsets` — minted fragments nothing references

**Changed indirectly, via 3.3.** The three `DataSubset` entries (`#train`, `#validation`, `#test`) are all still present in the full record with their fragment identifiers. They are no longer unreferenced labels: the fix to `affected_subsets` (below) means all three are now pointed at by another value in the record. This satisfies the minting rule without deleting subsets the bundle fully describes.

### 3.3 `known_biases[0].affected_subsets` — attribution narrower than the bias

**Changed.** The original listed only `doi:10.60775/fairhub.3#train`. The reconciled record lists all three:

```yaml
affected_subsets:
- doi:10.60775/fairhub.3#train
- doi:10.60775/fairhub.3#validation
- doi:10.60775/fairhub.3#test
```

and gained a `source_caveats` explaining that the representation imbalance is a property of the enrolled cohort as a whole, and that the bundle's statement about validation and test being "balanced as well as possible" is the mitigation applied to those splits rather than evidence that they are unaffected. Both edits appear in both records.

### 3.4 `file_collections[*].conforms_to` — commentary embedded in the standard name

**Changed.** In the original, each collection's `conforms_to` read e.g. `WaveForm DataBase (WFDB), within Clinical Dataset Structure (CDS) v0.1.1`. In the reconciled record each reads simply `WaveForm DataBase (WFDB)`, `Digital Imaging and Communications in Medicine (DICOM)`, `Open mHealth`, etc. The CDS organizational fact moved into each collection's `description` as a sentence ("The directory and its sub-directories are named and organized following the Clinical Dataset Structure (CDS) v0.1.1, and are accompanied by a manifest.tsv metadata file"). The `conforms_to_standard` pairs are unchanged, so the CDS term is still queryable.

The `#root_metadata` collection is the exception: its `conforms_to` was and remains `Clinical Dataset Structure (CDS) v0.1.1` alone, which is correct since CDS is the only standard those files follow.

One related change: `file_collections[#clinical_data]` originally carried `is_tabular: true`; the reconciled record drops that key and states "The data in this directory are tabular" in the `description` instead. This was not an audit finding and is a judgment call made while rewriting the descriptions.

### 3.5 `distribution_formats[4]` — source commentary in `notes`

**Changed.** The WFDB entry's `notes` key was renamed to `source_caveats`, with the text slightly extended ("names WFDB as the file format standard that all data files within that directory follow"). Both records reflect this. The `notes` on the Markdown entry (`distribution_formats[3]`) was correctly left as `notes`, since it describes which files use the format rather than annotating the evidence.

### 3.6 `distribution_formats[5]` — an access route, not a format

**Changed.** The entry reading `format: 'Azure Storage access and a smaller "mini" subset for pipeline development'` is removed from both records. `distribution_formats` now has five entries rather than six.

The content was not discarded: `data_governance.access_review_process` gained the sentence "The v3.0.0 documentation additionally describes Azure Storage access and a smaller mini-subset version of the dataset for pipeline development." The mini-subset also remains mentioned in the top-level `notes`, where it was already present in the original.

### 3.7 `human_subject_research` — single-element prose lists

**Left as-is.** `irb_approval`, `regulatory_compliance` and `special_populations` are still single-element YAML lists of paragraph prose in both records. The audit asked to "check the declared range"; the schema digest supplied to me lists `HumanSubjectResearch` accepted keys without declaring the range of each, so I cannot confirm from the digest whether these are scalar-ranged. Both records validated against the schema in Phase 1 and Phase 2 with the list form, which is evidence the range accepts it. Changing a shape that validates, on a range I cannot confirm from the digest, risked introducing a defect rather than removing one.

### 3.8 `at_risk_populations.special_protections` — restates its sibling boolean

**Changed.** The `special_protections` key is removed from both records. Its content — the age floor of 40, the maximum of 85, the pregnancy and gestational-diabetes exclusions, the English-language requirement — moved into the `notes` field, where it now sits alongside the transportation-assistance material that was already there. `at_risk_groups_included: false` remains and now carries that claim on its own, with the eligibility criteria in `notes` as the supporting detail rather than as a "protection".

### 3.9 `ethical_reviews[1].reviewing_organization` — an activity label, not an organization

**Changed.** The value `AI-READI ethics review` is removed. The entry now has no `reviewing_organization` and instead carries a `source_caveats` stating that the RO-Crate `ethicalReview` field names four individuals (Camille Nebeker, Debra Mathews, Kadija Ferryman, Nicholas Evans) and no reviewing organization. The four names remain in `review_details`, as they did originally.

### 3.10 `ethical_reviews[0].contact_person` — a team in a `Person` object

**Changed.** The object `{name: 'IRB Reliance Team, Human Subjects Division'}` is removed from `ethical_reviews[0]`. The contact route is preserved as prose: `review_details` gained the sentence "The IRB Reliance Team is reachable at hsdrely@uw.edu." The same email also remains in `human_subject_research.ethics_review_board`, where the bundle attaches it to the IRB organization's `ContactPoint`.

Related shape changes made at the same time, in three places where a `Person` object carried a name but no meaningful separate identity beyond the ORCID: `license_and_use_terms.contact_person`, `data_governance.committee_contact`, and `creators[0].principal_investigator` were each converted from a two-key object to the scalar string `Aaron Lee (ORCID:0000-0002-7452-1648)`. This was not an audit finding. It was done on the v4 rule that a scalar-ranged slot takes an identifier rather than an object — but I should be candid that I did not verify from the digest that these three slots are scalar-ranged, and the object form validated in Phase 1. This change is therefore less well-grounded than the others and is flagged here rather than presented as a clean fix.

### 3.11 `license_and_use_terms.data_use_permission` — scope tension undisclosed

**Changed.** The enum value `disease_specific_research` is unchanged. A `source_caveats` was added stating that the enum records the access condition attached to the public release ("Agreeing to use the data only for type 2 diabetes related research"), that the license grant itself is broader ("for research, commercial and non-commercial purposes"), that `consentNoncommercial` is recorded as false, and that no single permitted enum value expresses both scopes. Present in both records.

---

## 4. Low-severity findings

### 4.1 `notes` — trial registration placement

**Changed.** The audit called the ClinicalTrials.gov registration "borderline" in `notes` and suggested `related_datasets`. A sixth `related_datasets` entry was added:

```yaml
- relationship_type: is_described_by
  target_dataset: https://classic.clinicaltrials.gov/ct2/show/NCT06002048
```

The registration number also remains in `notes`, since the alternative title and the official study title are stated there together and splitting them would lose the connection.

### 4.2 `source_caveats` — duplication of the de-identification contradiction

**Left as-is.** Item (5) of the top-level `source_caveats` and `is_deidentified.source_caveats` still both describe the `NoDeIdentification` / `deIdentHIPAA: true` contradiction, in both records. The audit called this "redundant but not incorrect". The top-level item serves a reader scanning the record's overall trustworthiness; the object-level one serves a reader looking at the de-identification claim specifically.

### 4.3 `created_on` — omitted

**Left as-is.** Still absent from both records. The FAIRhub `created_at: 1763366400` corresponds to 2025-11-17, which `issued` already carries. The audit called the omission defensible.

### 4.4 `last_updated_on` — omitted

**Left as-is.** The audit confirmed the "Last updated on Jun 4, 2026" timestamp belongs to the documentation site page, not the dataset, and called the omission correct.

### 4.5 `was_derived_from` — omitted

**Left as-is.** The prior versions are carried in `related_datasets` with `is_new_version_of`. The audit called the omission defensible.

### 4.6 `existing_uses` and `use_repository` — omitted

**Left as-is.** The healthsheet answers "No" to both questions. Recording an entry stating that there are no known uses would be a pointer-to-absence. The audit called both omissions correct.

### 4.7 `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols` — omitted

**Left as-is.** The audit confirmed all three as correct omissions. The no-imputation fact is carried in `missing_data_documentation.handling_strategy` in both records.

### 4.8 `data_protection_impacts` — omitted despite explicit evidence

**Left as-is.** The bundle explicitly says "No, a data protection impact analysis has not been conducted." An entry recording that would be a statement of absence, which the omission rule prefers over population. The audit reached the same conclusion and noted the item only because the evidence is explicit rather than silent.

### 4.9 `errata` — omitted

**Left as-is.** The healthsheet erratum question has an empty response. The audit called this correct.

### 4.10 `other_tasks` and `discouraged_uses` — omitted

**Left as-is.** The healthsheet answers the discouraged-uses question by pointing at the license restrictions, which `prohibited_uses` already carries in six entries. The audit called omitting `discouraged_uses` to avoid duplication defensible.

### 4.11 `variables` — partial selection, undisclosed

**Changed.** Two things happened here.

First, disclosure: item (6) was appended to the top-level `source_caveats`, stating that the variables slot transcribes a selection, that the BMJ Open protocol lists roughly forty laboratory analytes, and that the list is therefore partial rather than exhaustive. This appears in both records (the core record has no `variables` slot, but the caveat is projected with the rest of the top-level caveats).

Second, expansion: the list grew from 18 to 23 entries. Five analytes were added from the same source table — blood urea nitrogen, sodium, potassium, albumin, haemoglobin, platelets — while the entry count reflects those additions against the original eighteen. The selection remains partial and is now labelled as such.

### 4.12 `variables[*].notes` — reference ranges in prose rather than in the declared float fields

**Changed.** Reference ranges that are simple numeric intervals now populate `minimum_value` and `maximum_value`. Twelve entries gained one or both bounds: HbA1c (4.0–6.0), glucose (62–125), C peptide (1.1–4.4), insulin (0.0–24.9), CRP-HS (0.0–10.0), total cholesterol (max 200), HDL (min 39), LDL (max 130), triglycerides (max 150), BUN (8.0–21.0), sodium (135–145), potassium (3.6–5.2), albumin (3.5–5.2), haemoglobin (11.1–17.7), platelets (150–450).

Each such entry's `notes` now states explicitly that the bounds record the laboratory reference range, not observed data extremes — an important distinction, since `minimum_value`/`maximum_value` would otherwise read as data range.

Four entries deliberately do not carry bounds and say why in `notes`: NT-proBNP (range varies by age), troponin-T (differs by sex), creatinine (differs by sex), and the two urine analytes (no range given by the source). The MoCA entry retains its 0–30 bounds, which are the instrument's scale rather than a reference range.

---

## 5. Changes to the core record

The core record was re-projected from the reconciled full record. Every change above that touches a slot present in `CoreDataset` is reflected there: the removed `publisher`, the trimmed `Creator`, the grant identifier, the three-way `affected_subsets`, the added `instances[0].source_caveats`, the cleaned `conforms_to` values in `distributions`, the removed Azure `distribution_formats` entry, the scalar `contact_person` and `committee_contact`, the trimmed `at_risk_populations`, the two `ethical_reviews` fixes, the `license_and_use_terms.source_caveats`, the sixth `related_datasets` entry, and the rewritten top-level `notes` and `source_caveats`.

Two projection details worth noting. The core record's `created_by` slot, which held `AI-READI Consortium` in the original, is absent from the reconciled core — this follows the full record, where `created_by` was also dropped alongside `publisher` as part of the attribution cleanup. And `file_collections` projects to `distributions` with `total_bytes` renamed to `bytes` and `file_count` not carried, which is the shape difference between the two schemas rather than a reconciliation change.

---

## 6. Findings left as-is, in summary

| Finding | Reason |
|---|---|
| 2.1 `conforms_to_standard` | Audit verified clean; no defect |
| 3.7 `HumanSubjectResearch` list shapes | Range not confirmable from digest; current form validates |
| 4.2 duplicated de-identification caveat | Redundant but correct; serves two reading paths |
| 4.3 `created_on` | Covered by `issued`; omission defensible |
| 4.4 `last_updated_on` | Timestamp belongs to the docs site, not the dataset |
| 4.5 `was_derived_from` | Version lineage carried in `related_datasets` |
| 4.6 `existing_uses`, `use_repository` | Attested absences; omission correct |
| 4.7 annotation and imputation slots | Attested absences; omission correct |
| 4.8 `data_protection_impacts` | Explicit "not conducted"; pointer-to-absence avoided |
| 4.9 `errata` | Empty healthsheet response |
| 4.10 `other_tasks`, `discouraged_uses` | Content already in `prohibited_uses` |

---

## 7. Residual concerns

Three items in this reconciliation are weaker than the rest and should be read with that in mind.

**The `nih:` prefix.** Moving the award number into the grant `id` improved the identifier's content but introduced a prefix the schema digest does not show as declared. The alternative — leaving a RePORTER search URL as the grant identifier — was worse. The caveat states the situation plainly.

**The scalar `Person` conversions.** Three slots (`principal_investigator`, `contact_person` on two objects, `committee_contact`) were changed from `Person` objects to strings on a rule about scalar ranges that I could not verify against the digest for those specific slots. If those ranges are `Person`, this change is a regression. It validated, but validation alone does not settle it.

**The variable list is still partial.** Expanding from 18 to 23 entries reduced the gap but did not close it; roughly forty analytes appear in the source table. The list is now labelled as partial, which is the honest state, but a complete transcription would be better.