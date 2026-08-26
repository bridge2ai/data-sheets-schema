# CHORUS full/core reconciliation

- **Run label**: `2026-08-24_claude-opus-5-claudecode-generic-v5_rep2`
- **Arm**: BASELINE (input documents only)
- **Condition**: `generic_v5`, prompt `src/download/prompts/d4d_generic_arm_prompt_v5.md`
- **Mode**: four-phase project agent (all four phases run sequentially in one context)
- **Runtime / provider / model**: Claude Code / Anthropic / claude-opus-5
- **Declared input bundle**: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- **Full record**: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CHORUS_d4d.yaml`
- **Core record**: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. This record is about the **CHoRUS dataset** — the
multi-center, multimodal critical care dataset assembled by the CHoRUS for Equitable AI
data generation project — and its identifier is `https://chorus4ai.org/`. This matches the
`scope:` declaration for CHORUS in `data/preprocessed/source_manifest.yaml`
(`referent: CHoRUS dataset`, `referent_id: https://chorus4ai.org/`,
`related_but_distinct: []`), and it is the identifier the sources themselves use: no source
in the bundle states a DOI for the dataset.

The choice is held consistently across both records — the same `id`, `name` and `page` in
each, and no nested object stands in for another dataset.

The bundle also documents two things that are *not* the referent, and neither was recorded
as a property of the dataset:

- the **NIH award** (application 10472824, core project OT2OD032701). Its title, period and
  amount are recorded under `funders[].grants[]`, where they describe the grant, not the data.
- the **AIM-AHEAD Bridge2AI for Clinical Care Training Program**. Its trainee eligibility
  rules, stipend, application deadlines, curriculum staffing and AIM-AHEAD/NIH leadership
  are properties of a training program, not of this dataset, and were excluded. What was
  kept from that source is what it states about the dataset itself: modality inventory and
  data standards, admission counts, controlled access, the access route, and the dataset's
  use in training activities.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs read during this run, in full:

| Path | Role |
|---|---|
| `/tmp/agentic_fanout/CHORUS_rep2.md` | rendered instruction |
| `.claude/agents/d4d-provenance-guard.md` | evidence boundary |
| `.claude/commands/d4d-full-core.md`, `d4d-agent.md`, `d4d-uniform-rules.md` | method and decision rules |
| `data/preprocessed/concatenated/CHORUS_preprocessed.txt` | the only source of dataset facts |
| `data/preprocessed/source_manifest.yaml` (`scope:`, `naming:`, `source_priority`) | referent, canonical label, source ranking |
| `data_sheets_schema_all.yaml`, `data_sheets_schema_core_all.yaml` | structure only, via `SchemaView` |

**No prior generated D4D record was read, cited, or consulted** — nothing under
`data/d4d_concatenated/`, nothing under `data/ro-crate_packages/`, from any arm, label or
date. Record structure was derived at runtime from `SchemaView` over the two schemas
(`class_induced_slots`, class ranges, enum permissible values), not from any existing YAML
used as a template. Both headers carry `Prior D4D factual reuse: prohibited`.

### Source ranking and the one disagreement

`d4d download priority --project CHORUS` ranks the four sources: `project_documentation`
(chorus4ai.org) tier 2; `nih_reporter_project` and `cohort_2_webinar` tier 4;
`github_organization_overview` tier 5.

One substantive disagreement was found, and it was resolved by the ranking rather than by
reading:

> **Number of admissions.** `project_documentation` (tier 2) states the current released
> dataset holds **50,000 patient admissions**; `cohort_2_webinar` (tier 4) states that as of
> August 2025 the dataset covers 14 hospitals with **over 45K unique admissions**.
> `d4d download priority --decide project_documentation,cohort_2_webinar` returns
> `project_documentation` as the winner. **50,000 is the recorded value**
> (`instances[0].counts`), and both figures with the preference are stated in the
> dataset-level `source_caveats`.

Two further differences are *renderings*, not disagreements, and both sit at the same tier,
so the ranking cannot decide them. Each is represented rather than silently resolved:

- the principal investigator's name — `ROSENTHAL, ERIC S.` (NIH RePORTER) versus
  `Eric Rosenthal` (webinar). The webinar form is used and the RePORTER form is recorded in
  that creator's `source_caveats`.
- the dataset's title — the webinar slides head it both `CHoRUS Dataset` and
  `Bridge2AI for Clinical Care Dataset`. The former is used as `name`; the latter is
  recorded in the dataset-level `source_caveats`. No `title` is asserted, because no source
  gives the dataset an official title distinct from its name (the long
  "Patient-Focused Collaborative Hospital Repository Uniting Standards (CHoRUS) for
  Equitable AI" titles the award and the network, and is recorded as the grant's name).

### Unsupported, stale and mis-scoped assertions — what was deliberately omitted

Prefer-omission decisions, each with the reason the evidence does not carry the slot:

- **`license`** (dataset level) — not asserted. The GitHub organization README (tier 5)
  says "This project is licensed under the MIT License", on a page whose repository listing
  shows repositories under both MIT and Apache-2.0. That statement covers the
  organization's software, and no source states a license for the *dataset*, whose access is
  controlled and conditioned on a signed licensing agreement. The MIT statement is recorded
  in `license_and_use_terms.license_terms` and in `source_caveats`, attributed to the README.
- **`publisher`** — declared `uriorcurie`; no source gives a registry identifier for any
  organization, so the slot is omitted rather than filled with a name or an invented CURIE.
- **`doi`, `download_url`, `version`, `created_on`, `issued`, `last_updated_on`,
  `distribution_dates`** — no source states any of them.
- **`data_use_permission`** (`LicenseAndUseTerms`) — the DUO vocabulary distinguishes
  `user_specific`, `institution_specific` and others; the bundle states a registration form,
  a signed licensing agreement and a `.edu` email requirement but names no DUO category.
  Mapping those requirements onto one enum value would be inference, so the terms are stated
  in `license_terms` and no enum value is chosen.
- **`regulatory_restrictions`** — the bundle mentions HIPAA and GDPR only as topics of a
  training-program workshop, never as regulations governing this dataset. Omitted as
  mis-scoped.
- **`participant_compensation`** — the bundle's only compensation figure is an $8,000
  stipend for *trainees*, not for data subjects. Omitted as mis-scoped.
- **`at_risk_populations`, `informed_consent`, `collection_consents`,
  `consent_revocations`, `collection_notifications`, `retention_limit`,
  `data_protection_impacts`, `ip_restrictions`, `errata`, `version_access`,
  `known_biases`, `anomalies`, `content_warnings`, `cleaning_strategies`,
  `relationships`, `variables`, `is_tabular`, `language`, `compression`,
  `related_datasets`, `parent_datasets`, `subsets`** — no supporting statement in the
  bundle. `related_datasets` is additionally empty by declaration: the manifest's
  `related_but_distinct` list for CHORUS is `[]`.
- **`total_size_bytes` / `bytes`** — the sources give exactly one size, "23 Tb Waveform
  data". Converting it to an integer byte count requires choosing a base the source does not
  state, and it covers one modality rather than the dataset, so it is recorded verbatim in
  the waveform collection's description and no integer is asserted.
- **`start_date` / `end_date`** on `collection_timeframes` — the award period
  (2022-09-01 to 2026-11-30) is the *project's* period, not the timeframe of the clinical
  encounters. Writing it into these fields would mis-scope it, so the fields are empty, the
  retrospective nature of collection is stated in `timeframe_details`, and the gap is named
  in that object's `source_caveats`.

### Identifiers

Every identifier in both records was checked against the bundle with
`data_sheets_schema.grounding.check_run` over `uriorcurie_slots()`:

```
{'grounded': 0, 'minted_fragment': 0, 'absent': 0}   # no findings
```

**Zero `absent`** — the records state no registry identifier the bundle does not contain —
and **zero resolver-URL findings**, so no `uriorcurie` slot holds a resolver URL where the
schema declares a prefix.

The reason all three counters read zero is that this record contains no registry-style
identifier at all, and that is the correct outcome for this bundle. The bundle supplies no
ORCID, no ROR and no DOI for anything it names. Under the rule that an identifier naming
something outside this dataset is a fact like any other, supplying RORs for Massachusetts
General Hospital, the University of Florida, UTHealth Houston or Tufts University — or
ORCIDs for the six named leadership-team members — would be an unsupported claim even
though the values would be correct. Those organizations and people are therefore recorded
by **name and affiliation only**.

One consequence is recorded rather than worked around: `Person` declares `id` as
**required**, so no `Person` object can be emitted for anyone the bundle names without
inventing an identifier for them. `creators[].principal_investigator`,
`LicenseAndUseTerms.contact_person`, `EthicalReview.contact_person` and
`DataGovernance.committee_members` are consequently empty. The principal investigator is
carried as a `Creator` with `name` and `affiliations` populated, and the omission and its
reason are stated in that creator's `source_caveats` and in the dataset-level
`source_caveats`. Minting a fragment for a person was rejected: a person has a referent
outside this record, so the fragment rule does not reach them.

The 10 identifiers actually present are all URLs: the dataset's own
`https://chorus4ai.org/` (which appears 6 times in the bundle) and 9 `file_collections[].id`
values minted as fragments on it (`#demographics`, `#medication-administration`,
`#procedures`, `#nursing-flowsheets`, `#diagnoses`, `#clinical-notes`, `#imaging`,
`#waveform-telemetry`, `#waveform-eeg`). Each names a part of this dataset with no referent
outside this record, which is the one case in which minting is right, and each hangs off an
identifier the bundle supplies. No prefix was invented.

### Shape audit and corrections

Two defects were found and **corrected in the full record first**, before core was rebuilt
from it:

1. `maintainers[0].maintainer_details` embedded the evidence commentary
   "spelling as given by the source" inside the contact detail. The commentary was moved to
   that maintainer's `source_caveats`; the address `cmccrary@mgh.havard.edu` remains
   transcribed exactly as chorus4ai.org gives it, including the domain spelling, because an
   identifier copied from a source keeps the source's spelling.
2. `future_use_impacts[2].impact_details` embedded "(spelling as in the source)" inside the
   quoted website banner. The commentary was moved to that object's `source_caveats`; the
   banner text — including "repoitory" as chorus4ai.org spells it — is left exactly as
   written, because quoted source text keeps its original spelling.

Other shape checks, all clean: no `notes` is used anywhere in either record; all evidence
commentary sits in `source_caveats` (6 objects plus the dataset level); no prose sits in a
slot declaring a list; every enum value used (`OMOP_CDM`, `DICOM`, `WFDB`, `OTHER`,
`coverage_limitation`, `academic_institution`) is declared by its enum; no commentary is
embedded in a name, identifier or affiliation value; and no scalar-ranged slot holds an
object.

Two structured slots are deliberately left empty while related content sits in prose, and
both are judgements rather than oversights:

- `DataGovernance.committee_contact` / `committee_members` — the bundle gives two
  access-request addresses (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`) and
  names no committee. `committee_contact` is singular and cannot hold both without silently
  selecting one; `committee_members` would assert that these two people form a committee,
  which no source says. Both addresses are stated in `access_review_process`, which is the
  field that asks how access is requested. Asserting false structure was judged worse than
  prose in the field that answers the question.
- `Maintainer` declares no contact field, so the program-manager contact sits in
  `maintainer_details` for want of anywhere else.

### Multivaluedness and slot-placement

Where a slot's declared range is multivalued, one object per distinct entity was emitted
rather than one object carrying several: 7 `creators` (six named leadership-team members
plus the consortium, not one merged Creator), 9 `file_collections` (one per modality,
matching the "9 Different data modalities" the project documentation states), 4
`raw_data_sources`, 5 `collection_mechanisms`, 5 `preprocessing_strategies`, 4
`addressing_gaps`, 4 `instances`, 3 `purposes`, 3 `tasks`, 3 `future_use_impacts` and 2
`known_limitations`.

Slot placement was decided from each class's own question rather than by name similarity.
Three cases worth naming:

- the **access route** (registration form, licensing agreement, `.edu` email, the two
  request addresses) went to `data_governance.access_review_process`, not to
  `distribution_formats`, which asks how the dataset is distributed.
- **retention of raw data** — clinical note text staying at the contributing site while only
  tokens are held centrally — went to `raw_sources` (`RawData`: "Was the raw data saved in
  addition to the preprocessed data?"), not to `known_limitations`, and the origin systems
  went to `raw_data_sources`, which is a different slot asking where the original data comes
  from.
- the **holdout test set** went to `splits`, which asks about recommended data splits, and
  its purpose to `purposes`; it is not restated as an intended use.

### Back-ports from Phase 2

**None.** Phase 2 re-read the declared bundle against the completed full record and found no
fact the bundle supports that the full record had missed, and no fact stated differently.
Core therefore required no correction to be applied back to full, and the two Phase 3 shape
corrections above flowed in the required direction: full first, then core rebuilt from it.

## Phase 4 — strict full/core reconciliation

### Shared-slot identity

Shared slots were derived at runtime with LinkML `SchemaView` over `Dataset` and
`CoreDataset`; no hand-written field list was used. `Dataset` induces 98 slots and
`CoreDataset` 84; 82 are shared, of which **81 have the same induced range and
cardinality**.

`data_sheets_schema.d4d_pair_consistency` reports:

```
PASS: 79 schema-identical slots; projected slots=['resources'];
      per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
      Phase 4 must semantically review related distribution content;
      deterministic matches=9 (9 at collection level, 0 at nested resource level),
      unmatched core distributions=[]
```

The validator's 79 is the 81 schema-identical slots minus the two it exempts as per-record
metadata. **41 of the shared slots are populated, and every one is present in both records
with deeply identical parsed YAML** — every nested mapping value and every list item in the
same order. Core condenses, paraphrases, reorders and omits nothing, including in the
narrative fields: `description`, `source_caveats` and every `*_details` and `response`
string is byte-for-byte the value in full. This identity is structural rather than
asserted — core's shared slots were produced by copying full's parsed values through the
`SchemaView`-derived identical-slot list, so divergence was not possible in either
direction.

`resources` is the one shared slot whose range is projected (`Dataset` in full,
`CoreDataset` in core). It is **absent from both records**, so the projection is vacuous and
there is no coverage to compare.

### Full-only slots

Five populated slots exist in `Dataset` and are **not declared by `CoreDataset`**, so their
absence from core is a schema fact, not an omission: `file_collections` (projected to
`distributions`, below), `splits`, `direct_collection`, `participant_privacy` and
`third_party_sharing`. Core has one slot full does not declare, `distributions`.

Top-level populated slot counts: **full 46, core 42** — 41 shared, plus five full-only in
full and one core-only in core.

### `file_collections` → `distributions`: semantic review

This is the related-content mapping the validator's warning marks. It was reviewed, and the
warning is not evidence that the review happened, so here is what it found.

All **9 collections match 9 distributions by `id`, with equal coverage and no unmatched
distribution on either side**. Every populated `FileCollection` slot — `id`, `name`,
`description`, `conforms_to`, `conforms_to_standard` — is also declared by
`CoreDistribution`, so **no full-only nested slot was dropped in the projection** and each
of the 9 pairs is deeply identical across all five.

| distribution | `conforms_to` | `conforms_to_standard` |
|---|---|---|
| Demographics | OMOP | `OMOP_CDM` |
| Medication administration | OMOP | `OMOP_CDM` |
| Procedures | OMOP | `OMOP_CDM` |
| Nursing flowsheets | OMOP | `OMOP_CDM` |
| Diagnoses | OMOP | `OMOP_CDM` |
| Clinical notes | OHNLP | `OTHER` |
| Imaging | DICOM | `DICOM` |
| Waveform telemetry | WFDB | `WFDB` |
| Waveform EEG | EDF+ and Persyst | `OTHER` |

Reviewed and found not to conflict:

- **Names, descriptions and formats** agree by identity across the pair.
- **`format`, `media_type`, `encoding`, `compression`, `path`, `hash`/`md5`/`sha256`,
  `bytes`** are unpopulated on every `CoreDistribution`, and their `FileCollection`
  counterparts are unpopulated too. No source states a file format, media type, checksum,
  byte count or path for any modality — the dataset is analyzed inside a controlled-access
  enclave rather than distributed as files, so these have no evidence and no conflict.
- **Checksums and byte counts**: none in either record. The single size figure the sources
  give, "23 Tb", sits in the waveform telemetry description in both records for the reason
  given in Phase 3, and is stated identically in each.
- **Access URLs and release scope**: no access URL or download URL appears in either record,
  at dataset or distribution level, because the sources give none. All 9 modalities carry
  the same access condition — controlled — stated once in each distribution's description
  and consistently at dataset level in `distribution_formats`, `data_governance` and
  `confidential_elements`.
- **`total_file_count` / `total_size_bytes`**: absent from full, and `CoreDataset` declares
  neither, so there is no distribution-level figure to compare them against.
- **`dialect`** (core-only) and **`is_tabular`** (both) are absent from both records. No
  source characterizes the dataset as tabular, and it plainly is not uniformly so —
  relational OMOP tables alongside DICOM imaging and WFDB/EDF+ waveforms — so no boolean was
  asserted.
- **Dataset-level `conforms_to_standard`** is `[OMOP_CDM, DICOM, WFDB, OTHER]`, exactly the
  set union of the 9 per-distribution values, in both records. Dataset-level `conforms_to`
  names the same standards in the sources' own words. No standard is claimed at dataset
  level that no distribution carries, and none is carried by a distribution that dataset
  level omits.
- **Top-level identity and access facts against distributions and repeated statements**:
  the 9-modality inventory implied by the 9 distributions agrees with the "9 Different data
  modalities" stated in `description` and referred to in `data_governance`,
  `confidential_elements`, `distribution_formats` and `updates`. Counts repeated across
  slots are internally consistent in both records: 50,000 admissions (`description`,
  `instances[0].counts`, `updates`), 1.6 billion OMOP rows (`description`,
  `instances[1].counts`), 7,642 admissions with radiology data (`description`,
  `instances[2].counts`, imaging distribution, `known_limitations[0]`), 1000 images
  (`description`, `instances[3].counts`, imaging distribution, `known_limitations[0]`,
  `raw_data_sources[1]`, `is_deidentified`), 14 contributing hospitals and 20 academic
  centers, and grant OT2OD032701 with period 2022-09-01 to 2026-11-30.

### Current versus anticipated release — not a contradiction

The records state 50,000 patient admissions and also 100,000 patient admissions, and these
are **not conflicting values for one quantity**. The project documentation distinguishes a
"Current Released Dataset" (50,000 admissions, 1.6 billion OMOP rows, 7,642 admissions with
radiology data, 23 Tb of waveforms) from an "Anticipated Final Dataset" (100,000 admissions,
9 modalities, 14 hospitals), and the NIH abstract describes acquiring data from more than
100,000 critically ill patients. The two scopes are labelled as such wherever they appear —
in `description`, in `instances[0]` and in `updates` — and `status` records `Released`. The
same distinction explains the modality states recorded in `known_limitations`: imaging
de-identification and EEG extraction were in process as of August 2025, which describes the
current release rather than contradicting the anticipated one.

## Commands run

```bash
# Phase 1 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset .../CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data .../CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset .../CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data .../CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 3 — scope, ranking, grounding
poetry run d4d download scope --project CHORUS
poetry run d4d download priority --project CHORUS
poetry run d4d download priority --project CHORUS --decide project_documentation,cohort_2_webinar
python -c "... data_sheets_schema.grounding.check_run(full, core, bundle, uriorcurie_slots()) ..."

# Phase 4 — pair consistency and report claims
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml
python -c "... data_sheets_schema.report_claims.check_report(report, full, core, declared_slots()) ..."

# Provenance and gates
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep2 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v5.md \
  --prompt-text /tmp/agentic_fanout/CHORUS_rep2.md \
  --condition generic_v5 --runtime 'Claude Code' --provider Anthropic \
  --reasoning-effort high --phase ... (one per phase performed, in order)
poetry run d4d runs check --strict
poetry run d4d download scope --check --project CHORUS
```

`--sync-core` was **not** run. Core was built by projection from the Phase 3-corrected full
record, so the pair was already identical when the validator first saw it; running a
synchronization step would have had nothing to synchronize and would have obscured that.

## Files changed

| File | Change |
|---|---|
| `.../claudecode_agent/{LABEL}/CHORUS_d4d.yaml` | written in Phase 1; two Phase 3 shape corrections (evidence commentary moved into `source_caveats` on `maintainers[0]` and `future_use_impacts[2]`) |
| `.../claudecode_agent_core/{LABEL}/CHORUS_d4d_core.yaml` | written in Phase 2; rebuilt from the corrected full record after Phase 3 |
| `.../claudecode_agent_core/{LABEL}/CHORUS_reconciliation.md` | this report |

## Result

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | **No issues found** |
| `linkml-term-validator` full | **passed** |
| `linkml-validate` core (`CoreDataset`) | **No issues found** |
| `linkml-term-validator` core | **passed** |
| `d4d_pair_consistency` (no `--sync-core`) | **PASS**, 79 schema-identical slots, 1 semantic-review warning, reviewed above |
| Identifier grounding vs bundle | **0 absent, 0 resolver-URL findings** |
| Prior-D4D reuse | **none** — no generated record read from any run |
| Full top-level populated slots | 46 |
| Core top-level populated slots | 42 |

**Nothing diverged between the two records.** Every schema-identical shared slot is present
in both with deeply identical content, the one projected slot pair is fully matched with no
nested slot dropped, and no contradiction was found within either record or between them.
The corrections this run made were the two Phase 3 shape fixes to the full record, both
applied before core was rebuilt; **no repair phase was required after Phase 4**, because
neither the grounding checker, the report-claims checker, nor the final pair-consistency run
reported a finding that required changing either record.
