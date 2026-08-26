# AI-READI full/core reconciliation — 2026-08-24_claude-opus-5-claudecode-generic-v5_rep3

Run label: `2026-08-24_claude-opus-5-claudecode-generic-v5_rep3`
Arm: BASELINE (input documents only)
Condition: generic_v5 (`src/download/prompts/d4d_generic_arm_prompt_v5.md`)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5 · Reasoning effort: high (asserted by launcher)
Mode: four-phase project agent

Records reconciled:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d_core.yaml`

Declared input bundle (only source of dataset facts):
`data/preprocessed/concatenated/AI_READI_preprocessed.txt`
Manifest: `data/preprocessed/source_manifest.yaml`

## Resume

This run was interrupted by a session limit after Phase 1 and Phase 2 had written
their artifacts. Per the snapshots section of `.claude/commands/d4d-full-core.md`,
the resumed invocation re-ran each phase's validation commands against the
existing artifact before deciding to skip it. Both artifacts existed and passed:

| phase | artifact | schema validation | term validation | decision |
|---|---|---|---|---|
| `generate_full` | `AI_READI_d4d.yaml` | No issues found | passed | skipped on validated artifact |
| `generate_core` | `AI_READI_d4d_core.yaml` | No issues found | passed | skipped on validated artifact |

Phases 3 and 4 had not run and were performed in full by the resumed invocation,
together with a repair and a rewritten report. No artifact under any other label
was read at any point.

## Referent

`Dataset` admits one referent. The manifest declares it:

```
referent:    AI-READI dataset
referent_id: https://doi.org/10.60775/fairhub.3
referent_note: fairhub.1 and fairhub.2 are earlier releases of the same dataset,
               both documented in the bundle, not separate datasets.
related_but_distinct: []
```

Both records identify themselves as `id: doi:10.60775/fairhub.3`, release 3.0.0,
and hold to that choice consistently. Releases 1.0.0 and 2.0.0 are represented as
earlier releases of the same dataset through `related_datasets`
(`relationship_type: is_new_version_of`) and `version_access.versions_available`,
never merged into the current release's figures. The record states release
3.0.0's totals (2,280 participants; 356,343 files; 3,815,969,779,678 bytes) and
labels the 204- and 1,067-participant figures explicitly as the earlier releases'.

## Phase 3 — source and provenance audit

### Provenance

- Every factual input path is on the Phase 3 allowlist: the declared bundle, the
  manifest, the two schema files, and this run's own same-label pair.
- No prior-run D4D record, evaluation, or reconciliation report was read. Nothing
  under `data/d4d_concatenated/` outside this run's own label was opened, and no
  `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was opened.
- The core record's `# Sources:` line names the same-label full record, so the
  pair is tied to one run.
- Both headers carry `Prior D4D factual reuse: prohibited`.

One provenance defect was found and is recorded rather than hidden: the core
header already carried `# Phase 4 reconciliation: completed` when the resumed
invocation opened it, written by the interrupted invocation before Phase 4 had
run. Phase 4 has now run, so the line is true of the bytes that exist; it was
premature when written.

### Fact checks against the bundle

Headline values were checked directly against the declared bundle. All are
present in it: 2,280 participants; 356,343 files; 3,815,969,779,678 bytes;
collection window 2023-07-19 to 2025-05-01; release date 2025-11-17; DOI
10.60775/fairhub.3; IRB approval STUDY00016228; ClinicalTrials.gov NCT06002048;
NIH award OT2OD032644 with application ID 10471118 and award amount 5026499;
grants P30DK035816 and UL1TR003096; Research to Prevent Blindness; license
documents 10.5281/zenodo.17555036 (v2.0) and 10.5281/zenodo.10642459 (v1.0);
recommended split sizes 1,576 / 352 / 352 and their mean ages 61.1 / 60.3 / 60.5
against a cohort mean of 60.8; the LeeLab Anura, Garmin Vivosmart 5 and Dexcom G6
devices; 24,636 FAIRhub views.

No unsupported, stale, or mis-scoped assertion was found. Historical values
(releases 1.0.0 and 2.0.0, the pilot phase, license v1.0) appear only where their
historical scope is stated.

### Source disagreements

The full record's `source_caveats` already records thirteen numbered
disagreements plus two unresolved observations, each naming what each source
said, the manifest tier of each, and which was preferred. The audit re-checked
the resolutions and found them consistent with `source_priority`:

- Where tiers differ, the higher-ranked source was preferred and the alternative
  recorded — items 2 (project name expansion, tier 1/4 over tier 3), 5 (PI
  affiliation, tier 1 API over tier 1 RO-Crate corroborated by the license
  agreement), 7 (enrollment start, tier 1 over tier 3), 8 (target enrollment,
  tier 1 over tier 2), 10 (de-identification, tier 1 over tier 3), 12
  (recruitment window, tier 1 over tier 3).
- Where the disagreeing sources share a rank, the ranking cannot decide and no
  value was selected — item 3, publisher: the FAIRhub API says "FAIRhub" and the
  RO-Crate says "AI-READI Consortium", both tier 1, so the scalar `publisher`
  slot is left unpopulated in both records. This is the correct application of
  the same-rank rule, not an omission.
- Item 13 records the arithmetic residual between the per-directory inventory
  (356,334 files, 3,815,969,360,064 bytes) and the stated release totals
  (356,343 files, 3,815,969,779,678 bytes): nine files and roughly 420 KB. Both
  figures are carried as their sources state them rather than one being adjusted
  to match the other. Verified independently in Phase 4 by summing the nine
  `file_collections` entries.

### Shape audit

Two shape findings, each present in both records:

1. `$.creators[0].principal_investigator` held the string `Aaron Lee`. The
   schema declares this slot's range as `Person`, which carries an identifier
   slot `id` of range `uriorcurie` and is not inlined, so the slot takes a
   Person's identifier and not a display name. The bundle states Aaron Lee's
   ORCID as `https://orcid.org/0000-0002-7452-1648` at three places in the
   FAIRhub API metadata (responsible-party investigator, central contact, and
   overall official), and the record already carries it in CURIE form as
   `creators[1].id: ORCID:0000-0002-7452-1648`. Writing the name in one place
   and the ORCID in another gives one person two identities.
2. `$.labeling_strategies[0].data_annotation_protocol` held
   `N/A - no labels are provided`. That slot's description asks for the
   annotation methodology, tasks and protocols followed during labeling; a
   statement that the thing is absent does not answer it. The fact that no
   labeling was performed is already stated in the sibling `labeling_details`
   and in `instances[0].label_description`.

No other reference-slot violation was found: a schema-driven walk of both
records, following induced ranges and inlining from `Dataset` and `CoreDataset`,
reported these two and nothing else. No object appears in a scalar-ranged slot,
no enum value outside its declared permissible values, no prose in a slot the
schema declares as a list, no `notes` slot is used at all, and no evidence
commentary appears outside `source_caveats`.

### Identifier form and grounding

`uriorcurie_slots()` resolves to `data_substrate`, `data_topic`, `id`,
`latest_version_doi`, `publisher`. Every populated one uses a declared prefix
where one fits: `doi:` for the dataset id and `latest_version_doi`, `ORCID:` for
people, `ROR:` for organizations. `data_topic` holds
`https://meshb.nlm.nih.gov/record/ui?ui=D003924` — the schema declares no MeSH
prefix, so this is the `uri` fallback for an identifier no declared prefix
covers, and it is stated in the bundle 24 times. Slots declared `uri` rather
than `uriorcurie` correctly hold URLs (`access_urls`), and the `doi` slot, whose
range is `string`, correctly holds the bare `10.60775/fairhub.3`.

No identifier was supplied from model knowledge. The grounding checker reports
**27 grounded, 12 minted_fragment, 0 absent** for the pair. The twelve minted
fragments are the nine `file_collections`/`distributions` ids and the three
`subsets` ids, each hung off the dataset's own attested DOI CURIE
(`doi:10.60775/fairhub.3#cardiac_ecg`, `…#split-train`, and so on) rather than
on an invented prefix.

### House style and naming

The manifest declares AI-READI's canonical label as `AI-READI`. Every sentence
composed for these records uses it. The four `AI_READI` occurrences across the
pair are all in the mandated header block (the datasheet title line and the
bundle/source file paths), which the condition fixes verbatim and which are
identifiers. No British spelling appears in composed prose; the bundle's own
`licence`/`programme` spellings were not imported.

### Back-porting

No Phase 2 discovery required back-porting into the full record: Phase 2 found
no source-supported value that the full record lacked or stated differently.
Both shape findings above existed identically in both records and were corrected
in both.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

**Schema-derived shared-slot count: 79 schema-identical slots.** All pass:
present in both records or absent from both, with deeply identical parsed YAML
content including nested mappings and list order. Narrative fields were not
condensed, paraphrased, or reordered in core.

Per-record slots exempt from identity, and correctly differing:
`conforms_to_class`, `conforms_to_schema`.

### Populated inventories

- Full: **79 populated top-level slots**, 1,748 lines.
- Core: **66 populated top-level slots**, 1,281 lines.

The fourteen slots populated in full and not in core — `citation`,
`collection_consents`, `collection_notifications`, `consent_revocations`,
`direct_collection`, `file_collections`, `participant_compensation`,
`participant_privacy`, `relationships`, `splits`, `subsets`,
`third_party_sharing`, `total_file_count`, `total_size_bytes` — were each checked
against `CoreDataset`. **None of them is declared on `CoreDataset`**, so their
absence from core is required by the schema rather than an omission. The one slot
populated in core and not in full, `distributions`, is likewise declared only on
`CoreDataset` and not on `Dataset`; it is the projection target for full's
`file_collections`.

### Projected slots

`resources` is `Dataset`-ranged in full and `CoreDataset`-ranged in core. Neither
record populates it, so coverage is trivially equal and there is nothing to
project.

### Related, non-identical representations — semantic review

The validator emits a `semantic-review-required` warning for
`$.file_collections <-> $.distributions`. That warning marks the review as owed;
it is not evidence the review happened. The review was performed:

- **Coverage.** Nine `file_collections` and nine `distributions`, with identical
  name sets and no unmatched core distribution: `cardiac_ecg`, `clinical_data`,
  `environment`, `retinal_flio`, `retinal_oct`, `retinal_octa`,
  `retinal_photography`, `wearable_activity_monitor`, `wearable_blood_glucose`.
- **Deep identity of every field the two classes share.** `id`, `path`,
  `description`, `conforms_to`, and `conforms_to_standard` are identical across
  all nine pairs. Full's `total_bytes` and core's `bytes` carry the same integer
  in all nine cases; the field name differs because `FileCollection` declares
  `total_bytes` and `CoreDistribution` declares `bytes`.
- **Fields absent from core by schema, not by omission.** `file_count` and
  `collection_type` are declared on `FileCollection` and not on
  `CoreDistribution`, so their absence from the core projection is required.
- **Fields present in core and not available in full.** `format` and
  `media_type` are declared on `CoreDistribution` and not on `FileCollection`.
  Core populates them for `clinical_data` only (`CSV`, `text/csv`), which agrees
  with that collection's own description in both records and with the bundle.
  The other eight leave them unpopulated. This is an asymmetry of density, not a
  contradiction: no value in either record is contradicted by the other. It is
  recorded here rather than filled in, because filling it would be generation
  and Phases 3 and 4 audit rather than generate.
- **Counts against distribution-level values.** The nine collections sum to
  356,334 files and 3,815,969,360,064 bytes against the stated release totals of
  356,343 files and 3,815,969,779,678 bytes. The scopes differ — the
  per-directory inventory does not enumerate root-level metadata files — and the
  residual is recorded in `source_caveats` item 13 rather than treated as a
  contradiction.
- **Dialect, formats, tabularity.** `dialect` is unpopulated in both.
  `distribution_formats` is deeply identical across the pair (four entries:
  DICOM, CSV, JSON, Markdown). `is_tabular` is `false` in both, consistent with
  a nine-modality release that is predominantly DICOM imaging.
- **Top-level identity, version and access facts** agree with the version
  history and the distribution-level statements: `id`, `doi`, `version: 3.0.0`,
  `issued: 2025-11-17`, `latest_version_doi: doi:10.60775/fairhub.3`,
  `license: AI-READI custom license v2.0`, and `page:
  https://fairhub.io/datasets/3` are identical in both records and consistent
  with `version_access.versions_available`, `distribution_dates`, and
  `license_and_use_terms`.
- **Historical versus current releases** are distinguished throughout rather
  than read as contradictions: releases 1.0.0 (204 participants, 2024-05-03) and
  2.0.0 (1,067 participants, 2024-11-08) appear only in `distribution_dates`,
  `related_datasets`, `version_access`, and the `instances[0].description`
  sentence that labels them as earlier releases.

**Zero unresolved contradictions within or between the two records.**

### Synchronization

`--sync-core` was **not** run. Phase 3 had made the full record canonical and the
pair was already deeply identical on all 79 schema-identical slots before and
after the repair, so there was nothing for synchronization to do. The validator
was run only in its independent, non-mutating form.

## Repair

Both shape findings required changing both records, so a repair phase ran. One
fix-validate loop was sufficient.

| record | slot | before | after |
|---|---|---|---|
| full, core | `creators[0].principal_investigator` | `Aaron Lee` | `ORCID:0000-0002-7452-1648` |
| full, core | `labeling_strategies[0].data_annotation_protocol` | `N/A - no labels are provided` | slot removed |

Files changed: `AI_READI_d4d.yaml`, `AI_READI_d4d_core.yaml`. Both changes were
applied identically to both records in one pass, preserving the deep identity of
the shared slots. No fact was added: the ORCID was already in the record and in
the bundle, and the removed value asserted nothing the sibling
`labeling_details` does not already state.

This report was written after the repair and describes the bytes that exist.

## Commands run

Validation of the two resumed artifacts, before deciding to skip their phases:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Scope and priority declarations:

```bash
poetry run d4d download scope --project AI_READI
poetry run d4d download priority --project AI_READI
```

Pair consistency (independent form, no `--sync-core`), grounding, and report
claims — each run before the repair and again after it:

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full <full_file> --core <core_file>

poetry run python -c "
from pathlib import Path
from data_sheets_schema.grounding import check_run
from data_sheets_schema.identifiers import uriorcurie_slots
r = check_run(Path('<full_file>'), Path('<core_file>'), Path('<bundle>'), uriorcurie_slots())
print(r['distinct'])
for f in {(x['kind'], x['identifier']) for x in r['findings']}: print(*f)"

poetry run python -c "
from pathlib import Path
from data_sheets_schema.report_claims import check_report, declared_slots
import yaml
full = yaml.safe_load(Path('<full_file>').read_text())
core = yaml.safe_load(Path('<core_file>').read_text())
out = check_report(Path('<report_file>'), full, core, declared_slots())
[print(f) for f in out['findings']]"
```

Provenance and gates:

```bash
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-24_claude-opus-5-claudecode-generic-v5_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt ...
poetry run d4d runs check --strict
poetry run d4d download scope --check --project AI_READI
```

## Final results

| check | result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full term validation | passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core term validation | passed |
| Pair consistency, 79 schema-identical slots | PASS |
| Semantic review of `file_collections` ↔ `distributions` | performed, 9/9 matched, 0 contradictions |
| Identifier grounding | 27 grounded, 12 minted_fragment, **0 absent** |
| Referent held consistently across the pair | yes |
| Repair | 2 findings, both records, 1 fix-validate loop |

Phases performed by this invocation: `source_audit`, `reconcile`, `report`,
`repair`, `report_after_repair`.
Phases skipped on validated artifact: `generate_full`, `generate_core`.
