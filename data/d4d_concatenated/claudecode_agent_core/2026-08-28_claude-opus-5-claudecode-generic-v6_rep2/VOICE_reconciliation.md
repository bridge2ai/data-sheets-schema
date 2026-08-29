# VOICE — Phase 3 / Phase 4 reconciliation

- **Label:** `2026-08-28_claude-opus-5-claudecode-generic-v6_rep2`
- **Condition:** generic_v6, BASELINE arm (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Mode:** four-phase project agent
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
  (md5 `dcd717170da6762569c0b4eeafc1c3d2`, 5,746 lines, 22 chunks)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d_core.yaml`
- **Coverage receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The record is about the **Bridge2AI-Voice adult
dataset**, identified by the PhysioNet project-level DOI recorded in the bundle as
"DOI (latest version)", written as the CURIE `doi:10.13026/37yb-1t42`. The
per-version DOIs the bundle carries (`10.13026/249v-w155` for 1.1,
`10.13026/k81f-qr68` for 3.0.0, `10.13026/8xbn-nq66` for 3.1.0, and
`10.57764/qb6h-em84` for the Health Data Nexus 1.0 release) are recorded as
versions of this one dataset under `version_access`, not as separate datasets.

The **Bridge2AI-Voice Pediatric Dataset** is documented in the bundle
(`physionet_pediatric_1_1_0`) and is a distinct dataset. It appears only in
`related_datasets`, with `relationship_type: references` — the weakest claim the
evidence supports, since the bundle states no typed relationship and only records
that each release page cross-references the other. No pediatric fact was merged
into any other slot; `d4d download scope --check --project VOICE` reports this
record in scope and does not list it among the 32 records that place pediatric
identifiers outside the declared slot.

## Phase 1 — reading and generation

The chunk manifest was current (`d4d bundle chunk --check --project VOICE`).
All 22 chunks were read with the file-reading tool in manifest order and a
coverage-receipt entry was written for each before the next was read: 20
`extracted`, 1 `redundant_with` (c004, PMC page furniture repeating c003's data
availability statement), 1 `nothing_relevant` (c001, the bundle preamble and
table of contents).

Structure was derived from class `Dataset` in `data_sheets_schema_all.yaml`.
Three schema facts shaped the record and are worth stating because they are not
obvious from the class listing:

- `principal_investigator`, `contact_person` and `committee_contact` have class
  ranges but are **not inlined** — the schema expects a string. They carry names
  and an address, not nested `Person` objects.
- `FileCollection.id` and `File.id` are **required**. Emitting file-level
  structure therefore compels minted identifiers (see Minted identifiers below).
- `FileCollection` declares no `format` slot; the format of the distributed files
  is stated in the collection description and in `distribution_formats`.

No `Person` objects were emitted anywhere. The bundle supplies no ORCID for any
individual, and a person has a referent outside this record, so an identifier
could not be minted for one. People are named in the string slots the schema
provides (`Creator.name`, `Creator.principal_investigator`) with their roles in
`Creator.description` and their institutions as `Organization` objects under
`Creator.affiliations`.

`credit_roles` was left empty throughout. The bundle states contributor roles in
two forms — CRediT terms for the *authors of the feasibility publication*, and
prose role titles for the *dataset's lead investigators* ("Co-Lead of Data
Acquisition", "Lead — Genomic data"). Neither can be mapped to
`CRediTRoleEnum` for this dataset without inference, so the roles are recorded as
prose in each creator's `description`.

`subsets` and `variables` were left absent. The releases are versions of one
dataset rather than subsets of it, and `DataSubset` inherits a required `id`
that nothing in the record points at; the release history is carried by
`version_access.versions_available`. The bundle gives no variable inventory with
names, only file names and data-dictionary structure, and `VariableMetadata`
requires `variable_name`.

## Phase 3 — source and provenance audit

Schema and term validation were re-run on the full record before the audit
(both clean). The agent's read history contains only the declared bundle, the
source manifest, the two schema files, the playbooks and the repository's own
tooling; **no prior generated D4D record, evaluation or reconciliation report was
opened**, from this project or any other. No `data/d4d_concatenated/` path other
than this run's own output directory was read.

### Findings and corrections

Four corrections were made, all to the full record; the core was re-derived
afterwards.

1. **Unsupported identifier removed.** `distribution_formats[0].media_type`
   carried `application/vnd.apache.parquet`. The bundle names the format as
   Parquet but states no media type anywhere, so this was an identifier supplied
   from outside the evidence — the defect the grounding rule exists for. The
   value and the sentence in the sibling `source_caveats` that justified it were
   both removed. `format:` retains the format as the bundle words it.
2. **Consortium membership caveat added.** `creators[1].affiliations` is the
   union of two institution lists that do not agree: the project documentation's
   twelve collaborators and the IRB protocol's nine participating institutions,
   which add Massachusetts Eye and Ear Institute and Emory University while
   omitting five of the twelve. Both sources sit at manifest tier 2, so the
   ranking cannot decide; a `source_caveats` on that creator now states both
   lists rather than letting the union read as a single attested membership.
3. **Affiliation conflict recorded.** Three sources place Alistair Johnson
   differently — the IRB protocol at the Hospital for Sick Children (tier 2),
   the audiomics white paper at "Division of Biostatics, Hospital for Sick
   Children" (tier 3), the feasibility publication at the University of Toronto
   (tier 3). The tier-2 source was preferred and the disagreement recorded in
   `creators[5].source_caveats`.
4. **Derived count made traceable.** `file_collections[0].file_count: 11` is a
   count of the files the version 3.1.0 release page enumerates for the features
   folder (nine Parquet binaries plus two TSVs), not a figure the bundle states.
   A `source_caveats` now says so and records that no byte size is available,
   which is why `total_size_bytes` and `total_file_count` are absent.

### Source disagreements represented rather than resolved

Where the manifest ranks one source higher, its value is stated and the
disagreement recorded in the relevant `source_caveats`. Where the disagreeing
sources share a rank, both values are recorded.

| Question | Sources | Outcome |
|---|---|---|
| Intended size of the finished database | project documentation: 10,000 voices, 10,000 enrolment anticipated by 2027 (tier 2); IRB protocol: 30,000 participants, 5,000 per category (tier 2); audiomics white paper: 30 000 voices (tier 3) | Same tier — both figures recorded in `purposes[0].source_caveats`; neither selected |
| High Volume Expert Clinic threshold | IRB protocol: over 1,000 patients per year; project documentation: more than 50 patients per month (both tier 2) | Same tier — both recorded in `sampling_strategies[1].source_caveats` |
| Alistair Johnson's affiliation | IRB protocol (tier 2) vs two publications (tier 3) | Tier 2 preferred; conflict recorded |
| FFT size for the spectrograms | v1.1 release page: 512-point, no downsampling; v3.0.0/3.1.0: 400-point with 2× time-domain downsampling (both tier 1) | Different releases of one dataset — current release stated, earlier value recorded in `preprocessing_strategies[3].source_caveats` |
| Access label | v1.1: "Restricted Access", registered users; v3.x: "Credentialed Access", credentialed users (both tier 1) | Current release stated, earlier recorded in `distribution_formats[0].source_caveats` |
| Free-speech transcripts in the release | project documentation content warning says they are included (tier 2); PhysioNet release pages say transcripts of free speech audio were removed (tier 1) | Tier 1 preferred for the fact; the warning is still recorded as the documentation states it, with the removal in `content_warnings[0].source_caveats` |
| Pre-processing for cleaning | project documentation answers "No" while the same document describes an audit protocol with QC metrics | Both recorded in `cleaning_strategies[0].source_caveats`; not reconciled |
| Award number | seven renderings across five sources, two of them evidently corrupted | Three well-formed numbers recorded as separate `Grant` entries; all seven renderings listed in `funders[0].source_caveats`, the corrupted two explicitly not transcribed as grant numbers |
| Consortium size | 50 experts from 12 institutions (white paper); 14 institutions (feasibility publication), both tier 3 | Both recorded as stated in `creators[1].notes` |

### Receipts

55 `{slot, snippet}` pairs were back-ported into the existing entries of the
chunks the passages sit in — no chunk gained a second entry. Six were filed
against the wrong chunk on first writing and were moved to the chunk whose bytes
actually contain them (the validator's `snippet_adjacent_chunk` finding caught
all six); one citation snippet was replaced with the text the chunk actually
carries.

Final state: **chunks 22/22 reviewed · snippets 271/271 verified · slots 184/432
with a receipt (28 exempt) · no findings**, under
`d4d receipts check --strict`.

The 248 populated leaves without a receipt are overwhelmingly composed values
rather than transcribed ones: the `name` I gave each object, prose
`description`s that synthesize several passages, and the per-file `path` and
`file_type` values composed from the folder layout the release page gives. Each
was re-examined against the chunk it came from rather than padded with a
snippet; none was found unsupported beyond the media type removed above.

### Minted identifiers

Eight fragments were minted on the dataset's own identifier:
`doi:10.13026/37yb-1t42#features`, `#metadata`, `#phenotype` and five
`#features-*` file identifiers. Each exists because `FileCollection.id` and
`File.id` are schema-required, and each is pointed at by the object it labels and
by the derived core's `distributions`. Nothing else was minted: no fragment
labels a part that only prose describes, and no identifier was minted for a
person or an organization. The grounding check reports
`{'grounded': 2, 'minted_fragment': 8, 'absent': 0}`.

## Phase 4 — re-derivation, checks and repair

The core was re-derived from the corrected full record with
`d4d derive core --phase4-complete`. It was never edited by hand and
`--sync-core` was never passed.

Derivation facts printed by the command:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d.yaml", "md5": "58259634d2b1c7aeaec7e0f7860a0156"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

### Deterministic checks

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS: 79 schema-identical slots; projected `resources`; per-record exempt slots `conforms_to_class`, `conforms_to_schema`; one `semantic-review-required` warning |
| grounding (`check_run`) | `grounded 2, minted_fragment 8, absent 0` |
| `d4d receipts check --strict` | 22/22 chunks, 271/271 snippets, no findings |
| `d4d download scope --check --project VOICE` | in scope; record does not identify itself as the pediatric dataset |

## Claims

No slots were removed from either record as a matter of schema fit. One slot was
removed as an audit correction:

| `media_type` | Removed | invented IANA type `application/vnd.apache.parquet`; the bundle names the format as Parquet but states no media type, so the value was an identifier the evidence does not contain |

**Action:** no assertion is made here that any slot is undeclared by the schema.
`subsets`, `variables`, `credit_roles`, `total_file_count`, `total_size_bytes`,
`is_tabular`, `dialect`, `publisher`, `issued`, `download_url`, `compression`,
`status`, `created_by`, `created_on`, `modified_by`, `was_derived_from`,
`imputation_protocols`, `annotation_analyses`, `use_repository`, `other_tasks`
and `data_protection_impacts` are all declared and were left **absent** because
the bundle does not support them, not removed.

## Semantic review

- **`file_collections` ↔ `distributions`** (the pair checker's
  `semantic-review-required` warning): 8 deterministic matches — 3 at collection
  level (`#features`, `#metadata`, `#phenotype`) and 5 at nested resource level
  (the five `#features-*` files) — and no unmatched core distributions. Read
  semantically, each core distribution carries the same name, description and
  identifier as the collection or file it was projected from, and the projection
  dropped only full-only nested slots (`collection_type`, `file_count`,
  `resources`). The three collections are genuinely distinct groupings the
  release page distinguishes (features, metadata, phenotype), not one grouping
  split three ways. **reviewed: consistent**
- **`total_file_count` / `total_size_bytes` against the entries beneath them:**
  both are absent at dataset level. `file_collections[0].file_count: 11` counts
  the eleven files the release page enumerates in the features folder, of which
  five are described as `File` entries; the remaining six are named in the
  collection description rather than given entries, so the count is deliberately
  larger than the entry list and a `source_caveats` says so. No byte size appears
  anywhere in the bundle, so no size was recorded at any level and none could be
  aggregated. **reviewed: consistent**
- **`dialect` and `is_tabular` against the files:** `is_tabular` is absent. The
  release distributes both dense tensor Parquet files and tab-separated phenotype
  tables, so neither `true` nor `false` describes the dataset, and the bundle
  makes no such statement. `dialect` is set on no `File` entry — the bundle
  describes Parquet and TSV formats but no dialect or profile — so the
  derivation correctly left the core's `dialect` absent rather than inventing
  agreement. **reviewed: consistent**
- **Historical release read as the current one:** the bundle documents six
  releases across two platforms, and this was the largest risk in the record. The
  scalar slots that can carry only one value are pinned to the current release —
  `version: 3.1.0`, `last_updated_on: 2026-05-01`, `citation` (the 3.1.0
  PhysioNet citation), `page: https://b2ai-voice.org/`,
  `license_and_use_terms` (credentialed access, DUA, no training required),
  `version_access.latest_version_doi: doi:10.13026/8xbn-nq66`. Everything
  release-specific that is *not* current is scoped in its own text: the Health
  Data Nexus platform is described as "an earlier version of the feature-only
  dataset", `distribution_dates` names which date belongs to which version, and
  `version_access.versions_available` gives one entry per release with its date,
  content and DOI. Two values were corrected during this review because they
  described version 1.1 rather than 3.1.0 — the FFT size and the access label —
  and both now state the current release with the earlier value in
  `source_caveats`. `instances[0].counts: 833` is the version 3.0/3.1 figure and
  its `source_caveats` records the counts of the earlier releases. **reviewed:
  corrected**
- **Related-but-distinct dataset:** the pediatric dataset's identifiers appear
  only inside `related_datasets[0]`; no pediatric DOI, PhysioNet URL, participant
  count or ethics approval was absorbed into `resources`,
  `distribution_formats[].access_urls`, `file_collections[].download_url` or any
  other slot. **reviewed: consistent**

## Repair

Phase 4's checkers reported no findings requiring a change: the pair checker
passed, grounding reported no absent identifier, the receipts validator reported
no findings, and both records passed schema and term validation on the first
Phase 4 pass. The four corrections listed above were made in Phase 3, before the
core was re-derived, and are attested by that phase rather than by a repair
phase. No `repair` phase was run and none is recorded.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d_core.yaml` (derived, then re-derived in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_coverage_receipt.yaml` (written during Phase 1, back-ported in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_reconciliation.md` (this file)

## Commands run

```bash
poetry run d4d bundle chunk --check --project VOICE
poetry run d4d download scope --project VOICE
poetry run d4d download priority --project VOICE
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2 --project VOICE --strict
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d derive core --full <full> --out <core>
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -c "... data_sheets_schema.grounding.check_run ..."
poetry run python -c "... data_sheets_schema.report_claims.check_report ..."
poetry run d4d download scope --check --project VOICE
poetry run d4d provenance record --project VOICE --method claudecode_agent --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2 ...
poetry run d4d runs validate --project VOICE --method claudecode_agent --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2
poetry run d4d runs check --strict
```

## Prompt canonicality

The run was launched from a rendered generic-v6 instruction. `d4d api prompts
check --strict` and `d4d runs check` results for this run are reported with the
provenance record; the prompt file recorded as the run's input is
`src/download/prompts/d4d_generic_arm_prompt_v6.md` and the instruction as sent
is the rendered file passed to `--prompt-text`.

## Final result

Both records validate against their schemas and their ontology terms, the pair
checker passes on the re-derived pair with its one semantic warning reviewed,
every identifier in the record is either grounded in the bundle or a fragment
minted on the dataset's own DOI, and the coverage receipt accounts for all 22
chunks with every snippet verified.
