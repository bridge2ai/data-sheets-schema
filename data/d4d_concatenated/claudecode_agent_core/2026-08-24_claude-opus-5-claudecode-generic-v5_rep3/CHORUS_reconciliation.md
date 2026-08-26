# CHORUS full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep3

Run label: `2026-08-24_claude-opus-5-claudecode-generic-v5_rep3`
Arm: BASELINE (input documents only)
Condition: generic_v5 · Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5
Mode: four-phase project agent (all four phases run sequentially in one context)

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d_core.yaml`
- Report: this file

## Referent

`Dataset` admits one referent. The manifest's `scope:` block for CHORUS declares
the referent as the **CHoRUS dataset**, identified by `https://chorus4ai.org/`,
with the note that no dataset DOI appears in any CHORUS source document and the
project site is the identifier the records themselves use. That is the referent
chosen and held to consistently in both records: `id: https://chorus4ai.org/`.
The manifest declares no `related_but_distinct` dataset for this project, and
neither record populates `related_datasets`.

The bundle also contains a large body of material about the **AIM-AHEAD
Bridge2AI for Clinical Care Training Program** (cohort 2 informational webinar).
That program is not the referent. Its content is represented only where it
states something about the dataset — the dataset's contents and data standards,
the access route, and the fact that the data are being used for training — and
its own eligibility rules, stipend, application dates and curriculum are
excluded as facts about the program rather than the dataset. The single
exception is `existing_uses`, where the program is named as a known use and its
cohort 2 dates and trainee count qualify that use.

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs read during this run, in full:

- `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (the declared bundle)
- `data/preprocessed/source_manifest.yaml` (scope, `source_priority`, `naming`,
  read through `d4d download scope`, `d4d download priority` and a direct load)

Structural inputs: `data_sheets_schema_all.yaml` (class `Dataset`) and
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), both resolved through
LinkML `SchemaView` rather than read as text, plus the checker modules
`grounding.py`, `identifiers.py` and `d4d_pair_consistency.py`.

**No prior generated D4D record was read, from any arm, label or date.** Nothing
under `data/d4d_concatenated/` was opened except this run's own two outputs, and
no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was opened. No `d4d:docExample` value was copied. No
live web content was fetched. Prior D4D content from the parent conversation was
treated as forbidden evidence and none was used.

### Source disagreement, resolved by the declared ranking

`source_priority` for CHORUS, lowest tier strongest:

| tier | source id | type |
|---|---|---|
| 2 | `project_documentation` | documentation (chorus4ai.org) |
| 4 | `nih_reporter_project` | NIH project page |
| 4 | `cohort_2_webinar` | tutorial |
| 5 | `github_organization_overview` | historical documentation |

One genuine disagreement was found.

**Admission count.** chorus4ai.org (tier 2) states a current released dataset of
**50,000** patient admissions. The cohort 2 webinar (tier 4) states that as of
August 2025 the dataset "covers 14 different hospitals with over 45K unique
admissions". The ranking decides: the tier 2 value is stated in the record
(`instances[0].counts: 50000`), and the webinar figure is recorded in that
object's `source_caveats` and in the record-level `source_caveats` together with
which was preferred and why. The two are not necessarily inconsistent, since the
webinar figure carries an August 2025 date and the website figure carries none.

A third figure was checked and found **not** to be a disagreement: the NIH
RePORTER abstract's "more than 100,000 critically ill patients" describes the
project's target, and matches chorus4ai.org's *anticipated final dataset* of
100,000 admissions rather than the released dataset. Released and anticipated
scale are represented as the distinct scopes they are, not reconciled into one
number.

No other source pair disagreed. The hospital count (14 contributing, within 20
academic centers) is stated consistently by all three of chorus4ai.org, the
webinar and the GitHub README.

### Evidence defects in the sources, recorded rather than silently absorbed

- **The webinar's data type table lost its column alignment** in the text
  extraction of the source PDF. The data type → data standard pairings are
  recoverable and are asserted (9 `distribution_formats` entries). The per-row
  entries in the access control, metadata and published metadata schema columns
  are not recoverable. Only the repeated `Controlled` access designation, which
  applies to every listed row, is asserted from that table. The
  `#limitation-metadata-publication` object states that some modalities carry a
  published metadata schema and others are marked planned, and its
  `source_caveats` states explicitly that no per-modality attribution is
  possible. This is recorded rather than guessed.
- **`cmccrary@mgh.havard.edu`** is transcribed exactly as chorus4ai.org gives
  it. The domain appears to contain a typographical error in the source; it has
  not been corrected, and the `source_caveats` on that maintainer says so.
- **`23 Tb`** is transcribed as the project website writes it. That source does
  not disambiguate terabits from terabytes and no conversion was applied.
- **chorus4ai.org carries a site-wide banner** reading "This repoitory is under
  review for potential modification in compliance with Administration
  directives" (spelling the source's). Since the tier 2 source is the one the
  ranking makes decisive, this is recorded in the record-level `source_caveats`
  as a qualification on the figures taken from it.
- The `github_organization_overview` source is manifest-classified as historical
  documentation (tier 5) and is a capture dated 2025-11-14; noted in
  `source_caveats`.

### Identifiers

**The bundle contains no ROR, no ORCID, no DOI and no ARK.** This was verified
directly against the bundle text, not assumed. Accordingly neither record
asserts one: every named person (six leadership team members) carries a `name`
and `affiliations` but no personal identifier, and every named organization
carries a `name` and no ROR. This is the #547 trap and it was declined
deliberately — supplying a correct ROR for Massachusetts General Hospital or the
University of Florida from model memory would be an unsupported claim
indistinguishable, to a reader who was not present, from a wrong one.

The consequence is recorded rather than hidden: `Creator.principal_investigator`
has range `Person`, whose `id` is **required**, so populating it would have
forced minting a personal identifier the evidence cannot supply. The slot is
left unpopulated for every creator and the `source_caveats` on the Rosenthal
entry states why. The same reasoning left `data_governance.committee_contact`,
`data_governance.committee_members` and `license_and_use_terms.contact_person`
unpopulated; the two access-request addresses the GitHub README gives are
carried in `data_governance.access_review_process`, which is the field that asks
how an access request is made.

Identifiers that *are* present fall into two groups, both admissible:

- **Three attested external URLs** used as object identifiers —
  `https://github.com/chorus-ai`,
  `https://reporter.nih.gov/project-details/10472824` and the AIM-AHEAD webinar
  PDF URL. Each appears in the bundle.
- **Minted fragments on the dataset's own attested identifier** —
  `https://chorus4ai.org/#…` — for parts of this record that have no referent
  outside it (purposes, tasks, creators, distribution formats and so on). This
  is the one case in which minting is right: the base is attested and the
  fragment is ours. No new namespace was invented, and no fragment was appended
  to an organization identifier.

Machine checks (both records): `resolver_url_in_identifier_slot` = **0**,
`undeclared_prefixes` = **0**, all identifier values classify as absolute `uri`
with **0** bare tokens and **0** undeclared CURIEs.

### Shape and slot-filling audit

- No prose sits in a slot whose range is a list; `stewardship_roles`,
  `special_populations`, `examples`, `keywords` and
  `external_resources[].external_resources` are all lists of strings.
- Enum values used are schema-declared: `OMOP_CDM`, `DICOM`, `WFDB`
  (`DataStandardEnum`); `coverage_limitation`, `integration_limitation`
  (`LimitationTypeEnum`). No value was invented. `CRediTRoleEnum`,
  `DataUsePermissionEnum` and `CreatorOrMaintainerEnum` are left unpopulated
  because the sources state no contributor role, no Data Use Ontology category
  and no maintainer type.
- No commentary is embedded inside a name, identifier or affiliation value. All
  evidence commentary sits in `source_caveats`, never in `notes`; `notes` is
  unpopulated throughout both records.
- `conforms_to` (scalar) names the OMOP Common Data Model, the standard the bulk
  of the content follows. `conforms_to_standard` carries the three registered
  standards the bundle attests — `OMOP_CDM`, `DICOM`, `WFDB`. EDF+, Persyst and
  the OHNLP schema have no `DataStandardEnum` value; `OTHER` was **not** added,
  because it would record that some unnamed further standard applies without
  saying which, and those three formats are already stated in the
  `distribution_formats` entries that carry them.

### Deliberate omissions

Recorded here so the absences read as decisions rather than gaps. In each case
the bundle states nothing and a value would have been a guess: `version`, `doi`,
`download_url`, `issued`, `created_on`, `last_updated_on`, `license` (top level),
`publisher`, `citation`, `language`, `status`, `is_tabular`, `compression`,
`total_file_count`, `total_size_bytes`, `known_biases`, `anomalies`,
`content_warnings`, `ethical_reviews`, `data_protection_impacts`,
`informed_consent`, `at_risk_populations`, `participant_compensation`,
`collection_consents`, `consent_revocations`, `collection_notifications`,
`direct_collection`, `missing_data_documentation`, `imputation_protocols`,
`annotation_analyses`, `machine_annotation_tools`, `variables`,
`use_repository`, `other_tasks`, `future_use_impacts`, `discouraged_uses`,
`prohibited_uses`, `distribution_dates`, `errata`, `retention_limit`,
`version_access`, `ip_restrictions`, `regulatory_restrictions`,
`parent_datasets`, `related_datasets`, `resources`, `file_collections`.

Two specific judgements are worth naming:

- **`license` is left unpopulated at the top level.** The chorus-ai GitHub
  README states "This project is licensed under the MIT License", but in that
  document it governs the organization's software repositories, not the data —
  and the same page lists Chorus_SOP as Apache-2.0. Recording MIT as *the
  dataset's* license would be a scope error, and it would contradict the
  controlled-access licensing agreement the webinar describes. The MIT statement
  is recorded where it is true, in the `source_caveats` of the GitHub
  `external_resources` entry and of `license_and_use_terms`.
- **`is_deidentified.identifiable_elements_present` is left unpopulated.** The
  sources describe de-identification as complete for some modalities and in
  process for others, so no single boolean is supported. The techniques are
  recorded in `method` and `deidentification_details`.

### Corrections made in Phase 3

Phase 2 read the bundle again alongside the validated Phase 1 full record and
found one source-supported fact the full record had missed; the source audit
then found five slotting defects. All six were fixed in the **full** record
first, and core was re-projected from the corrected full record afterwards.

| # | Finding | Correction |
|---|---|---|
| 1 | Phase 2 discovery: the RePORTER abstract states the project collaborates through the NIH Bridge2AI program, the NIH Bridge2AI Bridge Center, external biomedical and clinical organizations, industry and regulatory agencies. Phase 1 omitted it. | Back-ported into `creators[CHoRUS Consortium].description` in full, then carried to core. |
| 2 | The webinar `external_resources` entry carried a `restrictions` list describing how to get at *the dataset*. That slot means restrictions on reaching *the external resource*. | `restrictions` removed. The access requirements were already in `data_governance.access_review_process` and `intended_uses[training].usage_notes`. |
| 3 | `sampling_strategies[0].description` held a sentence about managing privacy and bias with social determinants of health — not a statement about sampling. | Removed from the sampling object; the content now sits in `human_subject_research.description`, a slot present in both records. |
| 4 | `participant_privacy[0].description` restated the ethics focus groups and community-perspectives content. `participant_privacy` is full-only, so that content would have been lost from core. | Removed from `participant_privacy`; consolidated into `human_subject_research.description` so both records carry it. |
| 5 | One sentence naming the CTP-deid repository and the privacy scan tool was repeated across three objects. | The duplicated sentence was dropped from the imaging preprocessing entry, whose text now describes the de-identification step itself. All three slots remain populated: the sentence is retained once, in `deidentification_details`, and the tooling is also named in `privacy_techniques`. |
| 6 | `instances[2]` was named "Radiology image". The webinar's count of 1000 is for "Imaging (from PACS)"; "radiology" comes from a different source and a different measure (7,642 *admissions* with radiology data). | Renamed to `Image` / `instance_type: image`, id `#instance-image`. |
| 7 | `data_governance.description` restated the registration route already given in `access_review_process`. | Trimmed to the non-duplicative claim. |
| 8 | Record-level `source_caveats` did not disclose the title's provenance, the `23 Tb` unit ambiguity, or the absence of any registry identifier in the bundle. | All three added. |

Both records were re-validated after the corrections; results below.

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with
LinkML `SchemaView`. No hand-written field list was used.

**Schema-derived shared slot count: 79 schema-identical slots.**
Projected slots: `resources`. Per-record slots (exempt, and required to differ):
`conforms_to_class`, `conforms_to_schema`.

Core was produced by projecting the Phase 3-audited full record onto the
`CoreDataset` slot inventory, so every schema-identical slot is deeply identical
by construction rather than by repair. No narrative field was condensed,
paraphrased, reordered or omitted in core. **`--sync-core` was not needed and
was not run**: the independent check passed on its first execution.

### Full-only slots

Three top-level slots are populated in full and are **not declared on
`CoreDataset`**, so their absence from core is required by the schema and is not
a divergence:

- `splits` — the holdout test set provisioned for external model validation
- `participant_privacy` — anonymization method and privacy techniques
- `third_party_sharing` — controlled distribution outside the contributing
  institutions

Before dropping them, each was checked for content that core could otherwise
lose. `participant_privacy` was the only one carrying such content, and it was
moved to `human_subject_research` in Phase 3 correction 4. The holdout set and
the controlled-sharing statement are represented in core through
`intended_uses[external validation]` and `data_governance` respectively, so no
fact is lost, only the full-only structure that carried it.

### Projected and related content

- `resources` is the one projected slot (`Dataset` in full, `CoreDataset` in
  core). It is unpopulated in both records — the bundle describes no component
  sub-datasets — so coverage is trivially equal and there is nothing to project.
- **`distributions` is absent from core, and the report is not claiming it was
  removed.** `file_collections` is unpopulated in full because the bundle gives
  no file paths, counts, byte sizes or checksums, so there is nothing to map to
  core's `distributions`, and no `distributions` block was ever emitted.
- The full/core mapping of `distribution_formats` (9 entries), `instances`,
  `total_file_count` and `total_size_bytes` was reviewed for scope conflicts.
  `total_file_count` and `total_size_bytes` are unpopulated in both: the only
  volume figure in the bundle, 23 Tb, covers waveform data alone and is recorded
  on the waveform `distribution_formats` entry rather than aggregated into a
  dataset-level total it does not describe.
- `dialect` and `is_tabular` are unpopulated in both. The dataset spans tabular
  OMOP content and non-tabular imaging, waveform and EEG content, so no single
  boolean holds; the bundle states no CSV dialect.
- Top-level identity, version and access facts were checked against the nested
  statements: `id` and `page` both resolve to the manifest's declared referent;
  the controlled-access statement in `description` agrees with all nine
  `distribution_formats` entries, with `data_governance`, with
  `license_and_use_terms` and with `third_party_sharing`; the 50,000 / 100,000
  released-versus-anticipated distinction is stated identically in
  `description`, `instances[0]`, `#limitation-released-versus-anticipated` and
  `updates`. No contradiction was found within either record or between them.

### Machine checks

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d_core.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
# PASS: 79 schema-identical slots; projected slots=['resources'];
#       per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']

# grounding.check_run(full, core, bundle, uriorcurie_slots())
# {'grounded': 0, 'minted_fragment': 0, 'absent': 0}

# grounding.british_spellings  -> 0 (full), 0 (core)
# grounding.gc_label_variants  -> {} (full), {} (core)  [canonical label: CHoRUS]
# grounding.resolver_urls_in_identifier_slots -> 0 (full), 0 (core)
# grounding.undeclared_prefixes -> 0 (full), 0 (core)
# identifiers.classify -> full: 76 uri; core: 73 uri; 0 bare tokens, 0 undeclared CURIEs
```

`grounding` reports **0 absent**, and that figure means what it says only in
combination with the bundle check above: the bundle asserts no ROR, ORCID, DOI
or ARK, and neither record asserts one. Zero absent here is the honest outcome
of declining to supply identifiers from memory, not the result of a record with
no identifiers to check — all 76 identifier values in full and 73 in core were
walked and classified.

### Repair

**No repair phase was run.** Pair consistency passed on its first independent
execution, grounding reported no findings, and the report-claims checker
reported none. Nothing that the Phase 4 checkers surfaced required changing
either record, so no `repair` or `report_after_repair` phase is recorded — an
empty one would assert work that did not happen.

The eight Phase 3 corrections above are **not** a repair in this sense: they
were made during the source audit, before Phase 4's checkers ran, and core was
projected from the already-corrected full record.

## Result

| | full | core |
|---|---|---|
| top-level populated slots | 43 | 40 |
| schema validation | pass | pass |
| term validation | pass | pass |

- Schema-identical shared slots: **79**, all deeply identical, all identically
  present or absent.
- Projected slots: 1 (`resources`), unpopulated in both.
- Per-record slots correctly differing: `conforms_to_class` (`Dataset` /
  `CoreDataset`), `conforms_to_schema`.
- Unresolved contradictions within or between the two records: **none**.
- Prompt condition: `generic_v5`, prompt file
  `src/download/prompts/d4d_generic_arm_prompt_v5.md`. The instruction as sent
  is recorded with the provenance record.
