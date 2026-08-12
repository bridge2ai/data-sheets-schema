# VOICE_PEDIATRIC full/core reconciliation

- Run label: `2026-08-11_claude-opus-5-claudecode-generic_rep3`
- Arm: BASELINE (input documents only)
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5
- Mode: four-phase project agent, generic prompt
- Declared input bundle: `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
  (md5 `008212accc7ec95bf3f0121566b588c2`, which is the post-#427 value the
  manifest records for this project — the bundle read was the current one)
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d.yaml`
  (md5 `c65fff180e5a2d126dc6cfc6e8935e64`, 67 populated top-level slots)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d_core.yaml`
  (md5 `a6cd0da0d9079e6726857bec5c05eca7`, 55 populated top-level slots)

## Referent

`Dataset` admits one referent. This record is about the **Bridge2AI-Voice
Pediatric Dataset**, the PhysioNet project `b2ai-voice-pediatric`, as described
by its version 1.1.0 landing page. The `id` is the PhysioNet latest-version DOI
`https://doi.org/10.13026/mf9s-5r03`; `doi` carries the version-1.1.0 DOI
`https://doi.org/10.13026/h995-bt35`, and `version_access.latest_version_doi`
repeats the former. Both records hold the same referent and the same identifiers.

The Bridge2AI-Voice **adult** dataset is a separate PhysioNet project and appears
only in `related_datasets` (`relationship_type: references`, target
`https://physionet.org/content/b2ai-voice/` — the value the bundle itself
supplies). No adult identifier or URL appears in `distribution_formats`,
`file_collections`, `external_resources` or `resources`.

## The bundle's composition, and what it forced

Only one of the six documents in the bundle
(`physionet_b2ai-voice-pediatric_1.1.0_2026-07-24.txt`) is about this dataset.
The other five — the project documentation site, the USF IRB protocol, the NIH
RePORTER page, the Data Transfer and Use Agreement, and the documentation
repository README — describe the Bridge2AI-Voice study and consortium, and large
parts of the documentation site describe the adult dataset explicitly (its
healthsheet answers are scoped to adult releases v2.0.0 and v3.0.0, including
833 participants, ~61,937 recordings, a 12-month collection window, five
recording sites, iPad/Avid AE-36 hardware, and clinician diagnostic labelling).

Where a study-level or consortium-level document is the only source for a value,
the value is populated and the scope is named in that object's `source_caveats`
(`consent_revocations`, `participant_compensation`, `confidential_elements`,
`ip_restrictions`, `regulatory_restrictions`, `discouraged_uses`,
`ethical_reviews[usf_single_irb]`, `retention_limit`, `updates`,
`data_collectors`). Where a statement is made *only* about the adult dataset, it
is omitted rather than transferred. Slots left absent for that reason, and named
in the top-level `source_caveats`:

- `known_biases` — the "skews based on disorder category, site, and other
  demographic factors" answer is an adult-release healthsheet answer.
- `collection_timeframes` — "collected over a period of 12 months" is adult.
- `labeling_strategies`, `annotation_analyses`, `machine_annotation_tools` — the
  clinician-labelling protocol and off-the-shelf transcription models are adult.
- `existing_uses`, `use_repository`, `other_tasks`, `future_use_impacts` — the
  summer school / hackathon use and the "no repository" answer are adult.
- `splits` — "no predefined recommended data splits" is adult.
- `content_warnings` — the free-speech transcription warning is adult; the
  pediatric release states instead that free-speech features were manually
  checked for unconsented speakers and PII before release.
- `data_protection_impacts` — the "No" answer is adult.
- `errata` — the pediatric page publishes release notes, not an erratum.
- `total_file_count`, `total_size_bytes`, `file_count`, `total_bytes` — no counts
  or byte sizes for the release appear in the bundle.
- `is_deidentified.identifiers_removed`, `subpopulations.distribution` — the
  pediatric page gives no field-level removal list and no demographic
  distribution.

This is the load-bearing finding of the run: the bundle is largely about a
dataset this project declares distinct, and the honest record is correspondingly
sparser than a naive read of the bundle would produce.

## Phase 3 — source and provenance audit

### Provenance

- Inputs read: the declared bundle, `data/preprocessed/source_manifest.yaml`,
  `data_sheets_schema_all.yaml`, `data_sheets_schema_core_all.yaml`,
  `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`.
- No prior D4D record was read, opened, grepped or listed. Nothing under
  `data/d4d_concatenated/`, `data/d4d_individual/` or `data/ro-crate_packages/`
  was consulted; the only generated YAML read in Phase 2 was the exact same-run
  Phase 1 full record under this run's label.
- Structure was derived at runtime from the schemas with `SchemaView`
  (`class_induced_slots` over `Dataset`, `CoreDataset` and every nested range),
  not from any example record. No `d4d:docExample` value was copied.
- `d4d api prompts check --strict`: 10 prompt files, 0 not at their pin. The
  generic arm prompt this run is labelled with is at its canonical pin.

### Corrections made in Phase 3 (all applied to full first, then re-projected to core)

1. **Fabricated author count.** The consortium creator entry asserted "130
   individual authors" for the v1.1.0 citation. Counting the BibTeX author field
   in the bundle gives **121**. Corrected.
2. **Fabricated ORCID-shaped identifier.** The first creator carried
   `id: https://orcid.org/creator/bensoussan-yael`, an identifier that looks like
   an ORCID and is in no source document. Replaced with the non-asserting token
   `creator_bensoussan_yael`.
3. **Institution homepage URLs from model memory.** Twelve `Organization` ids
   were institutional homepage URLs (`https://www.usf.edu/`,
   `https://weill.cornell.edu/`, `https://www.sickkids.ca/`, …). None appears in
   the bundle. Replaced with non-asserting tokens (`org_university_of_south_florida`,
   `org_weill_cornell_medicine`, `org_hospital_for_sick_children`, …).
4. **Non-inlined `Person` ranges.** `Creator.principal_investigator` and
   `DataGovernance.committee_contact` are `Person` referenced by identifier, not
   inlined. The nested Person objects failed schema validation; the PI detail
   moved into the creator's `description` and the committee contact became the
   identifier `mailto:DACO@b2ai-voice.org`. No commentary is embedded in an
   identifier value.
5. **Over-claiming `conforms_to`.** Top-level `conforms_to: Brain Imaging Data
   Structure (BIDS)` was removed. The bundle says pediatric data is extracted to
   REDCap format and *subsequently converted* to BIDS — a pipeline statement —
   while the published release is laid out as `features/`, `phenotype/` and
   `metadata/`, not as the BIDS tree the documentation shows. The BIDS statement
   remains in `preprocessing_strategies`, which is what the source supports.
6. **Transcription fidelity.** `Bélisle-Pipon` was restored to its accented form
   in the citation and in the creator name.

### Source disagreements found and how they were represented

- **Name spelling.** The PhysioNet author list gives "Jennifer Siu"; the project
  documentation gives "Jennifer Sui, MD" as the Hospital for Sick Children lead.
  Both are carried: the PhysioNet spelling is used as the creator `name`, and the
  discrepancy is stated in that creator's `source_caveats`. The two were not
  silently merged into one preferred spelling.
- **Two DOIs for one dataset.** The page gives a version-1.1.0 DOI
  (`10.13026/h995-bt35`) and a latest-version DOI (`10.13026/mf9s-5r03`). Both
  are carried, in `doi` and in `id`/`version_access.latest_version_doi`
  respectively, and the distinction is stated in `version_access.version_details`.
- **Participant count across sources.** The documentation site says "The
  pediatric dataset v1.0 is now available containing data from 300 participants"
  and separately announces v1.1.0; the PhysioNet v1.1.0 page says 300
  participants and adds that v1.1 released no new participants. These agree, and
  the reconciliation is stated in `instances[participant].description` rather
  than left implicit.
- **Feature row counts.** The torchaudio and PPG files carry 23,533 rows, the
  four SPARC files 23,532. Recorded as a `DataAnomaly` and as
  `missing_data_documentation`, with the release's own explanation (some files
  could not generate certain features) rather than as an error.
- **Which ethics approval governs.** The pediatric release cites the Research
  Ethics Board at the Hospital for Sick Children. The USF protocol says revision
  V2 brought the pediatric cohort under the single IRB, and also says Canadian
  institutions including SickKids do not abide by the single IRB and apply
  separately. Both reviews are recorded as separate `ethical_reviews` entries;
  `human_subject_research.ethics_review_board` names the SickKids REB, which is
  the approval the dataset itself cites.
- **Compensation.** `participant_compensation.compensation_provided: false` rests
  on the protocol's "Compensation will be provided to the adult population only".
  Its `source_caveats` records that this is a USF-held protocol statement and
  that the SickKids REB application, under which pediatric collection actually
  ran, is not in the bundle.
- **HIPAA.** The protocol's HIPAA-compliance statements are made about US
  collection sites; the pediatric cohort was collected in Canada. No
  `hipaa_compliant` value is asserted, and `regulatory_restrictions.source_caveats`
  says why.

### Shape and slot-filling audit

- No prose sits in a slot whose range is a list, and no enum value outside the
  schema's permissible values is used (`credit_roles`, `collection_type`,
  `limitation_type`, `data_use_permission`, `confidentiality_level`,
  `role`, `data_type` all checked against the induced enums).
- Structured slots are filled before prose: `creators[].affiliations`,
  `funders[].grants[].grant_number`, `variables[].variable_name`,
  `instances[].counts`, `distribution_dates[].release_dates` carry their content
  rather than leaving it in narrative.
- Evidence commentary is in `source_caveats` only; `notes` is unused in both
  records. No sibling value is restated.
- `data_topic` and `data_substrate` are ontology-term slots (`values_from:
  B2AI_TOPIC`). The bundle supplies no ontology terms, so both are omitted and
  the instance characterisation sits in `instance_type`, which is ranged
  `string` for exactly that.
- Parquet has no `FormatEnum` or `MediaTypeEnum` member, so the parquet `File`
  entries carry `path` and `description` and no format value; the TSV entries
  carry `format: TSV` and `media_type: text/tab-separated-values`.

### Phase 2 discoveries back-ported to full

None. Phase 2 derived core from the validated Phase 1 full record plus the same
bundle and found no core field the full record had left empty and no value the
sources contradicted. The Phase 3 corrections listed above were applied to full
first and core was re-derived from the corrected full record.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

- Schema-shared slot names between the two classes: **79**.
- Schema-identical slots checked by the validator: **78** (`resources` is a
  projection, `Dataset` in full and `CoreDataset` in core).
- Populated shared slots: **54**, all present in both records and all deeply
  identical by parsed-YAML comparison, including every narrative field. Core
  condenses, paraphrases, reorders and omits nothing.
- Full-only populated slots (13, none of which `CoreDataset` declares):
  `citation`, `file_collections`, `relationships`, `direct_collection`,
  `collection_notifications`, `collection_consents`, `consent_revocations`,
  `participant_privacy`, `participant_compensation`, `third_party_sharing`,
  `data_governance`, `variables`, `related_datasets`.
- Core-only populated slot (1): `distributions`.
- `resources` is absent from both records, so the projection is trivially
  covered.

### Related-content mapping and semantic review

`file_collections` (full) → `distributions` (core). Three collections, three
distributions, matched by `id`; no unmatched core distribution.

| id | full `FileCollection` | core `CoreDistribution` | reviewed |
|---|---|---|---|
| `features` | `path: features`, `collection_type: processed_data`, 11 nested `File` entries | `path: features` | name, path and description byte-identical; no format, compression, checksum or byte count is claimed on either side, so nothing can conflict |
| `phenotype` | `path: phenotype`, `collection_type: processed_data` | `path: phenotype` | identical name, path, description |
| `metadata` | `path: metadata`, `collection_type: metadata` | `path: metadata` | identical name, path, description |

Projection losses, deliberate and documented:

- `CoreDistribution` has no nested file list, so the 11 `File` entries under
  `features` (nine parquet feature files with their row counts and extraction
  parameters, `static_features.tsv`, `audio_quality_metrics.tsv`) appear in full
  only. The validator reports `0` matches at nested resource level for this
  reason, not because content diverged.
- `collection_type` has no `CoreDistribution` counterpart and is full-only.

Other cross-record checks:

- `total_file_count` / `total_size_bytes` are absent from full and have no core
  counterpart; no distribution-level byte or file count is asserted anywhere, so
  there is nothing to reconcile against.
- `is_tabular: true` is identical in both and agrees with the distribution
  content (column-oriented Parquet plus tab-delimited tables).
- `dialect` (core-only, `FormatDialect`) is deliberately absent: the release
  mixes Parquet, TSV and JSON, so no single dialect is well defined, and the
  bundle states none.
- Identity, version and access facts agree across the pair and internally:
  `id` / `doi` / `version` / `issued` / `page` / `license` agree with
  `version_access`, `distribution_dates`, `license_and_use_terms`,
  `distribution_formats[].access_urls` and the `citation` string in full.
- Historical versus current release: version 1.0.0 (17 December 2025) is
  recorded in `version_access.versions_available` and `distribution_dates` as a
  prior release, and version 1.1's release notes are recorded in `updates`. The
  differing content of 1.0 and 1.1 is represented as a version history, not as a
  contradiction.
- No unresolved contradiction was found within either record or between them.

### Validator output (final, independent run)

```
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=3 (3 at collection level, 0 at nested resource level),
  unmatched core distributions=[]
```

The warning marks the `file_collections` ↔ `distributions` mapping as requiring
the semantic review recorded in the table above; that review was performed and
is not evidenced by the warning itself.

The `--sync-core` pass changed the core file's bytes (md5
`694c577a9eebdd07b9ce22b4b8d283a8` → `a6cd0da0d9079e6726857bec5c05eca7`) through
serialisation only; parsed content was already deeply identical before and after,
and the independent check passes on the synchronised file.

## Files written

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_reconciliation.md`

No file outside these three was written. The live provenance record for this run
is written by the launcher, not by this agent.

Note on the core header: the launch specification's header block was used
verbatim, with two lines added that the playbook's completion criteria require of
a core record — `# Full D4D input: …` naming the same-run Phase 1 file, and
`# Phase 4 reconciliation: completed`.

## Commands run

```bash
poetry run d4d download scope --project VOICE_PEDIATRIC
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_PEDIATRIC_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_PEDIATRIC_d4d.yaml --core .../VOICE_PEDIATRIC_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_PEDIATRIC_d4d.yaml --core .../VOICE_PEDIATRIC_d4d_core.yaml
poetry run d4d download scope --check --strict --project VOICE_PEDIATRIC
poetry run d4d api prompts check --strict
```

## Final results

| check | result |
|---|---|
| full schema validation (`Dataset`) | pass |
| full ontology term validation | pass |
| core schema validation (`CoreDataset`) | pass |
| core ontology term validation | pass |
| schema-derived pair consistency | PASS, 78 schema-identical slots, 1 semantic-review warning (reviewed above) |
| `d4d download scope --check --strict` | in scope; no record identifies itself as a dataset the project declares distinct |
| `d4d api prompts check --strict` | 10 files, 0 not at their pin |
| prior-D4D reuse | none; no generated record outside this run's label was read |
| full populated top-level slots | 67 |
| core populated top-level slots | 55 |
| shared populated slots, deeply identical | 54 of 54 |
| unresolved contradictions | none |
