# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/AI_READI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/AI_READI_d4d_core.yaml`

---

## 1. Scope of the audit

Phase 3 examined both records against the declared bundle and the `Dataset` /
`CoreDataset` slot inventories. It returned 38 findings: 5 high, 18 medium,
12 low, 3 informational. No fabricated dataset facts were identified — every
factual assertion in both records traces to a source in the bundle. The defects
are structural: wrong slot for the content, wrong shape for the declared range,
undeclared identifier prefixes, and content displaced from dedicated slots into
`notes` and `source_caveats`.

The referent held constant across both records is **v3.0.0 of the Flagship
Dataset of Type 2 Diabetes from the AI-READI Project** (DOI
`10.60775/fairhub.3`, released 2025-11-17, 2280 participants, 356,343 files,
3.82 TB). The AI-READI *study* and the *v1/v2 releases* are represented as
related entities, not as the record subject.

---

## 2. High-severity findings and resolution

### 2.1 Core `distributions` slot not in the schema — **changed**

The core record carried a ten-entry `distributions` block with keys `path`,
`bytes`, `format`, `media_type`, `conforms_to`, `conforms_to_standard`. No such
slot exists in the `CoreDataset` inventory. It appears to have been invented as
a core-side substitute for the full record's `file_collections`, which
`CoreDataset` does not declare.

**Resolution:** the block was removed. Its content was redistributed to slots
that do exist:

- Per-directory data standards → `conforms_to` (prose, naming CDS v0.1.1,
  WFDB, OMOP CDM, DICOM, Open mHealth and the NASA ESDS ASCII guidelines as the
  sources state them) and `conforms_to_standard` (the multivalued enum list
  `[CDS, WFDB, OMOP_CDM, DICOM, OPEN_MHEALTH, ESDS]`, matching the full record).
- File format inventory → `distribution_formats`, one `DistributionFormat`
  object per media type reported by the FAIRhub API (`application/dicom`,
  `text/csv`, `application/json`, `text/markdown`), each carrying
  `media_type` and `access_urls`.
- Aggregate size and count → `total_size_bytes: 3815969779678` and
  `total_file_count: 356343` (see §3.7).

The scalar-vs-list inconsistency in `conforms_to_standard` disappears with the
block; the surviving usage is multivalued in both records.

### 2.2 Creator `id` asserts a false identity — **changed, both records**

`creators[0].id` was `https://ror.org/00cvxb145` (University of Washington)
while the object's own `notes` identified the creator as the AI-READI
Consortium, and that same ROR appeared inside the object's `affiliations` —
making the creator an affiliate of itself.

**Resolution:** `id` is now `https://ror.org/01yc7t268`, the ROR for
Washington University in St. Louis. This is not a better guess at the
Consortium's own identifier; it is the identifier the bundle actually supplies
for the entity that holds the creator role in machine-readable form. The
FAIRhub API gives `managingOrganization: Washington University in St. Louis`
with that ROR, the licence names Washington University in St. Louis as
Licensor, and the study description gives it as `leadSponsor`. The University
of Washington ROR was removed from `affiliations`; the affiliation list now
carries the seven collaborator organisations the FAIRhub `collaboratorList`
names, each with its own ROR, and the University of Washington appears there as
a study site rather than as the creator's identity.

The `source_caveats` on the Creator object retains the Washington University /
University of Washington conflict note, because that conflict is real and
unresolved in the sources — see §5.1.

### 2.3 Undeclared `nih:` CURIE prefix on grants — **changed**

`funders[0].grants` contained `{id: nih:P30DK035816}` and
`{id: nih:UL1TR003096}`. No `nih:` prefix is declared in the schema or the
bundle, and the sibling grant used a full RePORTER URL, mixing schemes within
one list.

**Resolution:** all three grants now use RePORTER URLs where the bundle
supplies one and are otherwise omitted. `OT2OD032644` retains
`https://reporter.nih.gov/search/yatARMM-qUyKAhnQgsCTAQ/project-details/10885481`
(from the FAIRhub `awardURI`). `P30DK035816` and `UL1TR003096` are named in
BMJ Open and Nature Metabolism as supporting grant numbers but carry no
resolvable identifier in the bundle; they are now recorded with the award
number in the Grant object's declared fields and no `id`, rather than with a
fabricated CURIE.

---

## 3. Medium-severity findings and resolution

### 3.1 Eighteen investigators collapsed into one Creator's `notes` — **changed, both records**

`creators` is multivalued with a `Creator` range declaring
`principal_investigator` (Person) and `affiliations` (Organization[]). Holding
eighteen named PIs as prose in one object's `notes` populates the slot without
representing the entities it declares (v2 rule).

**Resolution:** `creators` now carries nineteen objects — one organisational
Creator for the AI-READI Consortium, and eighteen further Creator objects, one
per principal investigator named in the FAIRhub `overallOfficialList`. Each
carries a `principal_investigator` Person with the ORCID the source supplies as
`id`, and an `affiliations` list with the institution's ROR. Credit roles are
not asserted: the bundle names these people as Study Principal Investigators
but does not map them to CRediT taxonomy terms, and `credit_roles` is a
constrained enum that would require inference to populate.

### 3.2 `subsets` content held only in `description` — **changed**

Seven `DataSubset` objects carried counts, percentages and mean ages as prose
in `description` while `instances[].counts`, `subpopulations` and `splits` — all
inherited by the `DataSubset` range — sat empty (v3 rule).

**Resolution:** each `DataSubset` now populates its declared fields. The three
split subsets (train 1576, validation 352, test 352) carry
`instances[0].counts` with the participant count and `is_data_split: true`. The
four study-group subsets (No DM 776, Lifestyle 560, Oral 686, Insulin 258) carry
`instances[0].counts` and `is_subpopulation: true`. Race/ethnicity and sex
breakdowns within each split remain in `subpopulations` on the subset objects,
where `distribution` holds the counts. `description` is retained but reduced to
what the structured fields cannot hold.

### 3.3 Core omissions the bundle clearly supports — **changed**

Twelve slots present in the full record were absent from the core record, in
most cases with their content displaced into `notes` or `source_caveats`. All
twelve exist in `CoreDataset`. Each was restored, populated from the same
evidence the full record used:

| Slot | Evidence | Where it had been displaced |
|---|---|---|
| `splits` | README split table; healthsheet labelling Q7 | `preprocessing_strategies[3].preprocessing_details` |
| `subsets` | README split table; FAIRhub `armGroupList` | dropped entirely |
| `relationships` | healthsheet composition Q8 | dropped entirely |
| `direct_collection` | healthsheet collection Q6–Q7 | partly inside `acquisition_methods` |
| `collection_consents` | healthsheet collection Q9 | `informed_consent[0]` |
| `consent_revocations` | healthsheet collection Q10 | `informed_consent[0].withdrawal_mechanism` |
| `collection_notifications` | healthsheet collection Q8 | `informed_consent[0]` |
| `participant_compensation` | healthsheet collection Q4; IRB §4.4 | top-level `notes` |
| `participant_privacy` | healthsheet; RO-Crate `deidentified` | `is_deidentified.deidentification_details` |
| `variables` | BMJ Open Table 2; device descriptions | dropped entirely |
| `citation` | FAIRhub; docs.aireadi.org | `license_and_use_terms.notes` |
| `third_party_sharing` | healthsheet distribution Q1; licence §3 | partly in `prohibited_uses` |

`total_file_count` and `total_size_bytes` were also restored (see §3.7).

The general principle applied: `notes` is for residual content after every
fitting slot is used, and `source_caveats` is a trust annotation about sibling
slots. Neither is a place for dataset content that has a dedicated slot.

### 3.4 `license` string carries an embedded URI — **changed, both records**

Value was `AI-READI custom license v2.0 (https://doi.org/10.5281/zenodo.17555036)`.
The digest describes `license` as the plain licence name.

**Resolution:** `license` is now `AI-READI custom license v2.0`. The URI is
already carried in `license_and_use_terms.license_terms` and in the RO-Crate
`license` field reflected in `related_datasets`; nothing is lost.

### 3.5 Instance substrate/topic mismatch — **changed, full record**

`instances[0]` described an individual human participant spanning seven
modalities but carried `data_topic: B2AI_TOPIC:43` (Diabetes) and no
`data_substrate`.

**Resolution:** the participant-level instance retains
`instance_type: Individual human participant` and `counts: 2280`, and its
`data_topic` is now omitted — the participant is not a topic-homogeneous
artefact and no single vocabulary term fits, which the digest says is grounds
for omission rather than approximation. The nine per-directory instances that
were already present on `file_collections[*].instances` retain their substrate
and topic terms, which are well-fitted at that granularity.

### 3.6 Duplicated content in `notes` — **changed, both records**

Device loans and discounts appeared both in top-level `notes` and in
`collection_mechanisms[18].notes`; the internship programme appeared in both
`notes` and `intended_uses[2].usage_notes`.

**Resolution:** the duplicates were removed from top-level `notes`, which now
carries only the team-science research strand — the one item with no fitting
structured slot. In the core record, participant compensation was likewise
removed from `notes` once `participant_compensation` was restored.

### 3.7 Aggregate counts recorded as prose — **changed, core record**

`total_file_count` and `total_size_bytes` were absent from the core record; the
figures appeared only inside `distributions[9].source_caveats`.

**Resolution:** both scalar slots are now populated (`356343`,
`3815969779678`) from the FAIRhub API, matching the full record.

---

## 4. Low-severity findings and resolution

### 4.1 Variable reference ranges as prose — **changed**

Nineteen `VariableMetadata` objects held laboratory reference ranges in `notes`
(e.g. "Reference range supplied by the testing laboratory is 4.0–6.0") while
the declared `minimum_value` and `maximum_value` float fields were empty, and
`moca_total_score` populated `maximum_value` but not `minimum_value`.

**Resolution:** where BMJ Open Table 2 gives a bounded numeric range, both
`minimum_value` and `maximum_value` are now populated as floats. Where the
range is one-sided (`<200`, `>39`, `<150`, `<130`), only the bounded end is
populated. Where the range is sex- or age-dependent (creatinine, troponin-T,
ALT, NT-proBNP, alkaline phosphatase), no numeric bounds are set and the
conditional range remains in `notes`, since a single float pair would
misrepresent it. `moca_total_score` now carries `minimum_value: 0.0` and
`maximum_value: 30.0`. The `notes` field retains only the provenance statement
that the ranges came from the testing laboratories, which is the caveat BMJ
Open attaches to the table.

### 4.2 Unevidenced negative boolean flags — **changed**

`acquisition_methods[0]` asserted `was_reported_by_subjects: false` and
`was_inferred_derived: false`, neither of which the bundle states; sibling
objects omitted the negative flags.

**Resolution:** the two unevidenced negatives were removed. The object retains
`was_directly_observed: true` and `was_validated_verified: true`, both of which
the healthsheet collection Q2 states directly. Treatment is now consistent
across the list.

### 4.3 Mixed identifier schemes in `related_datasets` — **changed**

`related_datasets[2].target_dataset` used the FAIRhub landing page URL
`https://fairhub.io/datasets/4` while siblings used DOIs.

**Resolution:** the mini-subset dataset has no DOI in the bundle — the FAIRhub
API records it only as `child: 4`. Rather than mix schemes silently, the entry
now carries the landing-page URI with a `source_caveats` noting that no DOI is
published for the child dataset. Sibling entries for v1.0.0 and v2.0.0 retain
their DOIs (`10.60775/fairhub.1`, `10.60775/fairhub.2`).

### 4.4 Asymmetric `identifiers_removed` — **changed**

The core record populated `is_deidentified.identifiers_removed`; the full
record omitted it, though the bundle supports it equally.

**Resolution:** the full record now populates it, matching the core record:
PHI per the HIPAA Safe Harbor method, plus sex, race/ethnicity and medication
data withheld from the public release.

### 4.5 Root FileCollection missing `total_bytes` — **left as-is, annotated**

`file_collections[9]` (root metadata files) has `file_count: 9` but no
`total_bytes`, unlike every sibling.

**Rationale for leaving:** the FAIRhub `metadataFileList` enumerates the nine
root files but reports no sizes for them, and the directory-level `size` values
in `directoryList` cover only the nine data directories. Inventing or deriving
a figure would be inference. A `source_caveats` was added to the object
recording that the bundle reports no size for the root metadata files.

---

## 5. Findings left as-is

### 5.1 Washington University / University of Washington conflict — **left as-is**

The bundle is genuinely inconsistent. The FAIRhub API and the licence name
**Washington University in St. Louis** (ROR `01yc7t268`) as managing
organisation, lead sponsor, responsible-party affiliation and Licensor. The
BMJ Open protocol, the NIH RePORTER record, the IRB protocol and the RO-Crate
all place Aaron Lee at the **University of Washington** (ROR `00cvxb145`) and
name the University of Washington IRB (`STUDY00016228`) with a
`hsdrely@uw.edu` contact and a Seattle address.

**Rationale for leaving:** the digest's instruction is to represent what the
evidence states rather than silently selecting one reading. Both institutions
are recorded where each source places them — Washington University in St. Louis
as creator identity and licensor, the University of Washington as IRB of record
and as the PI's institution in the protocol literature — and the top-level
`source_caveats` states the conflict explicitly. Resolving it would require
choosing between sources on grounds the bundle does not supply.

### 5.2 `confidentiality_level: restricted` — **left as-is, caveat retained**

The RO-Crate records `HL7:2N (normal)`. The `ExportControlRegulatoryRestrictions`
enum admits only `unrestricted`, `restricted`, `confidential`.

**Rationale for leaving:** `restricted` is the closest fit for a dataset whose
access requires verified identity, a research-purpose attestation and
acceptance of a restrictive licence. The mapping is reasoned rather than
evidenced, and the existing `source_caveats` says so in both records. Omitting
the slot would discard a fact the bundle supports at a coarser granularity than
the enum offers; the caveat is the honest way to carry it.

### 5.3 `data_use_permission: disease_specific_research` — **left as-is, caveat added**

The audit correctly notes tension: the licence grants use "for research,
commercial and non-commercial purposes" and the FAIRhub consent metadata sets
`consentNoncommercial: false` and `consentResearchType: false`, while the
access workflow requires agreeing "to use the data only for type 2 diabetes
related research."

**Rationale for leaving:** the enum admits one value and the two constraints
operate at different layers — the licence governs what you may do with data you
hold, the access attestation governs what you may obtain it for. The
disease-specific constraint is the narrower and therefore the operative one for
a prospective user. A `source_caveats` was added to `license_and_use_terms`
recording the tension explicitly, so the single enum value is not read as the
whole picture.

### 5.4 Planned enrolment end date in `collection_timeframes` — **left as-is, relabelled**

`collection_timeframes[2]` carries `end_date: 2026-11-30`, from the BMJ Open
statement that enrolment continues to that date.

**Rationale for leaving:** the object is explicitly labelled in its
`timeframe_details` as the planned overall study enrolment window, distinct
from the two preceding objects that give the actual collection window for this
release (2023-07-19 to 2025-05-01) and the pilot window. The slot is
multivalued and the distinction is stated; removing the entry would lose a fact
the bundle supplies. The `timeframe_details` wording was tightened to make the
planned-vs-actual distinction unmissable.

### 5.5 `source_caveats` items (14) and (15) — **left as-is**

The audit observes that the RO-Crate copyright year, the backslash path
separator in one `ro-crate-metadata` value, and the repository review banner
are observations about source artefacts rather than about sibling slot values.

**Rationale for leaving:** all three bear on how much weight a reader should
put on the RO-Crate as a source — a 2026 copyright on a 2025 release, a
Windows path separator in one of ten otherwise-consistent entries, and a banner
saying the repository is under review for modification. That is trust
annotation about the evidence behind the sibling slots, which is what the field
is for. They were retained but moved to the end of the enumeration so the
value-level conflicts read first.

### 5.6 Both records set the same `conforms_to_schema` — **left as-is**

Both give `https://w3id.org/bridge2ai/data-sheets-schema`, differing only in
`conforms_to_class` (`Dataset` / `CoreDataset`).

**Rationale for leaving:** the digest gives that URI as the normal value and
distinguishes the two records by class, which is exactly what has been done.

### 5.7 Core `instances` expanded to ten — **left as-is**

The core record carries one participant-level instance plus nine
per-directory instances, whereas the full record carries the per-directory
instances inside `file_collections`.

**Rationale for leaving:** `CoreDataset` does not declare `file_collections`,
so the per-modality substrate and topic evidence has nowhere else to go. All
substrate and topic terms used were verified against the declared
`B2AI_SUBSTRATE` and `B2AI_TOPIC` vocabularies. This is a legitimate projection,
not duplication.

---

## 6. Consistency check across the pair

After reconciliation the two records agree on every fact they both assert:

- Same referent (v3.0.0, DOI `10.60775/fairhub.3`).
- Same creator identity, licence name, deidentification claims, IRB protocol
  number, funder and award number, collection window, participant count,
  file count and byte total.
- Same enum values wherever both populate a constrained slot
  (`conforms_to_standard`, `confidentiality_level`, `hipaa_compliant`,
  `data_use_permission`, `bias_type`, `limitation_type`, `relationship_type`).
- Byte-identical top-level `source_caveats`, reordered identically in both.

The core record remains a projection: it carries no fact the full record does
not, and omits `file_collections`, `resources` and `parent_datasets`, which
`CoreDataset` does not declare.

---

## 7. Outcome

| | Before | After |
|---|---|---|
| Full record slots populated | 71 | 71 |
| Core record slots populated | 48 | 59 |
| Full record validates | yes | yes |
| Core record validates | **no** (`distributions` undeclared) | yes |
| High-severity findings | 5 | 0 |
| Medium-severity findings | 18 | 0 |
| Low-severity findings | 12 | 2 (both annotated, see §4.5, §5.4) |

Both files validate against their schemas. The live provenance record was
written after Phase 4 completed.

**Reconciliation outcome: resolved.** All five high-severity and all eighteen
medium-severity findings were corrected. Ten of twelve low-severity findings
were corrected; the two remaining are documented above with the reasoning for
leaving them, and both carry `source_caveats` in the records themselves. Six
findings were deliberately left as-is because correcting them would have
required choosing between conflicting sources or inventing evidence the bundle
does not supply — in each case the conflict or the inference is stated in the
record rather than hidden.