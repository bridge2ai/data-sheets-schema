# AI-READI D4D Reconciliation Report

**Version label:** `2026-08-19_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Scope and method

The Phase 3 audit returned 52 findings across both records, ranging from schema-shape defects to
placement and spelling issues. Each finding was assessed against the declared input bundle and the
schema digest. Where the finding identified a defect the evidence supports fixing, the record was
changed. Where the finding was descriptive, a false positive, or where fixing it would have
required a fact the bundle does not supply, the record was left as-is and the reason is recorded
below.

No finding was resolved by consulting any prior D4D record, and no new dataset fact was introduced
that the bundle does not state.

---

## 2. Findings acted on

### 2.1 Identifier shape — `uriorcurie` slots holding bare email addresses

**Audit findings:** high severity, `ethical_reviews[0].contact_person.id`,
`data_governance.committee_contact`, `license_and_use_terms.contact_person`,
`regulatory_restrictions.governance_committee_contact`.

Four `Person` objects carried bare email addresses in an `id` slot whose declared range is
`uriorcurie`. Three of them bound the shared project mailbox `contact@aireadi.org` as the identity
of a named individual, Aaron Y. Lee, for whom the bundle supplies an ORCID.

**Changed in both records.** The three Aaron Y. Lee contacts now carry
`id: https://orcid.org/0000-0002-7452-1648`, the identifier the FAIRhub `study_description`
attests for that person, with the mailbox demoted to prose in each object's `description`
("Central study contact, reachable at contact@aireadi.org"). The IRB reliance contact, which names
a team rather than an individual and for which the bundle supplies only an email, now carries
`id: mailto:hsdrely@uw.edu` — a well-formed URI rather than a bare address.

This removes the false identity claim the audit flagged: a shared organizational mailbox no longer
stands as the identifier of a named person.

### 2.2 Grant identifiers as bare award numbers

**Audit finding:** medium severity, `funders[1].grants[0].id`, `funders[2].grants[0].id`.

`P30DK035816` and `UL1TR003096` were used directly as `uriorcurie` values.

**Changed in both records.** Both now carry a resolvable RePORTER search URL constructed from the
stated award number, with the raw award number preserved in the object's `description`
("Award number as stated: P30DK035816") and a `notes` entry making the construction explicit: "No
resolvable award-specific URL is given in the bundle for this grant; the identifier above is a
search reference constructed from the stated award number." The award numbers themselves remain
exactly as the BMJ Open and Nature Metabolism sources state them.

### 2.3 `is_deidentified.identifiable_elements_present` contradicting the controlled tier

**Audit finding:** high severity — the flag was `false` while the record's own
`sensitive_elements` and `subsets` describe a controlled tier containing 5-digit zip codes,
genetic sequencing data, race/ethnicity and motor vehicle records.

**Changed in both records.** The flag is now `true`, on the reasoning that the record's `id`
denotes the whole dataset including the controlled tier. `method`, `identifiers_removed` and
`deidentification_details` were rewritten to scope their claims explicitly to the public tier and
to state the reasoning for the flag: "The identifiable_elements_present flag above is set true
because the dataset as a whole includes the controlled access subset … for the public subset alone
the corresponding value would be false."

### 2.4 `subpopulations.subpopulation_elements_present` contradicting the tier-1 healthsheet

**Audit finding:** medium severity — the flag was `true` while the object's own `notes` recorded
that the tier-1 healthsheet answers "No".

**Changed in both records.** The flag is now `false`, following the tier-1 answer. `identification`
was reworded to describe the cohort stratification while stating plainly that "the public release
carries no per-instance subpopulation labels", and `distribution` is now prefaced "Aggregate counts
published in the dataset README recommended-split table", making clear that the numbers describe
the cohort rather than released labels. The counts themselves are unchanged.

### 2.5 `regulatory_restrictions.hipaa_compliant` asserted without evidence

**Audit finding:** medium severity — no source asserts HIPAA compliance as a status.

**Changed in both records.** The value moves from `compliant` to `not_applicable`, with the
reasoning added to `source_caveats`: the FAIRhub metadata states only that the team checked no
HIPAA-identifiable data were present, and the Nature comment states the public set is PHI-stripped
via Safe Harbor — so the released data are not PHI and HIPAA does not attach to them.

`confidentiality_level` was **left at `restricted`** (see §3.1).

### 2.6 Absence-recording slots

**Audit finding:** low severity, seven slots populated with statements that something does not
exist: `existing_uses`, `errata`, `imputation_protocols`, `annotation_analyses`,
`labeling_strategies`, `data_protection_impacts`, `use_repository`, plus
`machine_annotation_tools`.

**Partially changed.**

Removed from the **full** record: `existing_uses`, `use_repository`, `imputation_protocols`,
`annotation_analyses`, `machine_annotation_tools`, `errata`. Removed from the **core** record:
`existing_uses`, `use_repository`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `data_protection_impacts`, `errata`.

Retained in both: `labeling_strategies`, whose single object states affirmatively *why* no labeling
was performed (hypothesis-agnostic design) rather than merely recording absence — this answers the
field. Retained in the full record: `data_protection_impacts`, which records a specific
healthsheet answer.

The audit separately flagged `machine_annotation_tools` as slot misuse — the OMOP CDM Data Quality
Dashboard is a quality-checking tool, not an annotation tool, and belongs under
`cleaning_strategies`. Acted on: a new `cleaning_strategies` entry now carries the DQD, with the
tool recorded structurally in `used_software` (`id: https://ohdsi.github.io/DataQualityDashboard/`)
rather than as a bare string.

### 2.7 Collapsed multivalued slots

**Audit findings:** low to medium severity across `human_subject_research.irb_approval`,
`regulatory_compliance`, `special_populations`, `ip_restrictions.restrictions`,
`regulatory_restrictions.regulatory_restrictions`, `data_governance.stewardship_roles`,
`version_access.versions_available`, `distribution_dates`, `at_risk_populations.special_protections`,
`known_biases[2].affected_subsets`.

**Changed in both records.** Every one of these single-element lists carrying several distinct
facts was split into one entry per fact:

- `irb_approval` → 3 entries (initial approval; reliance agreements; renewal requirement)
- `regulatory_compliance` → 5 entries (FDA status; review status; DMC status; GDS obligation;
  NCT identifier)
- `special_populations` → 4 entries
- `special_protections` → 4 entries
- `ip_restrictions.restrictions` → 4 entries
- `regulatory_restrictions.regulatory_restrictions` → 3 entries; the data-storage constraint
  moved here from `other_compliance` where it was appended as trailing prose
- `stewardship_roles` → 4 entries
- `versions_available` → 4 entries (one per version, plus the documentation-versioning note)
- `distribution_dates` → 4 objects (one per release, plus the cadence note carrying the
  `source_caveats`)
- `known_biases` representation-bias entry → split into three separate `DatasetBias` objects, one
  each for Black, Hispanic and Asian participants, each with a single-group `affected_subsets` and
  its own mitigation strategy, replacing the one object whose `affected_subsets` held the string
  "Black, Hispanic and Asian participants"

### 2.8 `acquisition_methods[3]` conflating recruitment with acquisition

**Audit finding:** medium severity — the EHR ICD-10 screening entry set
`was_inferred_derived: true`, but no released instance data derive from that screening; it is a
recruitment mechanism.

**Changed in both records.** The fourth `acquisition_methods` object was removed. The same content
now appears as a `collection_mechanisms` entry, explicitly qualified: "This mechanism served
recruitment rather than instance data acquisition; no released instance data derive from it." The
full record retains the EHR screening in `direct_collection` (`is_direct: false`) and in
`raw_data_sources`, where it belongs.

### 2.9 `data_substrate` omitted despite support

**Audit finding:** medium severity.

**Changed in both records.** `instances[0].data_substrate` is now `B2AI_SUBSTRATE:11` (DICOM),
which covers the largest share of the release by volume. Because the slot is single-valued and the
release spans many substrates, a note records the substrates the slot cannot express: waveform
data, CSV, retinal images, FLIO/OCT/OCTA data, glucose monitoring, heart rate, physical activity,
sleep, stress, respiratory rate, oxygen saturation and questionnaire responses.

### 2.10 `RO_CRATE` missing from `conforms_to_standard`

**Audit finding:** noted as a supported omission.

**Changed in both records.** `RO_CRATE` added to the enum list, and `conforms_to` extended with
"RO-Crate 1.2-DRAFT for the packaging metadata", matching the `conformsTo` declaration in the
RO-Crate source.

### 2.11 `distribution_formats` containing an access route

**Audit finding:** medium severity — `format: 'Cloud object storage access'` is not a format.

**Changed in both records.** That entry was removed. The core record gained
`download_url: https://fairhub.io/datasets/3`, and the Azure access route is described in
`data_governance.access_review_process` alongside the other access conditions. The remaining six
format entries each note whether they appear in the FAIRhub `format` array or are evidenced only
in the structure description.

### 2.12 `created_on` duplicating `issued`

**Audit finding:** medium severity — the value conveyed no distinct information.

**Changed in both records.** `created_on` removed; `source_caveats` now states: "No creation date
distinct from the publication date of 2025-11-17 is stated for this version in any source, so
created_on is omitted."

### 2.13 `was_derived_from` as a composite prose string

**Audit finding:** medium severity — the value bundled two identifiers and a parenthetical, and a
study is not a resource in the provenance sense.

**Changed in both records.** The slot was removed. The NCT identifier is retained in
`human_subject_research.regulatory_compliance` and the IRB protocol number in `irb_approval` and
`ethical_reviews`, where each answers the field it belongs to.

### 2.14 Source-commentary in a descriptive field

**Audit finding:** high severity — `creators[0].principal_investigator.description` embedded
commentary about which source gives which affiliation.

**Changed in both records.** The `description` is now purely descriptive ("Study Principal
Investigator, MD, Associate Professor, and responsible party for the study"), and the affiliation
disagreement moved to `creators[0].source_caveats`, which now records that the two tier-1 sources
disagree and that neither outranks the other.

### 2.15 IRB protocol internal inconsistency

**Audit finding:** medium severity — the top-level caveat reported a 4000-vs-4600 disagreement
without noting that the tier-2 IRB protocol contradicts itself.

**Changed in both records.** The caveat now states: "The tier-2 IRB protocol is internally
inconsistent, stating a target of 4600 participants in its participants section (question 2.1)
while its objectives section (question 1.5) describes collecting 'a cross-sectional dataset of
4,000 people'."

### 2.16 `file_collections[9]` missing `file_count`

**Audit finding:** low severity.

**Changed in the full record.** The root-metadata collection now carries `file_count: 9`, matching
the nine named files. `path` and `total_bytes` remain omitted: the bundle names the files but gives
neither a directory path (they sit at the dataset root) nor a byte total for them.

### 2.17 Redundant `conforms_to` prose in `file_collections`

**Audit finding:** medium severity, noted as redundant rather than wrong.

**Changed in the full record.** Each `file_collections[*].conforms_to` now names the file-format
standard alone (e.g. "WaveForm DataBase (WFDB)"); the CDS organizational statement moved into each
collection's `description`, and `conforms_to_standard` continues to carry both terms.

### 2.18 Non-American spelling in agent-authored prose

**Audit finding:** low severity — "tumour", "oedema", "prioritising", "programme".

**Changed in both records.** `data_collectors[1].collector_details` now reads "tumor and optic disc
edema"; `known_limitations` now reads "prioritizing"; "research programme" → "research program" and
"internship programme" → "internship program" throughout. Quoted material and source titles retain
their original spelling.

### 2.19 Core record: `distributions[*].conforms_to_standard` as a scalar

**Audit finding:** high severity — written as a scalar where the schema declares the slot
multivalued.

**Changed in the core record.** Every `distributions` entry now carries a list. Where the full
record's corresponding `file_collections` entry lists two terms, the core entry now lists both —
so `cardiac_ecg` carries `[WFDB, CDS]` rather than the previous scalar `WFDB`, and so on for all
ten entries.

### 2.20 Core record: `distributions[*].id` values

**Audit finding:** high severity — the audit questioned whether `distributions` and its keys are
declared in the core schema at all.

**Partially changed.** The `id` values (fragments on the dataset DOI) were removed from every
`distributions` entry, so the entries no longer mint identifiers whose necessity is unestablished.
The slot itself is retained (see §3.2).

### 2.21 Core record: content displaced into `informed_consent[0].notes`

**Audit findings:** two high-severity findings — compensation, notification and consent-process
content collapsed into one prose blob.

**Changed in the core record.** The notes field was reorganized and now closes with an explicit
statement of why the content sits there: "This notes field carries participant-notification,
consent-process and compensation facts for which the core schema declares no separate slot." The
content itself is unchanged and complete. This is a transparency fix rather than a structural one
— see §3.3 for why the content was not relocated.

### 2.22 Core record: content displaced into top-level `notes`

**Audit findings:** medium severity across `splits`, `subsets`, `citation`, `total_file_count`,
`total_size_bytes`.

**Partially changed in the core record.** The byte and file counts moved from `notes` into
`description`, where they read as dataset facts rather than residue. The `splits` content was
expanded in `notes` to carry the full per-stratum breakdown the audit noted was lost (all twelve
race/ethnicity cells, sex counts, diabetes-status counts and mean ages for each of train,
validation and test). The three-tier subset description was likewise expanded to name each tier and
its contents. The citation remains in `notes`. See §3.4.

### 2.23 Core record: `related_datasets` cross-references to a removed slot

Consequential change: the core record's `has_part` descriptions previously pointed at
`https://doi.org/10.60775/fairhub.3#dir-*` fragments that no longer exist there, since the
`distributions` entries lost their `id` values. Each description now reads "recorded in the
distributions slot of this record" instead of citing a dangling fragment.

### 2.24 `sensitive_elements` entries structurally indistinguishable

**Audit finding:** low severity.

**Changed in both records.** Each `sensitivity_details` now opens by naming which tier it
describes. The full record cross-references the subset identifiers
(`#subset-public`, `#subset-controlled`); the core record, which does not declare subsets, names
the tiers in words. `sex` was added to the controlled-tier list, which the bundle states and the
original entry omitted.

### 2.25 `external_resources` with unpopulated declared fields

**Audit finding:** low severity.

**Partially changed in both records.** `restrictions` added to two further entries where the bundle
supplies them: the Zenodo license record (the version 2.0 terms are the operative license) and the
BMJ Open publication (CC BY-NC 4.0, no commercial re-use). The remaining entries carry only
`external_resources` and `archival` because the bundle states nothing further about them.

### 2.26 Provenance additions

Two facts the bundle supplies and neither record carried were added to the full record's `notes`
and the core record's `notes`: the FAIRhub API `viewCount` of 24636 and the recorded citation count
of 0. The core record additionally records the mini subset's FAIRhub child-record identifier (4).

---

## 3. Findings left as-is

### 3.1 `confidentiality_level: restricted`

**Audit finding:** medium severity — the value is reasoned rather than evidenced, and the record's
own caveat concedes it.

**Left unchanged in both records.** The permitted enum offers only `unrestricted`, `restricted`,
`confidential`. Neither tier-1 value (`PublicDownloadSelfAttestationRequired`; `HL7:2N (normal)`)
maps onto any of the three. `unrestricted` would be false — access requires verified login, a
disease-specific use restriction and license assent, and a separate controlled tier exists.
Omitting the slot would discard information the evidence does support. The `source_caveats` was
strengthened to say plainly that this "is an interpretation rather than a stated value", but the
value stands.

### 3.2 Core record: the `distributions` slot itself

**Audit finding:** high severity — the audit could not confirm from the supplied digest that
`distributions` is declared in `data_sheets_schema_core_all.yaml`, and observed that the full
record uses `file_collections` for the same content.

**Left in place.** The schema digest supplied to this run documents the *full* `Dataset` class
only; it says nothing either way about which slots the `CoreDataset` class declares. I therefore
cannot assert from the digest that `distributions` is undeclared, and the audit's own wording
("if `distributions` is not defined … this fails validation; if it is defined …") acknowledges the
uncertainty. The narrower defects the audit identified within the slot — the scalar enum and the
minted `id` values — were both fixed. If validation rejects the slot, the correct remedy is to
replace it with whatever the core schema does declare for file-group structure; that is a
validation-driven change, not one this reconciliation can make on the evidence available.

### 3.3 Core record: slots present in the full record but absent from the core record

**Audit findings:** medium severity across `participant_privacy`, `consent_revocations`,
`direct_collection`, `relationships`, `splits`, `subsets`, `variables`, `third_party_sharing`,
`participant_compensation`, `collection_notifications`, `collection_consents`.

**Left absent from the core record.** The same reasoning as §3.2 applies: I cannot establish from
the supplied digest which of these the `CoreDataset` class declares, and inventing a slot the class
does not declare is a worse failure than omitting one it does. What was done instead is to make the
displacement visible and to ensure no *content* is lost:

- `participant_privacy` content is folded into `is_deidentified.deidentification_details`, which
  now carries the anonymization method, privacy techniques, reidentification risk *and* the
  data-linkage prohibition — the last two of which the audit correctly noted were previously lost.
- `consent_revocations` content sits in `informed_consent[0].withdrawal_mechanism`.
- `direct_collection`, `collection_notifications`, `collection_consents` and
  `participant_compensation` content sits in `informed_consent[0].notes`, now labelled as such.
- `relationships` content sits in `instances[0].notes`.
- `splits` and `subsets` content sits in top-level `notes`, now at full detail.
- `variables` (31 objects) and `third_party_sharing` remain absent; their substance is partly
  covered by `distributions` and the license slots respectively.

The core record states nothing the full record does not.

### 3.4 Core record: `citation` in `notes`

**Left as-is.** Same schema-uncertainty reasoning. The citation string is complete and verbatim
from the bundle; only its placement is at issue.

### 3.5 `publisher: https://fairhub.io`

**Audit finding:** medium severity — a bare URI in a `uriorcurie` slot, and the host is inferred
from the portal rather than stated as a publisher URI.

**Left unchanged in both records.** The schema declares no prefix for FAIRhub, so no CURIE form is
available; the v5 rule exempts identifier slots where no declared prefix fits. The FAIRhub metadata
gives `publisherName: "FAIRhub"` and the portal is unambiguously at that host. A bare literal
string would not satisfy `uriorcurie`.

### 3.6 `creators[0].affiliations` listing consortium institutions

**Audit finding:** medium severity — all nine ROR identifiers are attested, but the list conflates
the consortium's member institutions with formal affiliations of the creator organization.

**Left unchanged in both records.** Every identifier is drawn from the FAIRhub
`study_description` `collaboratorList` and `locationList` plus the lead sponsor; none was supplied
from outside the bundle. The `source_caveats` now states the limitation explicitly: "no source
states them as formal affiliations of the consortium entity itself."

### 3.7 `related_datasets[2]` and `[3]` targeting documentation websites

**Audit finding:** low severity — `https://docs.aireadi.org/` and `https://aireadi.org/` are not
datasets.

**Left unchanged in both records.** Both are recorded verbatim in the FAIRhub
`relatedIdentifier` list with `relationType: IsDocumentedBy`; the record mirrors the source. Each
description now names the source field explicitly. The tension is between the class name and the
DataCite relation vocabulary, not between the record and the evidence.

### 3.8 `related_datasets` `has_part` ARKs duplicating `file_collections`

**Audit finding:** high severity — two parallel representations of one part-whole structure with
different identifier schemes and no cross-link.

**Partially addressed, structure retained.** The ARK identifiers are attested verbatim in the
RO-Crate and represent the RO-Crate packaging entities, which are genuinely distinct objects from
the directories they package. Rather than remove either representation, each `has_part` description
in the full record now names the corresponding `file_collections` identifier explicitly ("the
RO-Crate packaging of the cardiac_ecg directory recorded at
`https://doi.org/10.60775/fairhub.3#dir-cardiac-ecg`"), supplying the cross-link the audit found
missing.

### 3.9 `keywords` drawn partly from the study record

**Audit finding:** low severity — "Type 2 Diabetes", "Data Sharing", "Exploratory Data Collection"
come from the study `keywordList` rather than the dataset `subject` list.

**Left unchanged in both records.** All three are attested in the bundle; the distinction between
study-level and dataset-level keyword lists is not one the schema draws.

### 3.10 `doi` in three surface forms

**Audit finding:** low severity.

**Left unchanged.** `doi: 10.60775/fairhub.3` is in the bare form its slot description requires;
`id` and `version_access.latest_version_doi` are `uriorcurie` slots where the `https://doi.org/`
form is valid. The three forms are correct for their three slots.

### 3.11 `conforms_to` as enumerating prose

**Audit finding:** low severity — restates in prose what `conforms_to_standard` encodes as terms.

**Left unchanged.** `conforms_to` is single-valued and its description asks what the sources say in
their words; `conforms_to_standard` records which registered standards those are. The instruction
is to populate both for the same statement.

### 3.12 `at_risk_populations` notes discussing AI/AN alongside a `false` flag

**Audit finding:** low severity — the placement was defensible but the notes did not say so.

**Changed only in wording.** The notes now close: "Native American participants are not among the
four race/ethnicity groups recruited in this release, so this engagement concerns a group not
enrolled and does not bear on the at_risk_groups_included flag above." The flag stands at `false`.

### 3.13 `collection_timeframes[0].source_caveats`

**Audit finding:** flagged as a positive control — correct handling of the one-day discrepancy.

**Left as-is**, with the word "discrepancy" added for clarity.

### 3.14 `purposes` / `addressing_gaps` / `tasks`

**Audit finding:** flagged as a positive control — correctly one object per item, using the
declared `response` field.

**Left entirely unchanged in both records.**

### 3.15 `conforms_to_class`

**Audit finding:** flagged as a positive control.

**Left unchanged:** `Dataset` in the full record, `CoreDataset` in the core record.

### 3.16 Core header `# Phase 4 reconciliation: completed`

**Audit finding:** medium severity — the line asserted completion of a phase that had not run when
the record was audited.

**Left in place.** The line is mandated verbatim by the run instructions and is now true: Phase 4
has run and this report is its output. The audit's objection was to its premature presence at
Phase 3, not to its correctness at Phase 4.

---

## 4. Referent

Both records describe the same single referent: **version 3.0.0 of the Flagship Dataset of Type 2
Diabetes from the AI-READI Project**, identified by `https://doi.org/10.60775/fairhub.3`. This
choice was held consistently across both records. Prior versions (1.0.0, 2.0.0) appear only as
`related_datasets` entries and in `version_access`; the study that produced the data appears only
through `human_subject_research`, `ethical_reviews` and the collection slots, never as the record's
subject.

---

## 5. Summary of the change

| | Full | Core |
|---|---|---|
| Slots removed | 7 | 8 |
| Slots added | 1 | 1 |
| Slots restructured | 14 | 15 |
| Identifier corrections | 6 | 6 |
| Boolean/enum corrections | 3 | 3 |

No dataset fact was added that the bundle does not state. No fact present in the pre-reconciliation
records was discarded — content moved between slots but nothing was dropped. The strongest
remaining uncertainty is the core schema's slot inventory (§3.2, §3.3), which the supplied digest
does not document and which validation, not this reconciliation, must settle.