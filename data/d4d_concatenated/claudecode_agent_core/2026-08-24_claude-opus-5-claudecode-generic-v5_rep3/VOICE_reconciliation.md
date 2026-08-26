# VOICE — Phase 3 / Phase 4 reconciliation

- **Run label:** `2026-08-24_claude-opus-5-claudecode-generic-v5_rep3`
- **Condition:** generic_v5, BASELINE arm (input documents only)
- **Mode:** four-phase project agent, Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/VOICE_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/VOICE_d4d_core.yaml`

## Resumed run: which phases ran

A prior invocation of this same label was interrupted by a session limit after
writing the full YAML and nothing else. Per the playbook's snapshots section, the
existing artifact was re-validated before being accepted:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset .../VOICE_d4d.yaml                     # No issues found
poetry run linkml-term-validator validate-data .../VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --target-class Dataset                            # Validation passed
```

Both passed and the header block matched the condition text verbatim, so
`generate_full` was **skipped on a validated artifact** and recorded as
`phases_skipped`. Phases 2, 3 and 4 were performed in this invocation. No
artifact under any other label was read at any point.

## Referent

`Dataset` admits one referent. This record is about the **Bridge2AI-Voice adult
dataset** — the PhysioNet project `b2ai-voice`, concept DOI
`10.13026/37yb-1t42`, current version 3.1.0 published 1 May 2026. The
Bridge2AI-Voice Pediatric Dataset (`10.13026/mf9s-5r03`) is documented in the
same bundle as source `physionet_pediatric_1_1_0`; the manifest declares it
related but distinct, and it is carried in the declared slot
`related_datasets` as a single `is_supplemented_by` entry. Its facts are not
merged into this record and it appears in no distribution, resource or access
slot. The choice is held identically in both records.

## Phase 3 — source and provenance audit

### Provenance

Read history for this invocation, in order: the rendered instruction
(`/tmp/agentic_fanout/VOICE_rep3.md`), `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-uniform-rules.md`,
the full and core schemas, `d4d download scope`/`priority` output for VOICE, the
declared bundle in full, and the same-label full record. **No prior or
concurrent D4D record, evaluation, reconciliation report or crate was opened**,
and no factual value in either record comes from the parent conversation.

### Findings and corrections

1. **`creators[#creator-consortium].affiliations` was empty while the evidence
   answered it.** The consortium creator's `description` said the project
   "gathered 50 multidisciplinary experts from 12 North American institutions",
   but `Creator.affiliations` — a declared, multivalued `Organization` slot —
   held nothing. The project documentation lists the twelve collaborating
   institutions by name under "Collaborators". **Corrected in full first**, then
   projected to core: twelve `Organization` objects, one per institution, names
   exactly as the source writes them. No `id` on any of them: no ROR or other
   organization registry identifier for any of the twelve appears anywhere in
   the bundle, and supplying one from outside the evidence is prohibited.

2. **`creators[].principal_investigator` considered and left absent.** The
   bundle names Yael Bensoussan as principal investigator in two places (the
   IRB protocol header and the NIH RePORTER project page). The slot's declared
   range is `Person`, **not inlined** — it is a reference by `Person.id`, and an
   inline object fails schema validation, which is what an attempt to populate
   it produced. No ORCID or other personal registry identifier for her appears
   in the bundle, and a person may not be given a minted fragment identifier.
   The slot therefore stays absent in both records; the fact itself remains
   where the schema can carry it, in `creators[#creator-bensoussan].description`
   and `funders[].description`.

3. **`conforms_to_class` in core corrected from `Dataset` to `CoreDataset`.**
   The projection inherited the full record's value. This slot is a statement
   about the record rather than about the data — the core record instantiates
   `CoreDataset` — and the pair validator lists it as one of the two per-record
   slots that must differ between the pair.

4. **Three investigator affiliations disagreed between sources; the
   disagreement was resolved by ranking but not recorded.** The feasibility
   publication's group-member list places Frank Rudzicz at Dalhousie
   University, Vardit Ravitsky at the University of Montreal and Alistair
   Johnson at the University of Toronto; the project documentation and IRB
   protocol place them at the University of Toronto, The Hastings Center and
   the Hospital for Sick Children. Those are tier 2 sources and the feasibility
   publication is tier 3, so the tier 2 affiliations stand — but the caveat did
   not say so. **Added as item (11) of `source_caveats`** in both records.

5. **`hipaa_compliant: compliant` reviewed and kept.** The Data Transfer and
   Use Agreement states the transferred data "is Personally Identifiable
   Information, as that is defined in OMB Memorandum M-07-16, and not covered
   under HIPAA", while the healthsheet states the HIPAA de-identification rules
   were applied and the IRB protocol states the collection applications and
   storage are HIPAA-compliant. These are consistent rather than contradictory:
   data from which HIPAA identifiers have been removed is not protected health
   information. `other_compliance` already says this. No change.

### Slots considered and deliberately omitted

- **`at_risk_populations`** — the bundle attests that adults with cognitive
  impairment, dementia and psychiatric conditions are enrolled, and that
  participants from socially and economically disadvantaged populations are
  recruited under a Plan for Enhancing Diverse Perspectives. That content is
  already carried by `human_subject_research.special_populations`, and the
  bundle states no protection specific to those groups as distinct from the
  general consent process. Restating sibling values in a second slot is a
  slot-filling violation, so the slot is left absent. The `assent_procedures`
  and `guardian_consent` fields concern minors, who belong to the separate
  pediatric dataset.
- **`external_resources`, `errata`, `use_repository`** — the healthsheet
  answers each with an absence ("It is self-contained"; "There is no erratum";
  "No"). A value recording that something does not exist has not answered the
  field.
- **`is_tabular`** — the release mixes Parquet tensor files with TSV tables and
  the bundle nowhere characterizes the dataset as tabular. Omitted rather than
  inferred.
- **`publisher`** — the range is `uriorcurie`. PhysioNet is plainly the
  publisher, but the bundle supplies no registry identifier for it, and an
  identifier naming an organization outside this dataset must come from the
  evidence.
- **`compression`, `download_url`, `was_derived_from`, `imputation_protocols`,
  `created_by`, `created_on`, `last_updated_on`, `modified_by`, `resources`** —
  no supporting evidence in the bundle.

### Re-validation after correction

Both records were re-validated after every edit; the commands and their
outcomes are listed under "Commands run" below.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

The shared-slot set was derived at runtime with LinkML `SchemaView` from
`Dataset` and `CoreDataset`; no hand-written field list was used.

| quantity | value |
|---|---|
| schema-identical slots checked by the validator | **79** |
| top-level slots populated in full | **79** |
| top-level slots populated in core | **69** |
| shared and populated in both | 67 |
| full-only, populated | 12 |
| core-only, populated | 2 |
| projected slots | `resources` (absent from both) |
| per-record slots, required to differ | `conforms_to_class`, `conforms_to_schema` |

Every schema-identical slot present in both records has deeply identical parsed
YAML content, including every nested mapping value and list item in the same
order. Narrative fields — `description`, `notes`, `source_caveats`, and every
nested `*_details` field — were copied unchanged; nothing was condensed,
paraphrased, reordered or dropped to make core shorter.

The 12 full-only slots are those `CoreDataset` does not declare: `citation`,
`subsets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`,
`file_collections`. Their absence from core is a schema fact, not an omission.

`resources` is the one projected slot (`Dataset` in full, `CoreDataset` in
core). Neither record populates it, so coverage is equal and vacuous. The
individual files the full record describes live in
`file_collections[].resources`, which is nested and full-only.

### Related-content semantic review: `file_collections` → `distributions`

The validator matched 4 of 4 collections deterministically with no unmatched
core distributions, and emitted the standing warning that a semantic review is
still required. That review was performed:

| id | full `file_collections` | core `distributions` | verdict |
|---|---|---|---|
| `#collection-features` | `features/`, `processed_data`, 11 nested `File` resources | `features/`, same name and description less its trailing pointer to the nested list | no conflict |
| `#collection-phenotype` | `phenotype/`, `processed_data` | `phenotype/`, `format: TSV` added | no conflict |
| `#collection-metadata` | `metadata/`, `metadata` | `metadata/` | identical |
| `#collection-raw-audio` | `b2ai-voice-audio/`, `raw_data`, `conforms_to_standard: [BIDS]` | same, plus `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` | no conflict; same standard and version the full record states at top level |

Points of substance:

- **Names, paths and identifiers agree exactly.** The core distributions reuse
  the full collections' `id` values, so the mapping is traceable in one step
  rather than inferred from position.
- **Nested files are full-only.** `CoreDistribution` declares no nested file
  list, so the 11 `File` objects under `#collection-features` — the nine Parquet
  feature files with their record counts and the two TSV files — are omitted
  from the core projection, which the playbook allows for full-only nested
  slots. The one sentence of the features description that pointed at that list
  ("Counts below are for version 3.1.0.") was dropped in core rather than left
  dangling. Nothing else in any description differs.
- **`format` is populated only where the enum can express the truth.**
  `FormatEnum` has no Parquet or WAV term, so `format` is set only on the
  phenotype collection (`TSV`) and left absent on the other three, whose formats
  are stated in prose in both records. Setting `TSV` on the mixed features
  collection would have been false.
- **Checksums, byte counts and file counts are absent from both.** The bundle
  gives per-feature record counts (`n=29278` and so on), which are numbers of
  recordings rather than files or bytes, so `total_file_count`,
  `total_size_bytes`, `bytes`, `hash`, `md5` and `sha256` are unpopulated
  everywhere and no cross-check applies.
- **Access URLs are not duplicated into distributions.** Access routes live in
  `distribution_formats[].access_urls` (declared range `uri`) in both records —
  the PhysioNet 3.1.0 page, the Synapse project for raw audio, and the Health
  Data Nexus platform for the earlier feature-only version.
- **`dialect` agrees with the formats.** `delimiter: \t`, `header: true`, taken
  from the 3.1.0 usage note (`pd.read_csv("demographics.tsv", sep="\t",
  header=0)`) and the statement that all TSV data files carry a JSON data
  dictionary keyed by column name. This agrees with `distributions[phenotype]
  .format: TSV` and with the `format: TSV` on the full record's
  `static_features.tsv` and `audio_quality_metrics.tsv`. `is_tabular` is absent
  from core, as noted above.

### Identity, version and access facts

`id`, `doi`, `version`, `issued`, `page`, `status`, `license` and `language`
are schema-identical and therefore deeply identical across the pair. They were
checked for internal agreement against the version and distribution slots:

- `id: doi:10.13026/37yb-1t42` and `doi: 10.13026/37yb-1t42` match
  `version_access.latest_version_doi`, and the PhysioNet page labels that DOI
  "DOI (latest version)".
- `version: 3.1.0`, `issued: 2026-05-01T00:00:00Z` and
  `page: https://physionet.org/content/b2ai-voice/3.1.0/` agree with the last
  entry of `distribution_dates.release_dates` and with
  `version_access.versions_available`, both of which reproduce the PhysioNet
  version sidebar (1.1 / 2.0.0 / 2.0.1 / 3.0.0 / 3.1.0).
- **Historical releases are scoped, not contradicted.** Version 1.0 on Health
  Data Nexus appears in `related_datasets` as `is_new_version_of` and in
  `distribution_formats` as an explicitly earlier hosted version; the
  healthsheet answers written against versions 2.0.0 and 3.0.0 are retained
  with their release scope named in the text. These are different values for
  different releases, not disagreements.
- `license`, `license_and_use_terms`, `data_governance` and
  `regulatory_restrictions` agree on one access model: credentialed/registered
  access to the feature-only data through PhysioNet with a signed data use
  agreement and no required training, and controlled access to raw audio
  through the Data Access Compliance Office and Synapse.

### Identifier grounding

```
{'grounded': 1, 'minted_fragment': 130, 'absent': 0}
```

**Zero `absent` identifiers**: every identifier either appears in the declared
bundle or is a fragment minted on this dataset's own DOI CURIE to label a part
of this record. No organization ROR, no personal ORCID and no third-party DOI
was supplied from outside the evidence.

### Scope

`d4d download scope --check --project VOICE` reports that no record is about a
dataset its project declares distinct, and neither record in this pair appears
in the separate advisory list of records that place the pediatric release
outside its declared slot.

## Commands run

```bash
# Phase 1 artifact re-validation (resume gate)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Scope and source ranking
poetry run d4d download scope --project VOICE
poetry run d4d download priority --project VOICE

# Phase 2 / Phase 3 validation, re-run after every correction
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
# grounding check (data_sheets_schema.grounding.check_run)
# report-claims check (data_sheets_schema.report_claims.check_report)
poetry run d4d download scope --check --project VOICE
poetry run d4d runs check --strict
```

All validations returned `No issues found` / `Validation passed`. The pair
validator returned `PASS` on both the synchronizing and the final independent
run, with the standing `semantic-review-required` warning addressed above.

## Files changed in this invocation

| file | change |
|---|---|
| `.../claudecode_agent/<label>/VOICE_d4d.yaml` | Phase 3 corrections only: twelve consortium `affiliations` added; `source_caveats` item (11) added. No other value altered. |
| `.../claudecode_agent_core/<label>/VOICE_d4d_core.yaml` | written in Phase 2, re-projected after each Phase 3 correction |
| `.../claudecode_agent_core/<label>/VOICE_reconciliation.md` | this report |

## Result

Both records validate against their schemas and their ontology terms. All 79
schema-identical slots are deeply identical and identically present. The one
projected slot is absent from both. The one related-content mapping
(`file_collections` → `distributions`) was reviewed field by field with **no
unresolved contradiction within or between the two records**. No repair phase
was required: the grounding checker, the report-claims checker and the final
pair-consistency run each reported nothing requiring a change to either record.
