# AI_READI full/core reconciliation

- Run label: `2026-08-11_claude-opus-5-claudecode-generic_rep2`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic prompt
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/AI_READI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the AI-READI dataset published on
FAIRhub, identified by `https://doi.org/10.60775/fairhub.3`, in its current release 3.0.0** —
the same referent the manifest declares for this project. Versions 1.0.0 and 2.0.0 are treated
as earlier releases of the same dataset (recorded in `version_access` and `related_datasets`,
not as separate referents), which is what the manifest's `referent_note` states. Both records
hold to this choice: `id`, `doi`, `version`, `title`, `total_file_count`, `total_size_bytes`
and every count are those of release 3.0.0. Where a source describes the controlled-access
tier, the project as a programme, or a historical release, that content is recorded as a
statement about those things (in `sensitive_elements`, `participant_privacy`,
`version_access`, `known_limitations`) rather than folded into the referent's own values.

The manifest declares `related_but_distinct: []` for AI_READI, so no related-but-distinct
dataset had to be represented through `related_datasets`.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs used were the declared bundle, `data/preprocessed/source_manifest.yaml`, and the
two schema files. Also read: the launch instruction, `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md` and `.claude/commands/d4d-agent.md`. **No prior full or core
D4D record, from any arm, label or date, was read, opened, grepped or consulted**, and nothing
under `data/d4d_concatenated/` or `data/ro-crate_packages/` was read other than this run's own
two output files. No evaluation report or reconciliation report from any run was consulted.

`d4d api prompts check --strict` reports all 10 prompt files at their pins, including
`src/download/prompts/d4d_generic_arm_prompt.md`, the file this run's condition is built from:
the run was made under a published version of its condition, not under edited text.

One qualification, disclosed rather than glossed: `d4d download scope --check --project
AI_READI` is required by the playbook's completion criteria and it walks every AI_READI record
on disk (81 records this run). Its output is a per-project verdict and a count; no field value
from any other record was surfaced or used. It was run after both outputs were final.

### Source disagreements found, and how they are represented

None was silently resolved. Each is recorded on the slot it affects and summarised in the
record-level `source_caveats`.

1. **Managing organisation / lead sponsor / PI affiliation.** The FAIRhub dataset and study
   descriptions name "Washington University in St. Louis" with ROR `https://ror.org/01yc7t268`
   as managing organisation, lead sponsor, and the affiliation of Aaron Lee and Cecilia Lee.
   The same FAIRhub record's location list gives University of Washington the ROR
   `https://ror.org/00cvxb145`; the licence agreement names the University of Washington as
   Licensor; NIH RePORTER gives University of Washington as the awardee organisation; and the
   BMJ Open and Nature Metabolism author lists place both Lees at the University of Washington.
   Represented: the name/ROR pairing is transcribed exactly as the source pairs it in
   `creators`, and in `data_governance.accountable_organization`, with `source_caveats` on each
   naming the conflicting evidence. No merge, and no substitution of the "obviously intended"
   organisation.
2. **De-identification.** FAIRhub records `deIdentType: NoDeIdentification` with the rationale
   that no identifiers were collected; the Nature Metabolism comment states the public set is
   stripped of PHI via the HIPAA Privacy Rule "Safe Harbor" method. Both statements are carried
   in `is_deidentified.deidentification_details` with a `source_caveats` naming the tension.
3. **Target enrolment.** 4000 in the BMJ Open protocol, Nature Metabolism, NIH RePORTER and the
   FAIRhub study description; 4600 in the UW IRB protocol application. Recorded in the
   record-level `source_caveats`; the value used in prose (`known_limitations`) is 4000, which
   four of five sources give.
4. **Enrolment start and study end.** 2023-07-19 (FAIRhub) against 18 July 2023 (BMJ Open); 30
   November 2026 enrolment end (BMJ Open) against an anticipated completion of 2027-01-01
   (FAIRhub). Represented as two distinct `collection_timeframes` entries — the v3.0.0
   collection window and the study enrolment window — each carrying its own dates and a
   `source_caveats`, rather than one averaged timeframe.
5. **Licence version.** The bundle contains the full text of AI-READI-LICENSE-v1.0 (Zenodo
   10642459); the FAIRhub metadata for release 3.0.0 names "AI-READI custom license v2.0"
   (Zenodo 17555036), whose text is not in the bundle. `license_and_use_terms` names the v2.0
   licence as the one governing this release and attributes the quoted clauses to the v1.0 text
   it actually has, with a `source_caveats` saying so.
6. **RePORTER page for OT2OD032644.** `project-details/10471118` in the README and the NIH
   RePORTER source document; `project-details/10885481` in the FAIRhub descriptions. Both
   recorded on the `Grant`.
7. **Acronym expansion.** "Equitable" (BMJ Open, Nature Metabolism) against "Exploratory" (NIH
   RePORTER, README, healthsheet, and the FAIRhub official title). Found during the audit: the
   Phase 1 `description` had merged them as "Equitable/Exploratory", which is a claim no source
   makes. Corrected to use the acronym alone, with the disagreement recorded in
   `source_caveats`.
8. **Demographic sub-populations.** The healthsheet answers "No" to identifying demographic
   sub-populations, while the README publishes aggregate race/ethnicity, sex and diabetes-status
   counts for the recommended splits. Both are recorded in the single `subpopulations` entry
   with a `source_caveats` distinguishing withheld per-participant labels from published
   aggregates.
9. **Completeness of the sample.** The healthsheet says the dataset contains all possible
   instances; the study description records the sampling method as a Non-Probability Sample.
   Both are in `sampling_strategies`, with a caveat noting they describe different reference
   sets.

### Corrections made in Phase 3

Applied to the full record first, then the core record was re-derived from it so the shared
slots stayed deeply identical.

| # | Finding | Correction |
|---|---|---|
| 1 | `description` merged two acronym expansions into "Equitable/Exploratory" — an unsupported composite | Removed the expansion; disagreement moved to `source_caveats` |
| 2 | `description` said retinal imaging spanned "six device families"; Table 4 lists seven device rows across five manufacturers | Replaced with the manufacturers the sources name (Optomed, iCare, Heidelberg, Topcon, Zeiss) |
| 3 | Shape: two `Grant` entries carried evidence commentary inside `name` ("NIH grant … acknowledged in the BMJ Open publication") | `name` removed; commentary moved to the grant's `description`; `grant_number` left as the structured value |
| 4 | `license_and_use_terms.name` spelled "licence" where the source spells the proper name "AI-READI custom license v2.0", disagreeing with the top-level `license` | Name matched to the source spelling |
| 5 | `at_risk_populations.at_risk_groups_included: false` was asserted without stating its basis, and the IRB form's protected-population checkboxes are not legible in the extracted text | Added `source_caveats` giving the basis and naming what the source could not answer |
| 6 | Person-ranged slots (`principal_investigator`, `contact_person`) had been written as inline objects; `Person.id` is an identifier and those slots are not inlined | Replaced with the ORCID identifier string; the person's title and contact e-mail moved into the `Creator.description`, where the schema has a home for prose |
| 7 | `known_biases[0]` carried `scope_impact`, which the schema declares on `DatasetLimitation`, not `DatasetBias` | Removed |

Findings 6 and 7 were surfaced by `linkml-validate` during Phase 1 and fixed before the record
was declared valid.

### Shape and slot-filling audit

- No prose sits in a slot whose range is a list; no enum value outside its schema's permissible
  values (`bias_type`, `limitation_type`, `collection_type`, `data_use_permission`,
  `hipaa_compliant`, `confidentiality_level`, `role`, `relationship_type` all checked against
  `SchemaView`).
- No commentary embedded inside a `name`, identifier or affiliation value after correction 3.
- `notes` is unused in both records: narrative sits in `description`, evidence commentary in
  `source_caveats`, and no sibling value is restated in `notes`.
- Structured slots are filled before prose: `grants`/`grant_number`, `affiliations`,
  `start_date`/`end_date`, `file_count`/`total_bytes`, `versions_available`,
  `irb_approval`, `release_dates` carry their content rather than leaving it in surrounding
  text.
- Nine identifiers are locally minted because the schema requires them and no source supplies
  one: the nine `FileCollection.id` values, plus fragment identifiers on inlined objects that
  the schema gives an optional `id`. They are formed as fragments of the dataset DOI from the
  directory or topic name (`https://doi.org/10.60775/fairhub.3#cardiac_ecg`). They are
  identifiers of record structure, not dataset facts.
- One inferred identifier is flagged in place: `related_datasets` includes the mini-subset as
  `https://fairhub.io/datasets/4`, constructed from the FAIRhub API field `"child": 4` and the
  site's URL pattern. Its `source_caveats` says the identifier was constructed and that no DOI
  or URL for the mini-subset appears in the bundle.

### Internal consistency checks (each record)

- Participant count 2280 is consistent across `description`, `instances.counts`,
  `subpopulations.distribution`, `splits`, `version_access` and `known_limitations`; the split
  counts 1576 + 352 + 352 sum to 2280, and the race/ethnicity (380+545+519+836), sex (951+1329)
  and diabetes-status (776+560+686+258) totals each sum to 2280.
- Version history is consistent: 204 (v1.0.0, 2024-05-03), 1067 (v2.0.0, 2024-11-08, 165,051
  files, 2.01 TB), 2280 (v3.0.0, 2025-11-17, 356,343 files, 3.82 TB); the healthsheet's
  204 + 863 = 1067 increment holds.
- `id`, `doi`, `version`, `license`, `page`, `publisher` and the DOIs cited in
  `version_access`, `related_datasets` and `distribution_dates` agree.
- Collection window 2023-07-19 to 2025-05-01 agrees between `collection_timeframes`,
  `description` and `instances`.

### Phase 2 discoveries back-ported to full

None. Core is a projection of the full record's schema-identical slots; consulting the bundle
for core slots the full record left empty (`imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `errata`, `dialect`, `compression`, `download_url`, `status`,
`created_on`, `issued`, `last_updated_on`, `resources`) found no supporting evidence for any of
them. The healthsheet returns an empty response for the erratum question and states that no
labelling or imputation was performed; no CSV dialect, compression scheme, checksum or direct
download URL appears anywhere in the bundle. Those slots are therefore absent from both records,
which is the correct answer where the evidence is absent.

Date-typed top-level slots (`issued`, `created_on`, `last_updated_on`) are omitted deliberately:
the schema ranges them as `datetime`, the sources give day precision only, and writing a
midnight timestamp would assert precision no source supports. The release dates are carried at
day precision in `distribution_dates.release_dates` and in `version_access.version_details`.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView`;
no hand-written field list was used.

### Schema-identical slots

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml
PASS: 78 schema-identical slots; projected slots=['resources']
```

`--sync-core` was **not** needed and was not run: the core record was generated by projection
from the Phase 3-audited full record, so every schema-identical slot was byte-for-byte derived
from it and no divergence could arise. An independent check confirms it: of the 62 slots present
in both records, all 62 compare deeply equal as parsed YAML, including every nested mapping and
every list item in order. Narrative fields are not condensed, paraphrased, reordered or omitted
in core — `description`, `source_caveats`, and every `*_details` string are the same strings.

Presence is identical too: no schema-identical slot is present in one record and absent from the
other.

### Projected slots

`resources` (`Dataset` in full, `CoreDataset` in core) is absent from both records. No source in
the bundle describes a nested dataset that is not better represented as a version relation or a
file collection, so the coverage requirement is met trivially (0 = 0).

### Related, non-identical representations — semantic review

The validator emitted one warning:

```
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=9 (9 at collection level, 0 at nested resource level),
  unmatched core distributions=[]
```

The warning marks work to be done, not work that was done. The review was performed:

| Property | Full `file_collections` | Core `distributions` | Verdict |
|---|---|---|---|
| identity | 9 collections | 9 distributions, same 9 ids | matched, no unmatched on either side |
| name | 9 values | identical | agree |
| path | 9 values | identical | agree |
| description | 9 values | identical | agree |
| byte count | `total_bytes` | `bytes` | equal for all 9 |
| format standard | `conforms_to` | `conforms_to` | equal for all 9 (WFDB, OMOP CDM, ESDS ASCII, DICOM ×4, Open mHealth ×2) |
| compression | absent | absent | agree; no source states a compression scheme |
| checksums | no slot on `FileCollection` | `hash`/`md5`/`sha256` absent | agree; no checksum appears in the bundle |
| access URL | no slot | no slot | carried once, identically, in `distribution_formats.access_urls` in both records |
| release scope | v3.0.0 | v3.0.0 | agree |
| full-only nested slots | `file_count`, `collection_type` | omitted from the projection | expected: `CoreDistribution` declares neither |

`total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678) are full-only slots and
were compared against the distribution-level values, whose represented scope is the same
release. The nine collections sum to 356,334 files and 3,815,969,360,064 bytes — short by
exactly 9 files and 419,614 bytes. That is not a contradiction: the FAIRhub structure
description lists exactly nine top-level metadata files outside any datatype directory
(`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`,
`healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`,
`study_description.json`). The totals and the per-collection figures corroborate each other.

`dialect` (core-only) is absent, and `is_tabular` is `false` in both — consistent: the dataset
is multimodal, and no source describes a tabular dialect. Formats agree across
`distribution_formats` (identical in both), `conforms_to` at dataset level (CDS v0.1.1) and
`conforms_to` per distribution.

Top-level identity, version and access facts (`id`, `doi`, `version`, `title`, `license`,
`page`, `publisher`, `language`, `keywords`) agree with `version_access`, `distribution_dates`,
`distribution_formats`, `license_and_use_terms` and `regulatory_restrictions` in both records.
Historical releases are distinguished from the current release throughout rather than treated as
contradictions: v1.0.0 and v2.0.0 counts, sizes and dates appear only inside `version_access`
and `related_datasets`, scoped as such.

**Unresolved contradictions within or between the two records: none.** The disagreements listed
in Phase 3 are disagreements *between sources*, represented identically in both records.

## Header note

The launch instruction supplied a header block to use verbatim, with "phase 2" and the core
schema path substituted in the core file. That block is reproduced exactly in both files,
including the `# D4D Datasheet for AI_READI Dataset` first line in the core file. Two lines the
playbook's completion criteria require of a core header were added below it rather than in place
of anything: `# Sources:` naming the bundle and the same-run full record, and
`# Phase 4 reconciliation: completed`. Nothing in the supplied block was altered or removed.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/AI_READI_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/AI_READI_d4d_core.yaml` (created, Phase 2; re-derived after the Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/AI_READI_reconciliation.md` (this file)

No file outside these three was written.

## Commands run

```bash
poetry run d4d download scope --project AI_READI
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset .../AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data .../AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset .../AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data .../AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml
poetry run d4d download scope --check --project AI_READI
```

The live provenance record for this run is written by the launcher, not by this agent, with:

```bash
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

It must be recorded after this report is final, since the record hashes the artifacts it names;
run `d4d runs validate` once afterwards so the run has a verdict to carry.

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass — no issues found |
| Full ontology term validation | pass |
| Core schema validation (`CoreDataset`) | pass — no issues found |
| Core ontology term validation | pass |
| Schema-derived pair consistency | PASS, 78 schema-identical slots |
| Deep identity of shared slots | 62/62 present in both, all deeply identical |
| Projected `resources` coverage | 0 = 0, consistent |
| `file_collections` → `distributions` semantic review | 9/9 matched, no conflicts |
| `d4d download scope --check --project AI_READI` | in scope — the record does not identify itself as a dataset the manifest declares distinct |
| Prior-D4D reuse | none |

Populated top-level slots: **77 in the full record, 63 in the core record** (informational
metadata, not a quality measure). Line counts, likewise informational: 1,752 (full) and 1,250
(core).
