# VOICE reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3`
- Method: `claudecode_release`
- Agent runtime: Claude Code (release); Provider: Anthropic; Model: claude-fable-5-2
- Mode: four-phase project agent, generic-v9 prompt; Arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/VOICE_preprocessed.txt` (md5 `9193c3cbe60b62a2fc0f704a2c4d23a3`, 22 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Chunk manifest: `data/preprocessed/chunks/VOICE_chunks.yaml` (reported `current`, 22 canonical chunks)
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). No sampling setting was inferred from the prompt, the model name or the effort level.

## Referent

The declared scope names the referent as the Bridge2AI-Voice dataset (adult), PhysioNet project DOI
`https://doi.org/10.13026/37yb-1t42`, and declares the Bridge2AI-Voice Pediatric Dataset
(`https://doi.org/10.13026/mf9s-5r03`) related but distinct, to be expressed under `related_datasets`.

The record describes that one referent at its current release, version 3.1.0 (published May 1, 2026):

- `id` is the project-level DOI as a CURIE, `doi:10.13026/37yb-1t42` (the release page labels it "DOI (latest version)").
- `doi` is the version 3.1.0 DOI, `10.13026/8xbn-nq66`, and `version` is `3.1.0`.
- Facts about releases 1.0, 1.1, 2.0.0, 2.0.1 and 3.0.0 appear only as labelled entries of `version_access.versions_available`.
- Facts about the pediatric dataset appear only in the one `related_datasets` entry.

The choice is held in both records: the core is a projection of the full record.

## Phase 1 - full generation

- Structure was taken from the schema sources under `src/data_sheets_schema/schema/` (class `Dataset` and the module files it imports). No prior D4D record was read.
- The bundle was read in manifest order, chunk by chunk, with the file-reading tool, and each chunk's receipt entry was written before the next chunk was read.
- The record was written after the last chunk. The receipt entries written during reading carried provisional slot addresses; they were corrected to the record's final structure before Phase 2 (addresses, dispositions and added quotations from chunks already read). One chunk (`c003`) changed from `extracted` to `nothing_relevant` because the grant number it quotes funds the feasibility article, not the dataset.
- The receipt checker counts a list of plain strings as one slot, so receipts for such lists (`keywords`, `version_access.versions_available`, and the like) are addressed at the list, with one quotation per item where the bundle states the items one by one.

Phase 1 gates, all on the bytes that entered Phase 2:

| Check | Result |
|---|---|
| Schema validation, class `Dataset` | No issues found |
| Term validation | Validation passed |
| Strict receipt check | chunks 22/22 reviewed; snippets 542/542 verified; slots 770/770 with a receipt (123 exempt); exit 0 |

The first run of the strict receipt check also exited 0 but reported 756/770 slots with a receipt; the 14 uncovered slots were the string-list slots described above plus one resource name, and were covered before Phase 2.

## Phase 2 - core derivation

The core was derived by `derive core` from the validated Phase 1 file. Derivation facts printed by the command:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d.yaml", "md5": "51f99448c371eca43e8e0aaabbf4b022"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against `CoreDataset` (No issues found).

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle, the source manifest, the chunk manifest. Structural inputs read: the schema sources, the playbook and its rules, and the receipt checker's source (to learn how it addresses list slots).
- No prior-run D4D record, evaluation or reconciliation report was read. Nothing under `data/d4d_concatenated/` was read other than this run's own three artifacts and its receipt.
- One scratch file outside the declared outputs was written by this run: `.temp/playbook_view_VOICE.md` (the rendered playbook view) with its empty error file `.temp/playbook_view_VOICE.err`. They hold no dataset facts.

### Findings

Six findings were recorded. Totals computed from the entries below: 6 in all, 1 medium, 5 low.

| # | Severity | Slot | Finding | Disposition |
|---|---|---|---|---|
| 1 | low | `collection_mechanisms[0].mechanism_details` | Supported omission: the documentation states that a total of 22 acoustic tasks are recorded through the app (chunk c007). | Sentence added, attributed to the documentation; receipt added to c007. |
| 2 | low | `acquisition_methods[0].acquisition_details` | Supported omission: the documentation states the countries of collection (USA and Canada) and that five recording sites are included (chunk c009). | Sentence added; two receipts added to c009. |
| 3 | low | `sampling_strategies[0].strategies` | Supported omission: the study metadata give a minimum age of 18 years, accept healthy volunteers, and exclude people who do not read or speak English (chunk c008). | Sentence added; three receipts added to c008. |
| 4 | medium | `language` | The value rests on a Healthsheet passage that ties English to v2.0.0, while the study protocol was later amended to include Spanish language speakers; no source states the languages of version 3.1.0. | Value kept as the only statement the bundle makes; the limitation is stated in the top-level `source_caveats`. |
| 5 | low | `preprocessing_strategies[1].used_software[0]` | The receipt named the tool but not its tie to the spectrograms. | Receipt added to c019 quoting the passage that describes the torchaudio-named spectrogram file. No value changed. |
| 6 | low | `is_deidentified` | The entry did not say that its statements concern the registered-access feature release, while the Data Transfer and Use Agreement describes the controlled-access data as Personally Identifiable Information. | `source_caveats` added to the entry. No value changed. |

### Audit notes without a finding

- Source conflicts. No pair of comparable statements was found that cannot both be true.
  - Grant numbers differ by source (PhysioNet 3OT2OD032720-01S1; NIH RePORTER 3OT2OD032720-01S3; feasibility article 1OT2OD032720-01). These are different awards under core project OT2OD032720, not conflicting statements about one award. The PhysioNet number is recorded and the others are named in `funders[0].source_caveats`.
  - Three author names are spelled differently in the documentation (Sui, Rudzizc, Don Bolser) than on the PhysioNet page (Siu, Rudzicz, Donald Bolser). The PhysioNet source ranks higher (tier 1 against tier 2) and its forms are used; each is noted on the creator entry.
  - Participant count is 833 in every source that states one for versions 3.0 and 3.1.
- Plans and earlier releases. Planned enrollment (10,000; 30,000), planned semi-annual updates, the Canadian research ethics board applications and the Synapse route for raw audio are stated in the tense the sources use. Healthsheet statements that name v2.0.0 or the Health Data Nexus platform are marked in `source_caveats`.
- Absences. Stated absences (no recommended splits, no erratum, no third-party IP restrictions, no export controls, no impact analysis, no use repository, "No" to confidential data) fill no slot; they are listed in the top-level `source_caveats`.
- Enumerations. `bias_type`, `limitation_type`, `maintainers[0].role`, `data_use_permission`, `hipaa_compliant` and the phenotype collection's `collection_type` are left empty because no passage states the category. `confidentiality_level` is `restricted` from "This is a restricted-access resource".
- `related_datasets[0].relationship_type`. No source names a typed relation between the adult and pediatric datasets. `references` records only that the adult release page points to the pediatric dataset; the entry's `source_caveats` says so. A reviewer who reads the rule on required enumerations more strictly would drop the entry.
- Principal investigator. Yael Bensoussan is designated principal investigator by the NIH RePORTER record and the study protocol, and Yael Bensoussan and Olivier Elemento are called co-principal investigators by the documentation. No other person is given that title. Thirteen further authors are recorded as lead investigators, the role the documentation states.
- Creators. All 122 authors of the version 3.1.0 release page are entered one per entry, each with its own receipt. Affiliations are recorded only for the fifteen people the documentation's "Who created this dataset" passage places at an institution. The feasibility article lists affiliations for more consortium members, but it is an earlier, lower-ranked roster and disagrees with the documentation for some people, so it was not used.
- Identifiers. The two person ids, the six software ids without a stated URL, the three file collection ids and the 97 file ids are labels minted on the record's own id. No registry identifier was supplied from outside the bundle.

## Phase 4 - re-derivation, checks, report

### Re-derivation

The core was re-derived from the audited full record with `--phase4-complete`. Derivation facts printed:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d.yaml", "md5": "ff4d47cd5124e66f09846bfbab3006be"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

### Deterministic checks on the final pair

| Check | Result |
|---|---|
| Schema validation, full, class `Dataset` | No issues found |
| Term validation, full | Validation passed |
| Schema validation, core, class `CoreDataset` | No issues found |
| Term validation, core | Validation passed |
| Report claims against the final pair | no findings; `claims_checked: 0` (nothing was removed, and the checker does not read the no-removal sentence) |
| Strict receipt check after the Phase 3 back-ports | chunks 22/22 reviewed; snippets 549/549 verified; slots 770/770 with a receipt (124 exempt); exit 0 |
| Pair consistency | PASS: 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class`, `conforms_to_schema`; one `semantic-review-required` warning |
| Identifier grounding | grounded 1, minted_fragment 108, absent 0 |

Receipt diagnostics reported and not gated: 14 snippets bear on no token of their value (receipts for true/false and enumeration values, whose quotation cannot share a token with the value), and 30 entry receipts overlap one leaf.

No checker finding required a change to the full record after re-derivation, so there was no repair phase.

## Claims

No slots were removed.

Between the Phase 1 record and the final record, content was only added: one sentence to each of three existing values (findings 1 to 3), text to the existing top-level `source_caveats` (finding 4), and a new `source_caveats` on the existing `is_deidentified` entry (finding 6).

## Semantic review

- `file_collections` <-> `distributions` (the pair checker's `semantic-review-required` warning): 100 deterministic matches, 3 at collection level and 97 at file level, no unmatched core distribution; each core distribution carries the id, name, path, description and format of the collection or file it was built from. reviewed: consistent
- Counts and sizes against the entries beneath them: `total_file_count`, `total_size_bytes`, `file_count` and `total_bytes` are populated in neither record, because the bundle states no file count or size; the features collection lists the 11 files the release page names and says in its caveat that the unnamed data dictionary files are not entered. reviewed: consistent
- `dialect` and `is_tabular` against the files: neither is populated in either record and no file carries a dialect; the release mixes Parquet tensor files with tab-separated tables, and no source classifies the dataset as tabular. reviewed: consistent
- Historical versus current release: the record's own slots use the version 3.1.0 page (its per-file counts, its phenotype tree, its author list, its release date); the 3.0.0 and 1.1 pages feed only `version_access.versions_available`; Healthsheet statements tied to v2.0.0 are marked in `source_caveats`. reviewed: consistent

## Scope check

`download scope --check --strict` on the final pair: "2 record(s) checked against the declaration"; "none is about a dataset its project declares distinct"; exit 0. The command says it checks the record's `id` only and does not inspect prose that discusses a related dataset.

## Files changed

- Written: the full record, the core record (derived twice, the second time with the Phase 4 header line), the coverage receipt, this report.
- The core record was never edited by hand.

## Commands

All run from the checkout root with `.venv/bin/python`.

1. `-m data_sheets_schema.cli agents playbook --relative-toolchain`
2. `-m data_sheets_schema.cli bundle chunk --bundle ... --chunk-manifest ... --manifest ... --check --strict`
3. `-m data_sheets_schema.cli download scope --manifest ... --project VOICE`
4. `-m data_sheets_schema.cli --manifest ... download priority --project VOICE`
5. `-c 'from linkml.validator.cli import cli; cli()' -s <full schema> -C Dataset <full>` (Phases 1, 3 and 4)
6. `-c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema <full schema> --target-class Dataset` (Phases 1, 3 and 4)
7. `-m data_sheets_schema.cli --manifest ... receipts check --method claudecode_release --label ... --project VOICE --bundle ... --chunk-manifest ... --strict` (before Phase 2, after re-addressing, and after the Phase 3 back-ports)
8. `-m data_sheets_schema.cli derive core --full <full> --out <core>` (Phase 2), then with `--phase4-complete` (Phase 4)
9. `-m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>`
10. The playbook's grounding program (`data_sheets_schema.grounding.check_run`)
11. The playbook's report-claims program (`data_sheets_schema.report_claims.check_report`) on this report
12. `-c 'from linkml.validator.cli import cli; cli()' -s <core schema> -C CoreDataset <core>`
13. `-m data_sheets_schema.cli download scope --manifest ... --project VOICE --check --record <full> --record <core> --strict`
12a. `-c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema <core schema> --target-class CoreDataset`

Two steps follow this report and their output is not recorded in it, because the provenance record pins this file's bytes:

14. `-m data_sheets_schema.cli provenance record ...` as rendered, with one `--phase` flag per phase performed (`generate_full`, `derive_core`, `source_audit`, `reconcile`, `report`)
15. The strict receipt check again with `--write`

## Final results

- Full record: 70 top-level slots, 1,526 lines; schema and term validation pass.
- Core record: 61 top-level slots, 1,184 lines; schema validation passes; header carries `# Sources:` and `# Phase 4 reconciliation: completed`.
- Phase 3: 6 findings (1 medium, 5 low), all dispositioned in the full record; no slot removed.
- Phase 4: pair check PASS, grounding 0 absent, 4 semantic review rows all consistent, no repair.

## Limits of this report

- Token usage, tool counts and timing are not reported here: the project agent cannot observe its own accounting. The whole-run transcript audit is the orchestrator's step and was not run by this agent.
- Reasoning effort is asserted by the launcher's recorder line, not observed by this agent.
- The receipt checker verifies that each quotation is in its chunk, not that it supports the value beside it; and it cannot tell that the three chunks marked `nothing_relevant` (`c001`, `c003`, `c004`) held nothing for the record.
