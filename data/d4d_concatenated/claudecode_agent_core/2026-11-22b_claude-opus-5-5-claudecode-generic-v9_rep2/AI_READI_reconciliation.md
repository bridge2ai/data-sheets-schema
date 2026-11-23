# AI_READI reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2

- Runtime: Claude Code; provider Anthropic; model claude-opus-5-5; four-phase project agent, generic-v9 prompt
- Arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 1a58ad7be37d4b08ebd9d94e6ad173a3, 25 chunks)
- Chunk manifest: `data/preprocessed/chunks/AI_READI_chunks.yaml` (current, 25 canonical chunks under the selected rule)
- Source manifest: `data/preprocessed/source_manifest.yaml`; profile `bridge2ai`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime)

## Referent choice

The declared scope names one referent, the AI-READI dataset at DOI 10.60775/fairhub.3, and
declares no related-but-distinct dataset. Both records describe **version 3.0.0 of the public
FAIRhub release** (`id: doi:10.60775/fairhub.3`, released 2025-11-17, 2280 participants,
356,343 files). The bundle's FAIRhub structured metadata, healthsheet, README and v3
documentation all describe that release. Facts about other things the bundle describes are
kept out of the referent's own slots:

- versions 1.0.0 (doi:10.60775/fairhub.1) and 2.0.0 (doi:10.60775/fairhub.2) are recorded
  only under `related_datasets` and `version_access`;
- the controlled-access dataset (zip code, sex, race/ethnicity, genetic data, health records,
  medications, accident reports), its Data Access Committee and data use agreement are
  described only in `sensitive_elements` and `source_caveats`, as data held separately;
- the study biorepository (biospecimens) is not part of the data release and is mentioned only
  in caveats;
- plans in the BMJ Open protocol and the IRB protocol (target enrollment, longitudinal arm,
  planned release dates) are not recorded as current facts.

## Phase 1 — full generation and coverage receipt

Read in chunk-manifest order with the Read tool. c018, c019, c022, c023 and c024 were each
read in two windows that together cover the chunk. **Deviation:** c013 (lines 2661–2739) and
c014 (lines 2740–2812) were opened in a single Read window, so the c013 receipt entry was
written after c014 had been read rather than before. Every other entry was written before
the next chunk was opened.

Dispositions: 22 chunks `extracted`; 3 `nothing_relevant` (c001 preamble/table of contents,
c006 reference list, c008 commentary author roster and affiliation key).

Phase 1 corrections before Phase 2 (receipt addresses only, using chunks already read):

- re-addressed receipts after referent decisions taken while reading: race/ethnicity groups
  moved from `subpopulations[0]` to `sampling_strategies[0]`; controlled-access element lists
  moved from `confidential_elements[0]` to `sensitive_elements[0]`, since the healthsheet
  states the data are not confidential;
- dropped receipt pairs for values not carried because their subject is not the referent:
  the biorepository's finite samples (a study limitation, not a data limitation), the Data
  Access Committee and controlled-access approval process, and the IRB protocol's planned
  medical-record and Department of Licensing extraction (controlled-access data);
- re-indexed `known_limitations` after that removal; split raw-format receipts into one
  entry each for ECG, MoCA and NORC lab output; changed two `data_collectors[*].id` snippets
  to the passages that carry the ROR identifiers; moved the transport-cost snippet from a
  sub-slot to the `participant_compensation[0]` entry;
- added receipts for four slots the first check reported unreceipted (`keywords`,
  `related_datasets[1]`, `file_collections[9].description`). The fourth was the minted
  name of the root-metadata collection; that value was removed from the record
  instead of being receipted.

Checks before Phase 2: schema validation `No issues found`; term validation passed;
`receipts check --strict` exit 0: chunks 25/25 reviewed, snippets 347/347 verified, slots
523/523 with a receipt (41 exempt).

## Phase 2 — core derivation

`derive core` ran on the validated Phase 1 file and printed:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml", "md5": "372c8cbefbe059aa87a5e718bf7f070b"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against `CoreDataset` (`No issues found`).

## Phase 3 — source and provenance audit

### Provenance

Files read in this run: the provenance guard, the playbook and its executable view, the
uniform rules, `d4d-agent.md`, the declared bundle (25 chunk windows), the chunk manifest,
the source manifest through the `download scope` and `download priority` commands, the
schema digest produced by the package's `schema_digest`, targeted lookups in the full schema
YAML (prefixes, a few slot ranges), the receipt validator's source code (for snippet
normalization) and the prompt rendered by `prompt render`. No prior full or core D4D record,
evaluation or reconciliation report from any label was opened, searched or listed. Phase 2
read only this run's full record. Result: **provenance boundary respected.**

### Findings

| # | Severity | Slot(s) | Source (chunk) | Finding | Action |
|---|---|---|---|---|---|
| 1 | moderate | `third_party_sharing[1]` | v3 docs (c011) | The entry described the full, controlled-access dataset under a data use agreement, a distinct set and not this public release. | Entry removed from the full record; the statement remains in `source_caveats`; its receipt pair removed from c011. |
| 2 | minor | `sampling_strategies[2]` | BMJ Open (c002) | The paraphrase said under- and oversampling was used "to monitor diversity"; the source says the composition is monitored for diversity and adjusted by under- and oversampling as needed. | Rewritten to match the source. |
| 3 | minor | `is_deidentified.source_caveats` | FAIRhub API (c015) | The caveat interpreted the `deIdentDirect`/`deIdentHIPAA` flags, which the sources do not define. | Rewritten to report the field values without interpretation. |
| 4 | minor | `creators[2..14,16].principal_investigator.affiliation` | FAIRhub study description (c020, c021) | Omission: each study principal investigator's affiliation and ROR identifier is stated but was carried only for two of them. | Back-ported 14 affiliations with receipts. |
| 5 | minor | `conforms_to_standard`, `file_collections[0..8].conforms_to_standard` | FAIRhub structure metadata (c015–c017), README (c019) | Omission: every datatype directory names its standards (CDS plus WFDB, OMOP CDM, ESDS, DICOM or Open mHealth), but the enum slot was empty. | Back-ported with receipts. |
| 6 | minor | `total_file_count`, `total_size_bytes` | FAIRhub API (c015–c018) | The relation between the stated totals and the per-directory figures was undocumented. | Added this record's arithmetic to `source_caveats` (see Semantic review). |

Totals from the entries above: 6 findings, 1 moderate and 5 minor. Three were corrections and
three were back-ported omissions.

Checked and found consistent: identifiers (DOI, ORCIDs and RORs all taken from the bundle in
CURIE form); version and release dates (FAIRhub page, API and healthsheet agree); counts
(2280 participants = 204 + 863 + 1213 in the README change table); license identity (three
names, one rights DOI, recorded in caveats); and dated statements, where historical values
carry explicit version scope.

Genuine source conflicts, each recorded in `source_caveats` with what each source says:

- The v3 documentation (tier 2) says v3.0 "contains data from the participants of the pilot
  study phase", while the FAIRhub metadata and healthsheet (tier 1) give 2280 participants
  collected from July 19, 2023 to May 1, 2025. The tier-1 value is preferred.
- The Nature Metabolism commentary (tier 3) says the public set is stripped of PHI via HIPAA
  Safe Harbor. The FAIRhub metadata (tier 1) gives `NoDeIdentification` with no active
  de-identification. The tier-1 value is preferred.
- The healthsheet spells the grant number OT2ODO32644 in one answer; the same file's
  fundingReference and NIH RePORTER give OT2OD032644, which is the value recorded.

Differences that are compatible and kept: the pilot enrollment start of July 18, 2023 (BMJ
Open) against a collection start of July 19, 2023 (FAIRhub); the "Equitable" and
"Exploratory" expansions of the project name; planned enrollment of 4,000 against 4,600 in
the IRB protocol (both plans); and the license's grant of research and commercial use against
the T2D-research-only access attestation.

After the corrections the full record was re-validated: schema validation `No issues
found`; term validation passed; `receipts check --strict` exit 0 with chunks 25/25 reviewed,
snippets 382/382 verified and slots 558/558 with a receipt (41 exempt).

## Phase 4 — re-derivation, checks, report

The core was re-derived from the corrected full record with `--phase4-complete` (source md5
e1354d0111917fcf9861e8b7a0e8a07a; same rule and slot lists as Phase 2) and validated. Results:

- Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources']`, plus one
  warning, `semantic-review-required` on file_collections ↔ distributions (28 deterministic
  matches, 10 at collection level and 18 at nested resource level, no unmatched core
  distributions).
- Grounding: `{'grounded': 27, 'minted_fragment': 28, 'absent': 0}`. No identifier is absent
  from the bundle.
- Scope check (`--strict`, both records): passed; no record describes itself as a dataset its
  project declares distinct.
- Schema and term validation passed for both records.

The minted fragments are the 10 file-collection ids and 18 file ids. Each sits on the record's
own id, `doi:10.60775/fairhub.3`, because the schema requires an id for those objects and
the core's distributions copy them.

Header note: `derive core` writes the core header's `# Schema:` line as the relative
`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, while the launch instruction
gives the absolute path. The playbook forbids editing the core by hand, so the line was left
as derived. Every other core header line matches the instruction's block, including
`# Sources:` and `# Phase 4 reconciliation: completed`.

No repair phase was needed: neither the grounding check nor the pair checker reported a
finding that required a change.

## Claims

No slots were removed.

Changes below slot level, compared with the first Phase 1 write: the `third_party_sharing[1]`
entry was removed in Phase 3 (finding 1), and the minted `name` of the root-metadata file
collection was dropped in the Phase 1 correction. Each slot named here is still present in
the final record.

## Semantic review

- file_collections ↔ distributions (pair checker `semantic-review-required`): the 10 core
  collection-level distributions match the 10 full `file_collections` by id, name, path,
  description, conforms_to, conforms_to_standard and bytes (= total_bytes). The 18 file-level
  distributions match the File entries by id, name, path, format and media_type. The
  root-metadata collection has no total_bytes because the bundle states none.
  **reviewed: consistent**
- Counts and sizes against the entries beneath them: the nine datatype directories'
  `file_count` values sum to 356,334 (this record's arithmetic), 9 fewer than
  `total_file_count` 356,343, which equals the nine listed root-level files. Their
  `total_bytes` sum to 3,815,969,360,064, 419,614 below `total_size_bytes`
  3,815,969,779,678; the bundle gives no size for the root-level files. Both differences are
  recorded in `source_caveats`, and neither stated total was adjusted.
  **reviewed: corrected** (the caveat was added in Phase 3)
- `dialect` and `is_tabular` against the files: no File carries a dialect, so the core has
  none. `is_tabular` is not populated because the release mixes tabular, imaging and waveform
  data (DICOM, WFDB, Open mHealth, CSV), so neither value applies to the whole dataset.
  **reviewed: consistent**
- Historical and current release: every current-state slot describes v3.0.0. Versions 1.0.0
  and 2.0.0 appear only in `related_datasets` and `version_access` with their dates and
  participant counts. The BMJ Open statement that a release was "planned for November 2024"
  is recorded as a past release date, and the v3 documentation's "pilot study phase"
  sentence was not adopted. **reviewed: consistent**

## Files changed

- Full record: written in Phase 1, corrected in Phases 1 and 3.
- Coverage receipt: written chunk by chunk in Phase 1; addresses corrected in Phase 1; Phase 3
  back-port pairs added to the existing c015, c016, c017, c020 and c021 entries; one pair
  removed from c011.
- Core record: derived in Phase 2 and re-derived in Phase 4. Never edited by hand.
- This report.
- Scratch files outside the three named outputs, all in the gitignored `.temp/`: the
  executable playbook view, the schema digest, the rendered prompt, receipt-check output and
  derivation JSON. **Deviation** from "do not write outside these three"; nothing else in
  the tree was changed.

## Commands

```bash
.venv/bin/python -m data_sheets_schema.cli agents playbook
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project AI_READI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml prompt render --project AI_READI --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2 --condition generic_v9 --runtime 'Claude Code' --out .temp/rendered_prompt.md
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "<grounding check_run program from the playbook>"
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI --check --record <full> --record <core> --strict
.venv/bin/python -c "<report_claims check_report program from the playbook>"
```

## Final results

- Full record: schema-valid, term-valid, strict receipt check passed.
- Core record: derived, schema-valid, term-valid, `# Phase 4 reconciliation: completed`.
- Pair: PASS. Grounding: 0 absent. Scope: passed. Semantic review: four rows, three
  consistent and one corrected.
- Reconciliation outcome: 6 Phase 3 findings, 1 moderate and 5 minor, all resolved in the
  full record and carried to the core by re-derivation. No repair phase.
