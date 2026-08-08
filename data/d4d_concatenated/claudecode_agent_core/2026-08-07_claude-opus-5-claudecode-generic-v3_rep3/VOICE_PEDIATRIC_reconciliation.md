# VOICE_PEDIATRIC full/core reconciliation

- Run label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep3`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic prompt
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5
- Reasoning effort: `high` (observed value of `$CLAUDE_EFFORT`)
- Temperature: 0.0
- Declared input bundle: `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d_core.yaml`

## Chosen referent

`Dataset` admits one referent. This record describes the **Bridge2AI-Voice
Pediatric Dataset v1.1.0**, the credentialed-access PhysioNet database published
2026-05-01 under DOI `10.13026/h995-bt35`, containing derived audio features for
23,533 recordings from 300 participants aged 2-18 recruited at the Hospital for
Sick Children. The record identifier is the version 1.1.0 DOI rather than the
latest-version DOI (`10.13026/mf9s-5r03`), which is recorded separately under
`version_access.latest_version_doi`.

The referent is *not* the Bridge2AI-Voice adult dataset, *not* the
Bridge2AI-Voice release programme as a whole, and *not* the underlying
Bridge2AI Voice Data Acquisition study. The bundle contains substantial material
about all three; how each was treated is set out under Phase 3 below.

## Relationship to the adult VOICE dataset

The adult dataset is represented only through the full record's
`related_datasets` slot, in two entries, and nowhere else:

| target | relationship_type | basis in the bundle |
|---|---|---|
| Bridge2AI-Voice Adult Dataset (`https://physionet.org/content/b2ai-voice/`) | `references` | The pediatric PhysioNet page states "Note that the Bridge2AI-Voice Adult Dataset is also available on PhysioNet: https://physionet.org/content/b2ai-voice/", and the documentation advertises adult v3.1.0 alongside pediatric v1.1.0 as separate PhysioNet links under registered access. |
| Bridge2AI-Voice dataset (NIH Bridge2AI Common Fund flagship voice dataset) | `is_part_of` | "The Bridge2AI Voice consortium has also prepared a pediatric dataset"; the documentation presents adult and pediatric releases together as the Bridge2AI-Voice dataset. |

`DatasetRelationshipTypeEnum` has no value for a companion or sibling release.
`is_version_of`, `has_version`, `is_new_version_of`, `derives_from` and
`supplements` would each assert something the bundle explicitly contradicts —
the manifest curation note and the PhysioNet pages agree that the two are
distinct cohorts under separate protocols and that the pediatric project is not
a version of the adult one. `references` was therefore chosen as the weakest
claim that the documented cross-reference actually supports, and a
`source_caveats` on that entry records why.

`related_datasets` is a full-only slot: `CoreDataset` does not declare it, so the
core record carries no reference to the adult dataset. That is a schema
consequence, not an omission.

## Phase 3 - source and provenance audit

### Provenance boundary

No prior D4D record, from any arm, label or date, was read, opened, grepped or
consulted. Factual inputs were exactly:

- `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
- the `VOICE_PEDIATRIC` block of `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (structure only)

`data/preprocessed/concatenated/VOICE_preprocessed.txt` was not read. One `ls` of
`data/d4d_concatenated/claudecode_agent/` returned directory names only; no file
under `data/d4d_concatenated/` was opened other than this run's own two outputs,
and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was touched. All record
structure was derived at runtime from the two schemas with LinkML `SchemaView`;
no prior YAML was used as a template and no `d4d:docExample` value was copied.

### Scope discipline within a shared corpus

The bundle's six documents differ sharply in scope. Only the PhysioNet
`b2ai-voice-pediatric` 1.1.0 page is scoped wholly to the referent. The
documentation site (`docs.b2ai-voice.org`) mixes pediatric-specific passages with
a healthsheet and study-metadata block written for the adult releases; the IRB
protocol is the USF-centred consortium protocol; the NIH RePORTER page describes
the parent award; the DTUA is the consortium-wide transfer agreement; the GitHub
README describes the documentation repository.

Facts were taken from pediatric-scoped statements wherever they exist.
Consortium-wide statements were used only where the pediatric release falls
inside their scope, and each such use carries a `source_caveats` naming the
document (`confidential_elements`, `consent_revocations`,
`cleaning_strategies[inadvertent_caregiver_audio]`, `discouraged_uses`,
`regulatory_restrictions`, `retention_limit`, `ethical_reviews`).

Adult-scoped assertions deliberately **not** carried into this record:

- 833 participants / ~61,937 recordings, and the "around 833 instances" answer
- v2.0.0 / v3.0.0 release dates, DOIs, and the v3.0.0 de-identification methods
- "five recording sites", "collected over a period of 12 months", "iPads (9th or
  10th generation) ... Avid AE-36 microphone" (device block in the adult
  healthsheet)
- the Health Data Nexus hosting, semi-annual update cadence, erratum answer and
  extension answer, all of which describe the earlier HealthDataNexus release
- "not representative because it was collected at a limited number of geographic
  locations", the sensitive-category list, the labeling answers, the
  Summer School / hackathon existing use, and the "no predefined data splits"
  answer

The last group is the reason `collection_timeframes`, `splits`,
`existing_uses`, `labeling_strategies`, `future_use_impacts`, `errata` and
`content_warnings` are absent: the bundle carries answers to all of them, but
each is scoped to the adult cohort, and an absent slot is the correct answer when
the pediatric evidence is absent.

### Internal consistency checks

Identifiers, counts, dates and licences that recur across slots were checked for
agreement: DOI `10.13026/h995-bt35` (`id`, `doi`, `citation`, `version_access`);
version `1.1.0` and `issued` 2026-05-01 against `distribution_dates` and
`version_access.versions_available`; 300 participants and 23,533 recordings
against `instances`, `description` and the per-file counts in `file_collections`;
the 23,533 / 23,532 split against `anomalies` and `missing_data_documentation`;
`license` against `license_and_use_terms.license_terms`; the Synapse identifier
`syn73617068` and `DACO@b2ai-voice.org` across `raw_data_sources`, `raw_sources`,
`external_resources`, `known_limitations` and `maintainers`. No internal conflict
remained.

### Shape audit

Every emitted slot was checked against its induced range: no prose in a
multivalued slot, no enum value outside its permissible set (`selection_bias`,
`measurement_bias`, `scope_limitation`, `representativeness_limitation`,
`coverage_limitation`, `processed_data`, `metadata`, `data_file`, `TSV`, `JSON`,
`identifier`, `categorical`, `integer`, `general_research_use`, `restricted`,
`academic_institution`, `other`, `references`, `is_part_of`, and the CRediT
roles), and no commentary embedded inside a name, identifier or affiliation.
Evidence commentary was routed to `source_caveats`, narrative to `description`,
and `notes` used only for content `description` cannot hold.

`hipaa_compliant` was deliberately left unset. The DTUA states the Data "is not
covered under HIPAA", while the adult-scoped documentation answers "Yes" to
applying the HIPAA de-identification rules; no value of `ComplianceStatusEnum`
represents that pair honestly, so the two statements are recorded verbatim in
`regulatory_restrictions.other_compliance` instead. `dialect` was left unset
because the release mixes Parquet, TSV and JSON and no single dialect describes
it.

### Corrections made during Phase 3

Nine edits were applied to the full record and then propagated to core:

1. `citation` and `creator:jean_christophe_belisle_pipon.name` — restored the
   accented spelling "Bélisle-Pipon" used by the source.
2. `creator:vardit_ravitsky.description` — removed "contributing to the
   consortium's ethics work"; the bundle lists Ravitsky as a lead investigator
   but does not attribute that role to this individual.
3. `creator:jean_christophe_belisle_pipon.description` — same removal, same
   reason.
4. `creator:satrajit_ghosh.credit_roles` — `supervision` replaced by
   `investigation`, matching the treatment of the other cohort leads, whose
   evidenced role in Annex C is "Lead <cohort>".
5. `at_risk_populations.special_protections` — removed "Individuals who were
   non-verbal were excluded from the pediatric study". Exclusion is an
   eligibility criterion, not a protection; it is already recorded under
   `sampling_strategies` and `known_biases`.
6. `retention_limit` — added `source_caveats` scoping the two-year term and
   destruction certification to the consortium-wide DTUA governing transfers to
   a recipient institution, since the bundle states no retention limit for the
   registered-access featurized release itself.
7. `notes` — rewritten. The original restated `version_access.latest_version_doi`
   and the raw-audio facts already carried by `raw_data_sources`,
   `known_limitations` and `external_resources`. It now carries only content no
   sibling slot holds: the RRID and PhysioNet's own platform-citation
   requirement.
8. Added `data_protection_impacts` for the memorandum "Ethical Justification for
   Controlled Access to Raw Voice Data Samples", which the documentation
   publishes as the reasoning behind the governance structure separating
   registered access to features from controlled access to raw audio.

No Phase 2 discovery required a back-port: core was derived from the validated
Phase 1 full record plus the same bundle, and the source re-read during Phase 2
surfaced no fact missing from or contradicting the full record.

## Phase 4 - strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with
LinkML `SchemaView` via `data_sheets_schema.d4d_pair_consistency`; no
hand-written field list was used.

- Schema-identical shared slots: **78**
- Projected shared slots: **1** (`resources`)
- Schema-identical slots populated in this pair: **56**, all deeply identical and
  present in both records
- Full-only slots populated (12): `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `participant_compensation`, `participant_privacy`,
  `related_datasets`, `relationships`, `third_party_sharing`, `variables`
- Core-only slot populated (1): `distributions`
- `resources` is absent from both records, so the projection rule is satisfied
  vacuously. `dialect` is absent from core.

Core was generated by copying the 56 shared slots from the audited full record
verbatim, preserving key order, list order and every nested mapping. Nothing was
condensed, paraphrased, reordered or omitted, including narrative fields.

Slot totals: full **69** top-level slots, core **58**.

### Related-content review: `file_collections` -> `distributions`

The validator's `semantic-review-required` warning was reviewed rather than
accepted. `FileCollection` and `CoreDistribution` have different shapes:
`CoreDistribution` has no `collection_type` and no nested `resources`, so the
full record's two-level structure is flattened in core.

| full `file_collections` | core `distributions` | basis |
|---|---|---|
| `collection:features` (11 nested `File` resources) | folder entry `collection:features` **plus** the 11 file entries `file:torchaudio_spectrograms_parquet` … `file:audio_quality_metrics_tsv` | deterministic match on the folder entry; the 11 file entries are strictly finer granularity inside it |
| `collection:phenotype` | `collection:phenotype` | deterministic match |
| `collection:metadata` | `collection:metadata` | deterministic match |

Deterministic matches: 3 of 3 full collections. The 11 indices the validator
reports as unmatched (`[1..11]`) are exactly the file-level entries; each has a
`path` under `features/` that is a child of the matched folder's `path`, so none
of them can conflict with a collection.

Field-by-field: `name`, `path`, `description`, `format` and `media_type` were
copied unchanged from the corresponding full objects, so no value differs.
`compression`, `bytes`/`total_bytes`, `hash`, `md5`, `sha256`, `encoding` and
checksums are unset in both records — the bundle publishes no sizes, checksums
or compression for the release. No access URL is attached at distribution level
in either record; access points live in `distribution_formats.access_urls` and
`page`, which are schema-identical and therefore already deeply equal.

Release scope agrees: both records describe version 1.1.0 only, and the version
1.0.0 material appears in both solely under `version_access` and `updates`,
labelled as the superseded first release. `total_file_count` and
`total_size_bytes` are unset in full, so there is no count or size to compare
against distribution-level values.

`is_tabular` is `true` in both. It is consistent with the distribution formats:
every distributed data file is either a Parquet table ("an open-source
column-oriented data file format") or a tab-delimited table. `dialect` is unset
in core, so there is nothing for it to disagree with.

Top-level identity, version and access facts (`id`, `doi`, `version`, `issued`,
`license`, `page`, `publisher`, `language`, `conforms_to`) are schema-identical
slots and are byte-for-byte equal across the pair; they agree with
`version_access`, `distribution_dates`, `license_and_use_terms` and
`regulatory_restrictions` in both files. The historical release (1.0.0,
2025-12-17) is distinguished from the current release (1.1.0, 2026-05-01)
throughout rather than treated as a contradiction.

### Divergences

None. Every schema-identical shared slot has identical presence and deeply
identical parsed content in both records; every projected and related field has
been mapped and reviewed with zero unresolved contradictions within or between
the two records.

## Commands run

```bash
echo "$CLAUDE_EFFORT"                                    # -> high

poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_PEDIATRIC_d4d_core.yaml

poetry run d4d provenance record --project VOICE_PEDIATRIC --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 --project VOICE_PEDIATRIC
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3
```

`--sync-core` was not used: core was generated from the audited full record, so
there was nothing to synchronize, and the validator was run only as an
independent check.

## Final results

| check | result |
|---|---|
| full schema validation (`Dataset`) | pass, no issues found |
| full ontology-term validation | pass |
| core schema validation (`CoreDataset`) | pass, no issues found |
| core ontology-term validation | pass |
| full/core pair consistency | PASS — 78 schema-identical slots, projected `['resources']`, 0 errors, 1 semantic-review warning (reviewed above) |
| full top-level slots | 69 |
| core top-level slots | 58 |
| divergences requiring correction in Phase 4 | none |

Line counts are informational metadata only and are not a quality gate.
