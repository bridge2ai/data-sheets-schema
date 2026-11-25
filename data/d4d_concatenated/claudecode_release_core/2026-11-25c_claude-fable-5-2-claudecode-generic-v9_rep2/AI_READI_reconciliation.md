# AI_READI reconciliation report

- Label: 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); Provider: Anthropic; Model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). No sampling setting was inferred from the prompt, the model name or an effort level.
- Source bundle: data/preprocessed/concatenated/AI_READI_preprocessed.txt (md5 1a58ad7be37d4b08ebd9d94e6ad173a3, 25 chunks)
- Chunk manifest: data/preprocessed/chunks/AI_READI_chunks.yaml (reported current, 25 canonical chunks under the selected rule)
- Source manifest: data/preprocessed/source_manifest.yaml
- Full record: data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_d4d.yaml
- Core record: data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_d4d_core.yaml
- Coverage receipt: data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_coverage_receipt.yaml

## Referent

The declared scope names the AI-READI dataset, https://doi.org/10.60775/fairhub.3, and declares no related-but-distinct dataset. The record describes the public release 3.0.0 of that dataset. Releases 1.0.0 and 2.0.0 are earlier releases of the same dataset; their figures appear only under related datasets, as facts about those versions. The controlled access dataset is recorded as a related dataset by name, because the bundle states that it contains the public set plus more sensitive data; its contents are not written into this record's own composition slots.

## Phase 1 - full generation

- All 25 chunks were read with the file-reading tool, in manifest order, and a receipt entry was written per chunk.
- Deviation in write order: the first write of the entry for chunk c015 failed on an ambiguous edit anchor, and chunk c016 was read before that failure was noticed. The entries for c015 and c016 were then written together, before c017 was read.
- Receipt corrections before Phase 2: entries were first written with provisional slot addresses while reading. After the record was written the receipt was rewritten once with the record's final addresses, keeping one entry per chunk, and after the first receipt check the addresses of ten multivalued scalar slots were changed from indexed to list paths. The strict receipt check passed at each run; slot coverage went from 495 of 505 to 505 of 505.
- Scratch files outside the declared outputs: the executable playbook view and the repository's own schema digest for the full target class were rendered to two files under `.temp/` so they could be read with the file tool. They hold no dataset fact. Two inline diagnostics used repository modules (the schema digest renderer and the receipt validator's uncovered-leaf list); neither produced a value in the record.
- Schema validation and term validation of the full record: passed.
- Receipt check before Phase 2: chunks 25/25 reviewed, snippets 618/618 verified, slots 505/505 with a receipt.

## Phase 2 - core derivation

The core was derived by projection from the validated full record. The command printed:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_d4d.yaml", "md5": "458dee7d855127779eb2852a1b80cc25"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against the core schema, and the pair checker passed on it.

## Phase 3 - source and provenance audit

Provenance: the only factual inputs read were the declared bundle and the selected source manifest. No previously generated D4D record, evaluation or reconciliation report was read, opened or searched. The label directory also holds another project's files from the same series; they were listed by name only and not opened.

Findings (6 recorded: 3 medium, 3 low; all 6 corrected in the full record, each with its receipt):

| # | Severity | Location in the full record | Finding | Correction |
|---|---|---|---|---|
| 1 | medium | intended uses, second entry | One entry merged six "possible future uses" listed in the IRB protocol application, which concern the study's collected information rather than uses the dataset documentation recommends. | Replaced by a single use stated in the study description: future creation of AI/ML algorithms aimed at defining disease trajectories. |
| 2 | medium | prohibited uses, fifth entry | One entry merged three prohibitions of license clause 4.B(iv). | Split into three entries; the list now has eleven entries. |
| 3 | medium | preprocessing strategies, third entry | The .FIT export cell of the protocol paper's flattened device table was attributed to the Garmin device from cell order alone. | Reworded to state the table cell without a device, added the Open mHealth standard of the two wearable directories from the dataset structure description, and recorded the limitation in the entry's caveat. |
| 4 | low | collection timeframes, second entry | The study's actual start date was stated by the study description but the start date field was empty. | Back-ported start date 2023-07-19, with the study status and anticipated completion date in the details and the one-day difference from the protocol paper in the caveat. |
| 5 | low | version access, version details | Two statements about version accessibility from different sources and years stood side by side without attribution. | Each statement is now attributed to its source. |
| 6 | low | at-risk populations | The inclusion flag rested only on answers in the IRB protocol application, which is a plan. | The description now leads with the eligibility criteria the healthsheet says were used, and receipts from that passage were added. |

Source disagreements and how they were handled (all recorded in the record's caveats):

- Start of data collection: 2023-07-19 in the dataset description and study description (ranked higher) against 18 July 2023 for the start of enrollment in the BMJ Open protocol paper. The higher-ranked value is stated.
- De-identification: the dataset description records no active de-identification because no identifiers were collected; the Nature Metabolism comment says the public set is stripped of PHI via the HIPAA Safe Harbor method. The higher-ranked statement is recorded and no method is stated.
- Enrollment targets (4000, 4,000+, 4600) differ by document and are plans; none is written as a dataset figure. The record's instance count is the 2280 participants of release 3.0.0.
- The license is named three ways in three sources; the dataset description's name is in the license field and the other two are in the caveat.
- The healthsheet's "first year" wording and the documentation page's "pilot study phase" wording disagree with the same sources' statements that this release covers data through the second year; the release-specific statements are used.
- A grant number is misspelled once in the healthsheet; the spelling of the other four sources is used.

Stated absences were not turned into entries: no data protection impact analysis, no existing uses, no use repository, no retention limit, no extension mechanism, no labels, an empty erratum answer, and a citation given only as an instruction. They are listed in the record's top-level caveat.

Deliberate omissions: variables (the only variable roster is the IRB protocol's planned list, and the lab test table is flattened so units and ranges cannot be assigned to rows); the mini-subset version of the dataset (mentioned without an identifier or a description); byte size for the dataset-level metadata files (not stated).

After the corrections: schema and term validation of the full record passed; the strict receipt check reported chunks 25/25 reviewed, snippets 628/628 verified, slots 508/508 with a receipt.

## Phase 4 - re-derivation, checks, report

- Re-derivation with the Phase 4 marker from the corrected full record (md5 5d4963d5859ad3ef202ad1019819e3f6): derived and valid. The derivation facts are those printed under Phase 2, with the new source md5.
- Pair checker: PASS, 79 schema-identical slots, projected slots resources, no errors. One warning, semantic-review-required on file collections and distributions (28 deterministic matches: 10 at collection level, 18 at nested resource level; no unmatched core distribution).
- Identifier grounding: 28 grounded, 35 minted fragments, 0 absent.
- Scope check on the pair: neither record is about a dataset the project declares distinct.
- Schema validation: full passed, core passed. Term validation: full passed, core passed.
- No checker finding required a change, so there was no repair phase.

Slot counts (top-level populated slots, informational): full 69, core 59.

## Claims

No slots were removed.

## Semantic review

- File collections against core distributions (the pair checker's warning): each of the 10 collections and 18 files in the full record has exactly one distribution with the same id, name, path, standard and size; nothing in the core lacks a counterpart. reviewed: consistent
- Total file count against the entries beneath it: the nine data type directories sum to 356,334 files and the dataset-level metadata collection holds the 9 listed files, giving the stated 356,343. The count of 9 is this record's own count of the listed files. reviewed: consistent
- Total size against the entries beneath it: the nine directories sum to 3,815,969,360,064 bytes against the stated 3,815,969,779,678; the difference of 419,614 bytes is recorded in the caveat and neither figure was adjusted. No size is recorded for the metadata collection. reviewed: consistent
- Dialect and tabular flag against the files: no file carries a dialect, so the core carries none; the tabular flag is absent in both records because the release mixes tabular, imaging and waveform data. reviewed: consistent
- Historical against current release: version, issue date, participant count, file count, size and collection period are those of release 3.0.0; the figures of releases 1.0.0 and 2.0.0 appear only in the related dataset entries. reviewed: consistent

## Files changed

- Full record: written in Phase 1, corrected in Phase 3 (six findings above).
- Coverage receipt: written during Phase 1, addresses corrected before Phase 2, receipts added in Phase 3.
- Core record: derived in Phase 2, re-derived in Phase 4. Never edited by hand.
- This report.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project AI_READI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI --check --record <full> --record <core> --strict
```

The identifier grounding check and the report-claims check were run as the inline programs the playbook gives. The provenance record, the receipt check with the write flag and the run check are run after this report is written; their results are in the provenance record, not here.

## Final result

Both records validate. The pair is consistent, every identifier is grounded or a fragment minted on the record's own identifier, the receipt covers all 25 chunks and every receiptable slot, and the scope check passes. Six audit findings were corrected in the full record; no repair phase was needed.
