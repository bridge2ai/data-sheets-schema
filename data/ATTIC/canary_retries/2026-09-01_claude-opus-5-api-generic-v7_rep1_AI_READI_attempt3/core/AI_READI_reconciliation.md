# Reconciliation Report — AI_READI

**Version label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Records:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Phase:** 4 (strict reconciliation of Phase 3 audit findings)

---

## 1. Summary

The Phase 3 audit returned 50 findings against the full record. Of these, 5 were classed high-severity defects, 5 were secondary substantive issues, and a recurring shape problem affected seven multivalued slots. The remainder were confirmations that a check had been performed and passed, or judgment calls recorded for transparency.

Twenty-two findings resulted in a change to the full record; the corresponding change was propagated to the core record wherever the affected slot is projected into it. The remaining findings were left as-is, in most cases because the audit itself concluded the original handling was correct.

Slot count changed as follows: the full record gained `discouraged_uses`, `data_protection_impacts`, `extension_mechanism`, and a tenth `file_collections` entry; it lost the top-level `is_tabular` slot and two nested boolean flags (`is_deidentified.identifiable_elements_present`, `at_risk_populations.at_risk_groups_included`, `regulatory_restrictions.confidentiality_level`). The core record mirrors each of these, with the additional note that `is_tabular: false` was present in the original core record and is absent from the reconciled one.

---

## 2. Changes made

### 2.1 High-severity findings

**`creators[0]` — organizational creator demoted into its own affiliation slot**

The audit found that `affiliations[0]` carried only `name: AI-READI Consortium`, which is the creator itself as FAIRhub records it (`creatorName: AI-READI Consortium`, `nameType: Organizational`), not an affiliation of that creator, leaving the Creator with no name-bearing field populated.

The reconciled record keeps the organization in `affiliations` but adds a `description` making explicit that this is the organizational creator of record and citing both FAIRhub and the RO-Crate for it. The `source_caveats` was rewritten and substantially expanded: it now states that the AI-READI Consortium "is named here as the creating organization", and additionally addresses the second finding about this slot (see below). The `principal_investigator` value changed shape — see §2.5.

**`data_governance.committee_name` — composed a name no source uses**

The original read `AI-READI Data Access Committee`, a name the audit found neither source states: the BMJ protocol says "Data Access Committee" and the RO-Crate says "AI-READI Consortium".

Changed to `Data Access Committee` — the tier-3 protocol's wording verbatim. The `source_caveats` was rewritten to say the record "reproduces both rather than composing a single name", to attribute "Data Access Committee" explicitly to the BMJ Open protocol as used verbatim, and to note that the RO-Crate's `dataGovernanceCommittee` value names the consortium as a whole rather than a named access committee.

**`is_deidentified.identifiable_elements_present` — contradicted the tier-1 flags it cited**

The audit found `false` asserted against FAIRhub's `deIdentDirect: true` and `deIdentHIPAA: true`, with the caveat not naming those flags.

The boolean was **removed**. The `deidentification_details` prose now enumerates the FAIRhub flag values individually (`deIdentDirect true, deIdentHIPAA true, deIdentDates false, deIdentNonarr false and deIdentKAnon false`) and states that the RO-Crate records the dataset as deidentified. The `source_caveats` now opens by stating the flag "is left unset because the tier-1 sources cannot settle it", names the conflicting flags, and records that the two tier-1 sources are of equal rank so the ranking cannot decide.

**`extension_mechanism` — supported omission**

The audit noted the healthsheet answers the extension question with a quotable "No, currently there is no mechanism". The slot was **added** to both records, with `extension_details` recording that there is no mechanism outside the project team and attributing the statement to the healthsheet question it answers.

**`instances[0].data_substrate` — supported omission**

`data_substrate` was **added** with `B2AI_SUBSTRATE:11` (DICOM). A new `source_caveats` on `instances[0]` explains the choice: the four retinal imaging datatypes account for the great majority of files and bytes, and the bundle equally attests comma-separated values, JSON, tab-separated values, waveform data and time-series data. The same caveat covers the `data_topic` single-value finding (§3).

### 2.2 Secondary substantive findings

**`acquisition_methods[0].was_inferred_derived` — `false` overstated**

Changed from `false` to `true`. The `acquisition_details` gained a closing sentence enumerating the derived values the audit identified: BMI and waist-hip ratio calculated from measurements, LDL cholesterol / total globulin / A/G ratio marked calculated in the laboratory table, the Mars log CS score computed from the error count, and the Garmin sleep-phase and stress indices as device-derived.

Correspondingly, four `variables` entries gained a `derivation` field (`sleep`, `stress`, `contrast_sensitivity_log_cs`) and three new variables were added carrying `derivation` (`body_mass_index`, `waist_hip_ratio`, `ldl_cholesterol`), so that the boolean is evidenced by the variable list rather than by prose alone.

**`regulatory_restrictions.confidentiality_level` — enum was the record's own mapping**

The audit found `restricted` was this record's mapping of the source's "HL7:2N (normal)" onto a three-term scale, not a transcribed term. The slot was **removed**; the HL7 string remains verbatim in `other_compliance`, and a new `source_caveats` states that the term is omitted because mapping it "would be an inference of this record rather than a transcription".

**`sampling_strategies[0].is_sample` — caveat overstated a conflict**

The audit found the "all possible instances" statement and the "Non-Probability Sample" statement compatible: a census of the enrolled cohort and a non-probability draw from the study base are simultaneously true. `is_sample: true` was **added**, and the `source_caveats` rewritten to say the two statements "are compatible" rather than reproducing an unresolved conflict.

**`file_collections` — sums fall short of declared totals**

The audit computed a 9-file and 420,614-byte shortfall between the nine directory entries and the declared totals, attributable to the nine root-level metadata files. A tenth `FileCollection` (`doi:10.60775/fairhub.3#root_metadata`, `collection_type: metadata`, `file_count: 9`) was **added**, listing the nine files the bundle names. `total_bytes` is omitted on it because the bundle gives no size for them; its `source_caveats` records both arithmetic gaps and their attribution. The top-level `source_caveats` also now records both sums explicitly.

**`at_risk_populations.at_risk_groups_included` — generalized past the criteria**

The audit found `false` sound for minors, pregnant women and neonates but unsupported for prisoners, since the IRB form's prisoner questions are unanswered template text. The boolean was **removed**. `special_protections` was split from one concatenated element into three, and a new `source_caveats` records that the criteria settle the question for four groups but the bundle makes no statement about prisoners.

**`is_tabular` — a boolean cannot carry a mixed-modality dataset**

The audit found `false` lossy against the bundle's own statement that the release "encompass[es] tabular data, imaging data, and physiological signal/waveform data", and suggested omission. The slot was **removed from both records**, with the reason recorded in the top-level `source_caveats`.

### 2.3 Multivalued slots collapsed into single elements

The audit identified seven slots where distinct entities were concatenated into one list element. Six were split:

| Slot | Before | After |
|---|---|---|
| `human_subject_research.regulatory_compliance` | 1 element | 7 elements |
| `human_subject_research.special_populations` | 1 element | 3 elements |
| `at_risk_populations.special_protections` | 1 element | 3 elements |
| `ip_restrictions.restrictions` | 1 element | 4 elements |
| `data_governance.stewardship_roles` | 1 element | 3 elements |
| `distribution_dates` | 1 object, 1 date-string | 3 objects, one per release |
| `external_resources` | 1 object, 5 resources | 5 objects, one per resource |
| `version_access.versions_available` | 1 element | 3 elements, one per version |

The `external_resources` split also allowed the audit's separate finding about `archival` and `future_guarantees` to be partly addressed: `archival: false` is now set on the documentation entry, and the self-containment statement moved into that entry's `notes` with the CC-BY licence statement in its `restrictions`.

`version_access.version_details` lost the sentence about version 2.0.0's size and accessibility, which moved into the corresponding `versions_available` element.

### 2.4 Additional slots populated

- **`discouraged_uses`** — added. The audit recorded the omission as defensible but noted a reader may expect the slot. It now carries a `discouragement_details` recording the healthsheet's answer (pointing to the licence) and stating explicitly that the specific restrictions are recorded under `prohibited_uses`.
- **`data_protection_impacts`** — added. The audit called the omission borderline, since the bundle makes a positive statement that no DPIA was conducted. The slot now carries that statement.
- **`informed_consent[0].withdrawal_mechanism`** — added, restating the withdrawal terms already carried in `consent_revocations`.
- **`ethical_reviews`** — the Community Advisory Board was split out of the second entry into a third entry with its own `reviewing_organization`.
- **`participant_compensation[0].compensation_rationale`** — added.
- **`variables[moca_total_score]`** — `minimum_value: 0.0` **removed** (the audit found it inferred, not stated); `quality_notes` added, carrying the score thresholds and the caveats the bundle states about training, education and mental health.

### 2.5 Range corrections

Two nested values were changed from objects to scalars:

- `creators[0].principal_investigator` — from `{id: ORCID:..., name: Aaron Y. Lee}` to the string `Aaron Y. Lee (ORCID:0000-0002-7452-1648)`.
- `data_governance.committee_contact` — **added** as the string `Aaron Lee (ORCID:0000-0002-7452-1648), contact@aireadi.org`, addressing the audit's finding that the contact detail was buried in `stewardship_roles` prose.

`data_governance.accountable_organization` retains its object form with `ROR:01yc7t268`, unchanged.

### 2.6 Cosmetic

- `publisher` — trailing slash removed (`https://fairhub.io/` → `https://fairhub.io`), following the audit's suggestion. The value remains a URL rather than a CURIE, since the bundle supplies no registry identifier for FAIRhub.
- `file_collections[*].description` — each of the nine datatype entries gained the per-directory standards prose from the bundle ("All the data files within this directory follow the format specified in…"), which the audit noted was being dropped because `FileCollection` declares no `conforms_to` companion slot.

### 2.7 Findings addressed by expanded caveats rather than value changes

- **`creators` multivalued collapse** — the audit found one Creator object where the bundle lists sixteen Study Principal Investigators. The single Creator was retained as the organizational creator of record, but the `source_caveats` now states that Aaron Y. Lee "is nonetheless one of sixteen individuals the same FAIRhub record lists with the role 'Study Principal Investigator', so this slot should be read as naming the study's responsible-party PI rather than a sole dataset creator."
- **`subpopulations` vs the healthsheet's "No"** — a `source_caveats` was added to each of the three entries, explaining that the healthsheet's blanket "No" concerns demographic attributes withheld from the public release, and (for the diabetes entry) that diabetes status is a released study-group attribute, so `subpopulation_elements_present: true` there does not contradict it.
- **`collection_timeframes[0]`** — the caveat now names the one-day offset explicitly ("enrolment began on 18 July 2023, one day earlier") rather than framing the disagreement only in terms of the end date.
- **`license_and_use_terms`** — the caveat now opens by distinguishing the access condition (which `disease_specific_research` records) from the broader licence grant, citing `consentNoncommercial: false` and `consentResearchType: false`, before turning to the licence-name conflict it already covered.
- **`file_collections[*].id` minting tension** — the audit recorded an unresolvable conflict between the schema's required `id` and the v6 minting rule. The fragments were kept, since `FileCollection.id` is required per the schema digest, and the tension is now recorded in the top-level `source_caveats`.
- **`funders[2]` (Microsoft AI for Good Lab)** — the audit found this an acknowledgement of in-kind cloud support rather than a funding mechanism, and suggested moving it to `notes`. The entry was **removed** from `funders` (reducing it from three to two) and the acknowledgement moved into `notes`, where it now sits alongside the device-manufacturer in-kind paragraph and is explicitly characterized as "in-kind infrastructure support rather than a funding award".
- **`notes` competing-interests summary** — the audit accepted the compression but noted the bundle lists relationships individually. The sentence now adds "which list those relationships individually", pointing the reader to the source.

### 2.8 Instance-level missing information

`instances[0].missing_information` was **added**, carrying the missing-modality statement the audit found was present at the top level but absent from the instance-level slot declared for it. The top-level `missing_data_documentation` is unchanged, so the fact is now carried in both places.

---

## 3. Findings left as-is

The following findings produced no change to either record.

**Checks that passed.** The audit verified and confirmed: the `conforms_to_standard` enum at the top level (all seven terms valid); the split-table arithmetic at every level (race/ethnicity, sex and diabetes counts all sum correctly to 1576/352/352/2280); `total_size_bytes` against the API `size` and `total_file_count` against `fileCount`; `doi` as a bare DOI matching the anchored pattern, correctly contrasted with the CURIE form in `id` and `latest_version_doi`; `language: en`; `compression` correctly omitted; `errata` correctly omitted given the empty healthsheet response; `was_derived_from` correctly omitted in favour of the `related_datasets` construction; and `created_on` / `last_updated_on` / `modified_by` correctly omitted, with the docs-site edit metadata correctly excluded as belonging to the documentation rather than the dataset. None required action.

**Omissions the audit endorsed.** `existing_uses` and `use_repository` (the healthsheet answers "No" to both, so there is nothing to list); `annotation_analyses`, `labeling_strategies` and `machine_annotation_tools` (no annotation process exists; the negative is carried by `instances[0].label: false`); `other_tasks` (the "hypothesis agnostic" framing names no specific task).

**`related_datasets[2..5].target_dataset` mixed identifier forms.** The audit recorded that entries 2–3 carry bare URLs while the rest carry `doi:` CURIEs, and concluded the mixture is inherent to the source: the bundle's `relatedIdentifier` entries for the two documentation sites are typed `URL`. No repair was made; the records are identical here.

**`file_collections[*].conforms_to_standard` enum validity.** Confirmed conforming. The associated loss of per-directory standards prose *was* addressed — see §2.6.

**`variables[*].is_sensitive`.** Left unpopulated. The audit found the omission defensible since none of the listed variables are themselves controlled-access, so `false` would be uniform and uninformative.

**`instances[0].data_topic` single value.** No value change; the forced single choice is now explained in the new `instances[0].source_caveats` (§2.1).

**`participant_compensation[0].compensation_amount`.** `USD 200` retained; the audit found it faithful in substance. The `notes` gained the IRB protocol's statement that the amount may change in future years.

**Top-level `source_caveats` quality.** The audit found this slot well constructed and used as the guard intends. Its four original conflicts (acronym expansion, sponsor/awardee, enrollment target, year-labeling wobble) are unchanged; four new sentences were appended covering `is_tabular`, the minting tension, and the two arithmetic shortfalls.

**`license` string vs "Health Data License".** The audit noted the conflict is documented in `license_and_use_terms.source_caveats` but not on the `license` slot itself. No change: `license` is a plain string with no caveat slot of its own, and the conflict remains recorded on the structured slot where the licence is described.

---

## 4. Referent

The record's referent is unchanged: version 3.0.0 of the *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, identified by `doi:10.60775/fairhub.3`, as distributed on FAIRhub on 17 November 2025. Earlier versions are represented through `related_datasets` (`is_new_version_of`) and `version_access.versions_available`, not as the subject of the record. Both records hold to this consistently.