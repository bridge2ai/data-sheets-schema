# VOICE full/core reconciliation — crate-only, de-primed, replicate 2

- **Version label:** `2026-07-28_claude-opus-5-crateonly-deprimed_rep2`
- **Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`, temperature 0.0
- **Mode:** four-phase project agent (Phase 1 full, Phase 2 core, Phase 3 audit, Phase 4 reconciliation)
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_crate_only.txt`
- **Source manifest:** not used — this arm declares a single source bundle
- **Full:** `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d_core.yaml`
- **Repo commit at generation:** `0e19e85f`

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, searched, or cited. The only files opened for factual
content were the declared bundle (`VOICE_crate_only.txt`) and the two LinkML schemas. No file
under `data/d4d_concatenated/`, `data/d4d_individual/`, or `data/ro-crate_packages/` was read,
and `data/preprocessed/source_manifest.yaml` was not opened. The Phase 2 core record was
derived from the exact same-run Phase 1 full record (path carries this run's label) plus the
same bundle. Structure for both records was resolved at runtime from `Dataset` in
`data_sheets_schema_all.yaml` and `CoreDataset` in `data_sheets_schema_core_all.yaml` via
`SchemaView`; no `d4d:docExample` value was copied.

One incident worth recording: the session scratchpad is shared with concurrent agents, and an
intermediate build script written under a generic name was overwritten by another agent's
script, which produced a truncated core file. This was detected immediately, and the core
record was rebuilt from the Phase 1 full record with uniquely named artifacts and
re-validated. No foreign content entered either output; both files were re-validated after the
rebuild.

### What the bundle actually contains

The bundle is a reduced FAIRSCAPE/RO-Crate JSON-LD graph (75 nodes, `fairscapeVersion`
1.0.24, conforming to RO-Crate 1.2) plus an AI-readiness self-assessment. The graph holds one
root dataset entity, 15 data entities, 53 unique column schemas (55 schema nodes, two ids
duplicated), 1 software entity, and 2 computation activities. Substantive prose is concentrated
in the root entity's Croissant `rai:*` fields, which carry the collection, preprocessing,
annotation, bias, limitation, use-case, sensitivity, social-impact and maintenance narratives.
The AI-readiness file adds no dataset facts beyond restating crate values, except for two
counts (`15 dataset(s) documented`, `65% of files have checksums (11/17)`).

### Values verified against the bundle

Checked programmatically against the parsed crate JSON, all matching exactly:

- identity: `name`, `title`, `version` (3.0.0), `doi`, `license`, `publisher`, `citation`,
  all 18 `keywords`
- 117 `creators`, in the crate's declared author order, with no additions or omissions
- 15 `file_collections` ↔ 15 crate data entities: ids, declared names, byte sizes, content
  URLs all identical
- 11 `sha256` values in core `distributions`, all identical to the crate

`total_size_bytes` (13,789,023,450) is the arithmetic sum of the 11 declared file sizes. It is
consistent with the crate's declared `contentSize` of "12.9 GB" when that string is read as
GiB (12.84 GiB). Recorded as derived, not as a crate-declared scalar.

Of 130 narrative strings longer than 140 characters in the full record, 50 are verbatim crate
text (whitespace- and case-normalized). The remainder are composed from crate content: label
prefixes stripped from the `rai:dataBiases` segments, sentences recombined across `rai:*`
fields, or descriptions of crate structure written for a schema slot that has no crate
counterpart. No narrative asserts a fact absent from the crate.

### Source-quality defects found in the crate (recorded, not silently repaired)

1. `b2ai-voice-dataset-feature-sparc-periodicity` carries the name `sparc_loudness.parquet`
   while its content URL and schema are the periodicity ones.
2. `b2ai-voice-dataset-feature-torchaudio-pitch` carries the name
   `torchaudio_spectrogram.parquet` while its content URL and schema are the pitch ones.
3. `b2ai-voice-dataset-phenotype-task` carries the name `VOICE Questionnaire Tables`,
   duplicating the questionnaire group's name.
4. Schema id `ark:59853/b2ai-voice-schema-phenotype-confounders` is used twice, once for
   "Phenotype Confounders Schema" and once for "Phenotype Demographics Schema"; schema id
   `...-phenotype-voice-perception` is likewise duplicated.
5. Every data entity's `description` is placeholder text ("a datafile description" /
   "A Dataset description"). No per-file description exists in the crate.
6. `b2ai-voice-dataset-feature-ppgs` uses the key `size`; every other sized entity uses
   `contentSize`.
7. `sparc_pitch.parquet` is dated 08/18/2025 while the root and every other entity are dated
   12/16/2025.
8. The `VOICE Features Processing` computation is dated 01/29/2026, i.e. after the dataset's
   own `datePublished` of 12/16/2025.
9. `copyrightNotice` asserts 2026 while the release is dated 2025-12-16.
10. `irbProtocolId` and `completeness` are present but empty.
11. `hasPart`, `isPartOf` and `EVI#inputs` on the root are empty arrays, so the crate does not
    itself link its root to its parts; `EVI#outputs` was collapsed to a count of 15 by the
    bundle's own reduction step, which the bundle header discloses.
12. The IRB `contactPoint` places a phone number in the `contactType` field.
13. `static_features.tsv` is named in `rai:dataPreprocessingProtocol` and has a declared
    135-column schema, but no data entity for it exists in the graph. The AI-readiness count
    of "11/17" files with checksums does not reconcile with the 15 data entities in the graph.
14. Schema entities declare `"separator": ","` while the same phenotype files are declared
    `text/tab-separated-values`.

Consequences for the records: defects 1–3 are reproduced as declared, with the mismatch stated
in the corresponding `description` so the record neither hides nor silently corrects the source.
Defect 14 is why `dialect` is left absent in core — the crate gives contradictory delimiter
evidence, so no delimiter is asserted. Defects 8, 9 and 13 are recorded here only; neither
record asserts a `created_on`, `last_updated_on` or `total_file_count` value, because the
available candidates are activity dates or counts that do not reconcile.

### Correction applied during Phase 3

The four phenotype table-group entities (`diagnosis`, `enrollment`, `questionnaire`, `task`)
originally carried descriptions that named the specific column schemas belonging to each group.
The crate declares those schemas but never links a schema entity to a table-group entity, so
the grouping was an inference presented as a crate fact. All four descriptions were rewritten
to name the schemas and state explicitly that the correspondence is not asserted by the crate.
The full record was corrected first, both validations re-run, and core was then regenerated
from the corrected full record so the change propagated to the projected `distributions`
descriptions.

### Interpretations recorded (evidence-anchored, not crate-literal)

- `language: en` — from "fluent English speakers", "early releases focus on English, with
  Spanish protocols planned but not yet fully represented", and the `selected_language` column.
- `issued: 2025-12-16` — `datePublished` "12/16/2025" read as MM/DD/YYYY. Corroborated by
  `sparc_pitch`'s "08/18/2025", which matches the crate's own v2.0.1 release date of
  2025-08-18.
- Enum mappings: five `bias_type` values, five `limitation_type` values,
  `confidentiality_level: restricted` (from "Limited dataset available with Data Use
  Agreement"), `data_use_permission: [health_medical_biomedical_research, user_specific]`
  (from the registered-access/authorized-researcher language), and `Maintainer.role` values.
- `at_risk_groups_included: true` — from the crate's own enumeration of cognitive impairment,
  psychiatric history, PTSD, bipolar disorder, depression, anxiety, Parkinson's disease, ALS
  and laryngeal cancer cohorts. The slot's `description` states this basis.
- `is_tabular: true` — every released entity is a Parquet or TSV table with a declared or
  declarable column schema.
- `variables` holds 17 entries: the cross-cutting keys and the payload column of each feature
  table. The crate declares roughly 2,562 columns across 53 unique schemas; enumerating them
  would reproduce a data dictionary rather than describe the dataset, so the record documents
  the key and payload columns and leaves the rest to the crate's schemas.

### Fields deliberately left absent

`total_file_count`, `compression`, `download_url`, `page`, `status`, `created_on`,
`created_by`, `modified_by`, `last_updated_on`, `was_derived_from`, `conforms_to_class`,
`subsets`, `parent_datasets`, `collection_notifications`, `consent_revocations`,
`participant_compensation`, `existing_uses`, `use_repository`, `extension_mechanism`,
`resources`, and core-only `dialect`. In each case the crate either says nothing or gives
only contradictory or out-of-scope candidates. No Phase 2 discovery required back-porting into
the full record: every core slot the full record left empty was empty because the crate
supports nothing, not because the full extraction missed it.

### Assessment of the crate as an evidence source

The crate is strong on governance and process narrative and on file-level provenance, and weak
on per-file semantics. The `rai:*` block is unusually complete — collection, preprocessing,
annotation, imputation, bias, limitation, sensitivity, use-case and maintenance narratives are
all present and detailed, which is what allowed most of the ethics, collection, preprocessing,
uses and maintenance sections to be populated from a single structured source. Against that,
every per-file description is placeholder text, four of fifteen data entities have no size,
checksum or content URL, three entities carry a demonstrably wrong name, and the 53 column
schemas are not linked to the entities they describe. Dataset-level counts are asserted in
prose (833 participants, five sites) but not as structured fields, and the crate's own internal
counts do not fully reconcile. The result is a record that is well populated on narrative and
provenance and thin on file-level semantics — a shape that follows directly from the source
rather than from any target.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView`, not from a hand-written list.

- **Schema-identical shared slots:** 76
- **Projected slots (range differs):** `resources` (`Dataset` in full, `CoreDataset` in core) —
  absent from both records, so coverage is trivially equal
- **Full-only slots:** 17 — `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`
- **Core-only slots:** 2 — `distributions`, `dialect`
- **Populated slots:** full 73 of 94; core 63 of 79
- **Shared slots populated in both:** 62, all deeply identical (every nested mapping value and
  list item in the same order). No narrative was condensed, paraphrased, reordered or omitted
  in core. Verified independently of the validator by parsed-value comparison.

`--sync-core` was not needed: core was generated by projecting the Phase 3-corrected full
record through the `CoreDataset` slot inventory, so identity held by construction. The
validator was run once, without `--sync-core`, as the final independent check.

### Semantic review of related, non-identical content

`file_collections` (full) ↔ `distributions` (core), 15 ↔ 15, matched 1:1 by `id`, zero
unmatched on either side:

- **names and descriptions** — identical strings in both records, including the three
  reproduced crate name/URL mismatches and the four "not asserted by the crate" grouping
  statements.
- **paths** — identical; the crate's `contentUrl` values are within-crate `file:` URIs and are
  recorded as `path` in both, not as download URLs.
- **byte counts** — `FileCollection.total_bytes` equals `CoreDistribution.bytes` for all 11
  sized entities; the four table groups carry no size in either record, matching the crate.
- **checksums** — present only in core, because `FileCollection` has no checksum slot in the
  full schema. All 11 `sha256` values verified against the crate. This is a schema-driven
  asymmetry, not a divergence.
- **formats and media types** — present only in core, because `FileCollection` has no format
  slot. `TSV` / `text/tab-separated-values` assigned to the six phenotype entities from the
  crate's declared `format` field. The nine Parquet entities have an empty crate `format`
  field and Parquet is absent from the core `FormatEnum`, so both fields are omitted for them
  rather than guessed.
- **compression** — not declared anywhere in the crate; absent from both records.
- **access URLs** — no per-entity access URL exists in the crate. Dataset-level access URLs
  live in `distribution_formats.access_urls`, a schema-identical slot, and are identical in
  both records.
- **release scope** — every entity carries `version: 3.0.0` and `issued: 2025-12-16` in both
  records, except `sparc_pitch`, whose crate-declared 2025-08-18 date is preserved in both and
  flagged in its description.

Scope comparisons:

- `total_file_count` is absent from full and has no core counterpart — no conflict.
- `total_size_bytes` (full, 13,789,023,450) equals the sum of the 11 core `distributions.bytes`
  values exactly. The scopes agree: the total covers precisely the sized entities, and the four
  unsized table groups contribute nothing on either side.
- `is_tabular: true` is a schema-identical slot, identical in both, and agrees with the
  Parquet/TSV format assignment in `distributions` and with `distribution_formats`.
- `dialect` (core-only) is absent by decision, so no format-detail conflict can arise.

Identity, version and access facts were cross-checked across the two records and within each:
`id`, `doi`, `version`, `license`, `publisher`, `issued`, `citation` (full only),
`version_access.latest_version_doi`, `distribution_dates.release_dates`,
`license_and_use_terms.license_terms`, `regulatory_restrictions`, and the per-entity `version`
and `issued` values all agree. The v3.0.0 release (2025-12-16) is consistently distinguished
from the historical releases v1.0, v1.1, v2.0.0 and v2.0.1, which appear only in
`distribution_dates`, `version_access.versions_available` and `related_datasets` with explicit
historical scope. No contradiction remains within or between the two records.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d_core.yaml

poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d.yaml` (created Phase 1; four descriptions corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_d4d_core.yaml` (created Phase 2; regenerated after the Phase 3 correction)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/VOICE_provenance.yaml` (live provenance record)

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass |
| Full ontology term validation | pass |
| Core schema validation (`CoreDataset`) | pass |
| Core ontology term validation | pass |
| Schema-derived pair consistency | PASS — 76 schema-identical slots, 1 projected slot |
| Shared populated slots deeply identical | 62 / 62 |
| Related-content semantic review | complete — 15/15 matched, zero contradictions |
| Prior-D4D reuse | none |
