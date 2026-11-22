# VOICE reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3

- Agent runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt (`src/download/prompts/d4d_generic_arm_prompt_v9.md`)
- Arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/VOICE_preprocessed.txt` (bundle md5 `9193c3cbe60b62a2fc0f704a2c4d23a3`, 22 chunks under `data/preprocessed/chunks/VOICE_chunks.yaml`)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed and not asserted.

## Referent

The declared scope (`download scope --project VOICE`) names the referent as the
Bridge2AI-Voice dataset (adult), `https://doi.org/10.13026/37yb-1t42`, and declares
the Bridge2AI-Voice Pediatric Dataset (`https://doi.org/10.13026/mf9s-5r03`) as related
but distinct, to be expressed through `related_datasets` (in the bundle as
`physionet_pediatric_1_1_0`).

Chosen referent: the adult Bridge2AI-Voice dataset at its current PhysioNet release
3.1.0 (published May 1, 2026). Both records carry `id: doi:10.13026/37yb-1t42` (the
project-level DOI the release page labels "DOI (latest version)") and
`doi: 10.13026/37yb-1t42`; the 3.1.0 version DOI `10.13026/8xbn-nq66` appears in the
citation and in `version_access.versions_available`. Earlier releases (1.0 on Health
Data Nexus, 1.1, 2.0.0, 2.0.1, 3.0.0) are recorded only as version history. Pediatric
facts (300 participants aged 2-18, 23,533 recordings, Hospital for Sick Children,
its own ethics board) appear only in `related_datasets[0]`. The feasibility-study
participants (47 pilot participants, no audio collected) are not described as
participants of this dataset; that article is listed only as an external resource.

## Phase 1 — full generation (summary)

- Chunk manifest check: `bundle chunk --check --strict` reported `current`, 22
  canonical chunks.
- All 22 chunks were opened with the file-reading tool, in manifest order, and each
  got a receipt entry: 17 `extracted`, 5 `nothing_relevant` (c001, c003, c004, c010,
  c014).
- Order deviation, recorded: c001 and c002 were opened in a single parallel tool call,
  so c001's receipt entry was written after c002 was opened rather than before. From
  c003 on, every entry was written before the next chunk was opened.
- Phase 1 receipt corrections (before Phase 2, using chunks already read): the first
  strict check passed (22/22 chunks, 382/382 snippets) but reported 1 addressing slip
  (`creators[1].principal_investigator`, corrected to `creators[3]`, where Olivier
  Elemento sits in the author order), 4 populated slots without a receipt (`keywords`,
  `instances[0].label`, `participant_compensation[0].compensation_provided`,
  `related_datasets[0].relationship_type`), and 5 snippets filed under
  `sampling_strategies[0].strategies` that support `sampling_strategies[0].description`.
  Addresses were corrected and receipts added. A second pass found
  `sampling_strategies[0].is_representative` unreceipted, and a receipt was added. Final
  Phase 1 state: 22/22 chunks, 395/395 snippets verified, 321/321 receiptable slots
  with a receipt.
- Full record validated (schema: no issues; term validation: passed) before Phase 2.

## Phase 2 — core derivation

Command: `derive core --full <full> --out <core>` (registered spelling). The core
validated against `CoreDataset` (linkml-validate: no issues). Derivation facts printed
by the command:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d.yaml", "md5": "57f53c1426ccfff9d24483786871f8d4"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The md5 above is the Phase 1 full record. Phase 4 re-derived the core from the
Phase 3-corrected full record. That command printed the same rule, slots and
`identity_slots: 79`, plus a new `from.md5` for the corrected full record.

Core header note: the derive command writes `# Schema:
src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (repository-relative).
The launch instruction's CORE HEADER BLOCK gives the absolute path to the same file.
The core is never edited by hand, and the registered derive command has no flag for
this line, so the derived header is kept as written. It points to the same schema
file. Every other line matches the mandated block, including `# Sources:` and
`# Phase 4 reconciliation: completed`.

## Phase 3 — source and provenance audit

Provenance: the only factual inputs read were the declared bundle (via the 22 chunk
windows), the source manifest's VOICE scope, priority and naming declarations, and
the schemas, read through the repository's schema digest renderer and direct schema
queries. No prior generated D4D record, evaluation output or earlier reconciliation
report was opened. Other projects' files in the same version directories were listed
by name only and never read.

Source ranking used (`download priority --project VOICE`): PhysioNet pages tier 1;
project documentation, IRB protocol, DUA and documentation repository tier 2;
feasibility publication and white paper tier 3; NIH RePORTER tier 4. PhysioNet 3.1.0
is the current release; 3.0.0 is superseded by it.

Recorded findings:

| # | Slot(s) | Severity | Finding | Source (chunk) | Action |
|---|---|---|---|---|---|
| 1 | `content_warnings[0].warnings` | moderate | The healthsheet says the dataset includes transcriptions of free speech tasks. The same documentation says transcriptions from open-response prompts are removed from the feature-only dataset, the v1.1 notes say free-speech transcripts were removed, and the 3.1.0 file description names no transcript file. The unqualified current-state claim was not established. | c008, c009, c015, c019 | Corrected: the warning is attributed to the healthsheet, and the conflict is recorded in `content_warnings[0].source_caveats` |
| 2 | `language` | minor | "English" comes from the healthsheet (the v2.0.0-era option). IRB protocol revision V11 (February 10, 2025) added Spanish-language data collection. | c009, c011 | Corrected: top-level `source_caveats` added; the value is kept as stated |
| 3 | `sampling_strategies[0].description` | minor | The English-only exclusion criterion is from the project documentation's study metadata and was stated without that scope. | c008, c011 | Corrected: criteria attributed to their sources; `sampling_strategies[0].source_caveats` added |
| 4 | `version_access.version_details` | minor | The record tied the healthsheet's "end of November, 2024" publication date to the Health Data Nexus release by inference. | c009 | Corrected: restated as the healthsheet's own statement within its Health Data Nexus distribution answer |
| 5 | `sampling_strategies[0].description` | minor | Omission: the study metadata state healthy volunteers are accepted. | c008 | Back-ported with receipt |
| 6 | `data_governance.access_review_process` | minor | Omission: the Data Use Agreement (DUA) step of the controlled-access route. | c008 | Back-ported with receipt |

Finding totals, computed from the six rows above: 6 findings (1 moderate, 5
minor), 6 corrected, 0 left open.

Other audit checks, no change needed:

- Counts. `instances[0].counts: 833` matches PhysioNet 3.1 ("833 participants")
  and the healthsheet ("around 833 instances"). The release notes are consistent
  with it: 306 (v1.0) + 136 (v2.0) + 391 (v3.0.0) = 833, and v3.1.0 added no new
  participants. This sum is the audit's own arithmetic and is not written into the
  record.
- Target sizes. 10,000 voices (project documentation) and 30 000 participants (IRB
  protocol) are both tier 2 and are stated targets, not counts of the release. The
  white paper (tier 3) also states 30 000. Both are kept in `purposes[1]` with a
  caveat; neither is presented as a count of the release.
- Principal investigators. NIH RePORTER and the IRB protocol designate Yael
  Bensoussan as principal investigator. The project documentation names Bensoussan
  and Olivier Elemento as co-principal investigators. Both carry
  `principal_investigator` objects. No lead investigator or author was promoted to
  PI.
- Grant numbers. OT2OD032720 (core), 3OT2OD032720-01S1 (PhysioNet acknowledgment)
  and 3OT2OD032720-01S3 (the RePORTER record retrieved) are award numbers under one
  core project, so they do not conflict. The PhysioNet platform grants
  (R01EB030362, U24EB037545) fund PhysioNet, not this dataset, and are not recorded.
- Relationship type. `related_datasets[0].relationship_type: references` records that
  the adult release page links to the pediatric dataset. No source states a stronger
  relation, and the entry's `notes` say so.
- Identifiers. Every DOI and URL in identifier slots appears in the bundle. Person
  ids are fragments on the record's own id, because no ORCID is stated. Software ids
  are the GitHub URLs the bundle gives. No ROR, ORCID or other registry identifier
  was supplied from outside the bundle.
- Enumerations. The only enumeration values set are `collection_type: metadata`
  (the passage states "metadata related to the specific audio task and recording"),
  file `format: TSV` and `media_type: text/tab-separated-values`, taken from the
  `.tsv` extensions, and `relationship_type`. No `bias_type`, `limitation_type`,
  `data_use_permission` or `hipaa_compliant` value was set, because no passage
  states the category.
- `raw_data_format` and `principal_investigator` checked against the v9 rules:
  `raw_data_format` is not populated, and the PIs are as above.

## Phase 4 — re-derivation, checks, report

1. The core was re-derived from the corrected full record with `--phase4-complete`
   and validated against `CoreDataset` (no issues; term validation passed).
2. Pair checker (`d4d_pair_consistency`): PASS, 79 schema-identical slots; projected
   slots `resources`; per-record slots `conforms_to_class` and `conforms_to_schema`;
   one `semantic-review-required` warning (file_collections ↔ distributions, 14
   deterministic matches: 3 collections and 11 files; 0 unmatched).
3. Grounding (`check_run`): `{'grounded': 1, 'minted_fragment': 16, 'absent': 0}`.
   No identifier is stated without bundle support.
4. Scope check (`download scope --check --strict` on the pair): neither record
   identifies itself as the pediatric dataset.
5. Receipts (`receipts check --strict`) after Phase 3: 22/22 chunks, 403/403
   snippets verified, 321/321 receiptable slots with a receipt. One snippet shares
   no token with its value (`related_datasets[0].relationship_type`, an enum chosen
   from a linking sentence; see Phase 3).
6. Schema and term validation re-run on both records: all passed.

No checker finding required a change to the full record after Phase 3, so there was
no repair phase.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions` (pair-checker warning): the 3 collections
  (features, metadata, phenotype) and 11 feature files appear as 14 core distributions
  with the same ids, names, descriptions, paths, and TSV format/media type. The
  `collection_type: metadata` value is full-only by projection. **reviewed: consistent**
- `total_file_count` / `total_size_bytes` / `file_count` / `bytes` against the entries
  beneath them: none is populated in either record. The bundle gives per-file record
  counts (n=…), not file counts or sizes, and the phenotype and metadata folders are
  described without a complete file enumeration that would support a total.
  **reviewed: consistent**
- `dialect` and `is_tabular` against the files: no File carries a dialect, so the core
  has none, and `is_tabular` is omitted in both. The release mixes parquet tensors
  and TSV tables, and no passage classifies the dataset as tabular.
  **reviewed: consistent**
- Historical versus current release: `version` 3.1.0, `issued` 2026-05-01, the
  833-participant count, the file list (including `audio_quality_metrics.tsv` and the
  metadata folder, new in 3.1.0) and the de-identification statement "removed from
  v3.1" all describe the current release. Facts about 1.0, 1.1, 2.0, 2.0.1 and 3.0.0
  appear only in `version_access` and `distribution_dates`. Healthsheet statements
  that predate 3.x are attributed to the healthsheet: the 12-month collection period
  in `collection_timeframes[0]`, the English-only language and the Health Data Nexus
  distribution. **reviewed: corrected** (Phase 3 findings 1–4)
- Shared projected content (creators, funders, purposes, uses, ethics,
  de-identification, related_datasets): identical in both records by projection, and
  each value was checked in Phase 3 against the subject of its source passage.
  **reviewed: consistent**

## Files changed

- Created: `VOICE_d4d.yaml` (full), `VOICE_d4d_core.yaml` (core),
  `VOICE_coverage_receipt.yaml`, `VOICE_reconciliation.md` (this report), and, after
  this report, `VOICE_provenance.yaml` and the receipts sidecar written by the
  recorder.
- Helper script (diagnostic, read-only): `scripts/adhoc/voice_receipt_findings_2026-11-22b.py`.

## Commands run

- `.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict`
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE`
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE`
- `.venv/bin/python -m data_sheets_schema.cli agents playbook`
- `.venv/bin/python -m data_sheets_schema.cli prompt render --project VOICE --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3 --condition generic_v9 --runtime 'Claude Code' --out .temp/VOICE_rendered_v9.md`
- linkml-validate (Dataset, CoreDataset) and linkml-term-validator on both records, as registered
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3 --project VOICE --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --strict` (Phase 1, three times; Phase 3, once)
- `.venv/bin/python -m data_sheets_schema.cli derive core --full … --out …` (Phase 2) and the same command with `--phase4-complete` (Phase 4)
- `.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full … --core …`
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE --check --record … --record … --strict`
- grounding `check_run` and report-claims `check_report`, as registered

## Final results

- Full record: schema valid, term validation passed; 63 top-level slots populated.
- Core record: schema valid, term validation passed; 58 top-level slots populated.
- Pair: PASS. Grounding: 0 absent. Scope: in scope. Receipts: strict pass.
- Reconciliation outcome: 6 Phase 3 findings, all corrected in the full record and
  propagated by re-derivation. No Phase 4 repair was needed.
