# CM4AI reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1

- Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt · Arm: BASELINE (input documents only)
- Bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 50037fc631eafda807e19f83f6579818, 28 chunks)
- Chunk manifest: `data/preprocessed/chunks/CM4AI_chunks.yaml` · Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed.

## Referent

The manifest scope declares the referent "CM4AI (Cell Maps for Artificial Intelligence) dataset",
`referent_id` https://cm4ai.org/, with the note that the four Dataverse releases (B35XWX, F3TD5R,
K7TGEM, HIGT4C) are releases of this dataset, and no related-but-distinct datasets. Both records
take that referent: top-level `id` and `page` are https://cm4ai.org/, and the four releases are
entries under `resources` (ids `doi:10.18130/V3/B35XWX`, `doi:10.18130/V3/F3TD5R`,
`doi:10.18130/V3/K7TGEM`, `doi:10.18130/V3/HIGT4C`). Facts specific to one release are kept on
that release's entry. Top-level facts about governance, intended uses, limitations, biases,
completeness and maintenance come from the June 2026 release (HIGT4C, source tier 1), which the
project's release page names as the latest data release.

The Nature article (Schaffer et al. 2025) studies U2OS cells and does not state that it uses the
CM4AI releases. It is recorded only as `external_resources[0]`, linked through the shared award
number OT2 OD032742. It is not recorded as an existing use, and its methods were not copied into
the referent's collection or preprocessing slots.

## Phase 1 — full generation

- 28/28 manifest chunks were read with the file-reading tool in manifest order, and a receipt
  entry was written per chunk. Dispositions: 16 extracted, 10 nothing_relevant, 2 redundant_with
  (c021 → c020, c024 → c023).
- Deviation from the reading order: chunks c008 and c009 (lines 2425–2893) were opened in a
  single Read window, so c008's entry was written after c009 had been read. c009 is the
  nature.com footer (nothing_relevant). Every other chunk was read and receipted one at a time.
- Receipt correction loop before Phase 2, allowed by the playbook. All corrections reuse chunks
  already read. Entries were first written with provisional slot paths and were re-addressed to
  the final record's paths once the record was composed. Seven receipts were added for leaves the
  check reported uncovered: `id`, `preprocessing_strategies[1].name`, the
  `ethical_reviews[*].description` entries, `distribution_dates[0].description`,
  `distribution_formats[1].format` and `file_collections[*].name`. One snippet that the checker
  found in the adjacent chunk (MuSIC pipeline name, c011 → c010) was moved to its own chunk.
  Three dispositions changed between the first write and the final receipt:
  - c007: from nothing_relevant to extracted, for the acknowledgement on `external_resources[0]`;
  - c002, c003, c005 and c008: the Nature article was moved from the provisional
    `existing_uses[0]` to `external_resources[0]`, because the article does not state that it
    uses CM4AI data;
  - the NIH RePORTER keyword receipts were dropped. `keywords` carries only the Dataverse keyword
    line.
- Validation before Phase 2: schema validation `No issues found`, term validation
  `✅ Validation passed`, strict receipt check exit 0 (28/28 chunks, 359/359 snippets verified,
  542/542 slots with a receipt, 59 exempt).

## Phase 2 — core derivation

The core was derived with the registered command. Its derivation facts (final Phase 4 run):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml", "md5": "ba67dceee48c736b530bff2ffe5f02c3"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The first derivation (Phase 2, before the Phase 3 change) validated with `linkml-validate: No
issues found`.

Header note: `derive core` writes `# Schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
(repository-relative). The launch instruction's CORE HEADER BLOCK gives the absolute path to the
same file. The core was not edited by hand, as the playbook requires, and the registered command
was run as written. Both spellings name the same file, so this line is the only difference from
the block as specified.

## Phase 3 — source and provenance audit

Provenance: the only files read for facts were the declared bundle, the source manifest, the
chunk manifest and the schemas (through the repository's digest). No other run's D4D record,
receipt, report or evaluation was opened. The output directories were listed by file name only,
to confirm that no CM4AI artifact existed under this label.

Recorded findings (2):

| # | Severity | Slot | Finding | Action |
|---|---|---|---|---|
| 1 | minor | `resources[3].citation` | The release citation shortened the author list with "...", which is not the source's text (c026). | Corrected: the full 47-author citation was restored and its receipt replaced with the verbatim author string. |
| 2 | minor | `ethical_reviews[1].description` | The receipt snippet "and Jean-Christophe Belisle-Pipon" did not include the "Ethical Review" heading that the value restates. | Corrected: the snippet now quotes the heading and both names (c026). |

Totals, counted from the table: 2 findings, 2 minor, 0 major, 2 corrected.

Audited and kept without change:

- **Source conflicts.** The release page labels the June 2026 release "Released on: June 17,
  2025", while its Dataverse record (tier 1, above the tier 2 page) gives 2026-06-17. The Dataverse
  date is used, and the conflict is recorded in `resources[3].source_caveats` and the top-level
  `source_caveats`. The March 2025 page shows "Version 1.4" while its citation ends "V1"; both are
  recorded on `resources[0]`.
- **Funders.** The Dataverse releases list only NIH 1OT2OD032742-01. The preprint's
  acknowledgement adds 5U54HG012513-02 and the Frederick Thomas Fund of the University of
  Virginia, and NIH RePORTER gives 3OT2OD032742-01S2. These are compatible observations, not a
  conflict; each is kept with its source named in `funders[*].source_caveats`.
- **Tense and status.** Preprint statements dated May 2024 are qualified as such:
  `data_governance.description` (Data Access Committee "will supervise"),
  `preprocessing_strategies[1]` (ARK PIDs, DOIs "a future feature"), and the cell-map pipeline and
  labeling. The cell-map pipeline and labeling carry caveats that the June 2026 release excludes
  computed cell maps. Planned items keep their status ("coming soon" in `subpopulations`,
  "will be added in future releases" in `known_limitations[1]`).
- **Identity.** `principal_investigator` is used only because NIH RePORTER designates "Principal
  investigator: IDEKER, TREY". The ORCID ids for the data governance contact (Jillian Parker) and
  the ethical review contacts (Vardit Ravitsky, Jean-Christophe Belisle-Pipon) come from the same
  release's author list. They were matched by surname and initial, and each match is stated in
  that object's `source_caveats`. Creators with no stated ORCID carry no `id`.
- **Absences.** "FDA Regulated: No" and "Human Subjects: No" are not recorded as restriction
  entries. The first is a caveat; the second fills `human_subject_research.involves_human_subjects:
  false`. Embargoed Perturb-seq links are not recorded as external resources; they are described
  under `missing_data_documentation[0]`.
- **Enumerations.** `bias_type`, `limitation_type` and `collection_type` are left empty because no
  passage states the category. File `format`, `media_type`, `file_type` and `compression` are read
  from the file names and extensions.

## Phase 4 — re-derivation, checks, repair

- Core re-derived with `--phase4-complete` from the corrected full record (md5
  ba67dceee48c736b530bff2ffe5f02c3); it validated in the command.
- Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources']` and one warning,
  `semantic-review-required` on `$.file_collections <-> $.distributions` (38 deterministic
  matches: 4 at collection level, 34 at file level; no unmatched core distributions).
- Grounding: `{'grounded': 43, 'minted_fragment': 0, 'absent': 0}`. No absent identifiers.
- Scope check (`download scope --check --strict`, both records): "none is about a dataset its
  project declares distinct".
- Schema and term validation of both records: no issues, and term validation passed.
- No checker finding required a change to the full record after re-derivation, so there was no
  repair phase.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions` (pair-checker `semantic-review-required`): the 4
  collections and 34 files project to 38 core distributions with matching ids, names, md5s,
  formats and media types. Collection-level `file_count` is not a shared slot and does not reach
  the core. **reviewed: consistent**
- Counts against the entries beneath them: `file_count` is 6, 21, 8 and 10 against 6, 10, 8 and
  10 listed File entries. F3TD5R states 21 files but its captured page lists only "1 to 10 of 21
  Files"; the collection's description says the other 11 are not listed in the source. No
  `total_file_count`, `total_size_bytes` or `bytes` is recorded, because the sources give only
  rounded display sizes. **reviewed: consistent**
- `dialect` and `is_tabular` against the files: no file carries a dialect and the files are ZIP,
  JSON and HTML, so neither slot is populated in either record. **reviewed: consistent**
- Historical and current releases: B35XWX and F3TD5R (tier 5, historical) and K7TGEM (tier 1) are
  marked as archived releases on their `resources` entries. HIGT4C is the latest release, and
  top-level current-state slots draw on it. Release-specific details such as versions, dates, file
  lists and embargo notes stay on the release entry. **reviewed: consistent**
- The external resource for the Nature article is a related publication, not a use of the
  referent's data. **reviewed: consistent**

## Files changed

- Created: full record, core record, coverage receipt, this report (all under this run's label).
- Scratch copies (not outputs): `.temp/CM4AI_d4d_phase1_snapshot.yaml` and
  `.temp/CM4AI_coverage_receipt_phase1_snapshot.yaml` (Phase 1 state before the Phase 3
  correction), plus command logs in `.temp/` (gitignored).

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <abs>/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <abs>/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record <full> --record <core> --strict
grounding.check_run(<full>, <core>, <bundle>, uriorcurie_slots())
```

## Final results

- Full record: schema valid, term valid; 41 top-level slots populated.
- Core record: schema valid, term valid; 43 top-level slots populated (including the per-record
  `conforms_to_class` and `conforms_to_schema`, and `distributions`).
- Receipt check: strict pass, 28/28 chunks, 359/359 snippets, 542/542 slots.
- Pair consistency: PASS, with 1 semantic warning that was reviewed. Grounding: 0 absent. Scope: in scope.
- Phase 4 reconciliation: completed.
