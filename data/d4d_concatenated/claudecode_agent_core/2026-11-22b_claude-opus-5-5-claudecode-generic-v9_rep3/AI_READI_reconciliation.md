# AI_READI reconciliation report: 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3

- Runtime: Claude Code; Provider: Anthropic; Model: claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt; Arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 1a58ad7be37d4b08ebd9d94e6ad173a3, 25 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`; chunk manifest: `data/preprocessed/chunks/AI_READI_chunks.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime)

## Referent

The declared scope names the referent as the AI-READI dataset, `https://doi.org/10.60775/fairhub.3`, with no related-but-distinct datasets; the manifest notes that fairhub.1 and fairhub.2 are earlier releases of the same dataset. Both records describe **version 3.0.0 of the AI-READI dataset on FAIRhub (DOI 10.60775/fairhub.3, published 2025-11-17), the publicly accessible release**, with `id: doi:10.60775/fairhub.3`. Versions 1.0.0 and 2.0.0 appear only as version history (`version_access`, `distribution_dates`). The controlled-access set is described by the sources as a separate set, so its contents (ZIP code, race/ethnicity, sex, genetic data, past health records, medications, accident reports) and its access governance are recorded only in `source_caveats`, not as contents of this release.

## Phase 1 — full generation (summary)

- Read the playbook, provenance guard, uniform rules and agent method; checked the chunk manifest (`bundle chunk --check --strict`: current, 25 canonical chunks); read scope (`download scope`).
- Read all 25 chunks in order with the file-reading tool and wrote each chunk's receipt entry before reading the next.
- Structure came from the repository's schema digest (`schema_digest.digest_text('Dataset', ...)`) and `SchemaView.induced_slot` lookups on the full schema.
- Phase 1 correction loop (receipt addresses only, before Phase 2):
  - creator indices were re-addressed once the rank-1 FAIRhub PI roster (chunks c020–c021) fixed the final order;
  - entries for absences (labeling, sensitive elements) were moved to `source_caveats`;
  - the biorepository limitation was dropped and `known_limitations` renumbered;
  - `raw_data_sources[0]` was split (ECG / MoCA);
  - one wrong address (`funders[0].notes` → `funders[0].description`) was fixed after the first strict check reported `slot_not_in_record`;
  - entry-level receipts were added for creator names, `instances[0]` and `license_and_use_terms.name`.
- Final Phase 1 strict receipt check: 25/25 chunks, 496/496 snippets, 548/548 slots, exit 0.

## Phase 2 — core derivation

`derive core` (no model). Printed derivation facts (final re-derivation, Phase 4):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml", "md5": "4e90d06ee75cb4979810b3e1fc897ce7"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The first derivation (Phase 2, from full md5 13bbe1061a6234109e5d1abd8b5096c6) validated against `CoreDataset`.

## Phase 3 — source and provenance audit

### Provenance

- Inputs read:
  - the declared bundle;
  - the source manifest, chunk manifest and scope;
  - the full and core schemas;
  - the playbook, provenance guard, uniform rules and agent method;
  - repository code for the schema digest and the receipt validator.
- No generated D4D record from any run, label or arm was opened, searched or listed. No `*_crate_d4d.yaml` was read, nor any evaluation or reconciliation report. Nothing under `data/d4d_concatenated/` was read except this run's own output paths.
- Every identifier in the record comes from the bundle, or is a fragment minted on the record's own id (`doi:10.60775/fairhub.3`).

### Source conflicts and how they were handled

- **De-identification method.** Nature Metabolism (rank 3): the public set is stripped of PHI via HIPAA Safe Harbor. FAIRhub structured metadata (rank 1): `NoDeIdentification`, because no identifiers were collected. The rank-1 value is used; both are kept in `is_deidentified.source_caveats`.
- **PI affiliations.**
  - Aaron Y. Lee: the FAIRhub study description (rank 1) gives Washington University in St. Louis; NIH RePORTER (rank 4) gives the FY2022 award organization as University of Washington.
  - Cecilia S. Lee: the FAIRhub study description (rank 1) gives Washington University in St. Louis; Nature Metabolism (2024) gives University of Washington.
  - In both cases the rank-1 value is used and the disagreement is caveated.
- **PI roster.** The FAIRhub study description lists 16 Study Principal Investigators. The Nature Metabolism consortium listing also names Edberg, Ferryman, Ishikawa and Nebeker. These are compatible observations from different dates, not a contradiction, so all 20 are recorded; the four Nature-only entries are caveated.
- **License name.** "AI-READI custom license v2.0" (FAIRhub metadata), "Health Data License" (FAIRhub landing page) and "AI-READI DATA LICENSE AGREEMENT (Version 2.0)" (license document) are treated as one license.
- **Permitted use.** The consent metadata and README say the public data are for T2D-related research only; the license grant covers research, commercial and non-commercial use. Both are recorded.
- **Collection start.** July 19, 2023 (FAIRhub, data collected) and July 18, 2023 (BMJ Open, enrollment began) refer to different events; both are kept.
- **Stale wording.** The v3 documentation and healthsheet carry wording from earlier versions ("pilot study phase", "first year of data collection"). This is caveated; the explicit v3.0.0 figures are used.
- **Planned figures are not current state.** Enrollment target (4,000 vs 4,600) and follow-up share (10% vs 4%) are recorded as plans in `source_caveats` only.
- **Absences.** No labels, no DPIA, no retention limit, no extension mechanism, no existing uses, no confidential data, no sensitive data in the public set. These are recorded in `source_caveats` only, not as entries (R14).

### Findings (entries)

| # | Severity | Slot(s) | Finding | Source / chunk | Repair |
|---|---|---|---|---|---|
| F1 | major | `collection_mechanisms[18]`; `raw_data_sources[5]`, `raw_data_sources[6]` | Driving/accident records and extracted medical records were recorded as this release's collection mechanism and raw data sources. The sources place this content in the controlled-access set (R6). | c007 Fig. 1; c023 IRB 5.1/5.5; c011 and c018 controlled-access lists | Entries removed; receipts moved to `source_caveats`; lists renumbered. |
| F2 | major | `data_governance.committee_name`, `data_governance.access_review_process` | The Data Access Committee and the DUA/approval sentences describe governance of the controlled-access set, not of the public referent (R6). | c004, c005, c011, c023 | `committee_name` removed; `access_review_process` limited to public access steps (c015, c019); controlled-access governance moved to `source_caveats`. |
| F3 | minor | `raw_data_sources[7]` (now `[5]`), `participant_compensation[0]` | IRB-protocol plans ("will be given an option", payment timing, not prorated) were stated in the present tense (R2). | c022, c023, c025 | Restated as what the IRB protocol states. |
| F4 | minor | `collection_mechanisms[10].description` | The Dexcom masking statement had no receipt. | c004 | Receipt added to the existing c004 entry. |
| F5 | minor | `version_access.version_details` | The README's "year 3 data" label was used without noting the healthsheet's "second year" framing. | c018, c019 | Both framings now stated. |

Finding totals, computed from the five entries above: **5 findings — 2 major (F1, F2), 3 minor (F3, F4, F5).**

After the repairs, the full record re-validated (schema: no issues; terms: passed), and the strict receipt check passed (25/25 chunks, 498/498 snippets, 543/543 slots).

## Phase 4 — re-derivation, checks, report

- The core was re-derived with `--phase4-complete`; it validates against `CoreDataset` (no issues; terms passed).
- Pair checker: PASS. 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class` and `conforms_to_schema` (exempt). One warning: `semantic-review-required` on `file_collections` ↔ `distributions`, with 28 deterministic matches (10 collection-level, 18 file-level) and no unmatched core distributions.
- Grounding: `{'grounded': 27, 'minted_fragment': 32, 'absent': 0}`.
- Scope check (`--strict`, both records): no record is about a dataset its project declares distinct.
- The core header was written by `derive core`. Its `# Schema:` line is the repository-relative core schema path, not the absolute path in the launch instruction's core header block. The core was not hand-edited, per the Phase 4 rule.

## Claims

| Slot | Action | Reason |
|---|---|---|
| `committee_name` | Removed | Phase 3 F2: the Data Access Committee governs the controlled-access set, not the public v3.0.0 referent; the statement is kept in top-level `source_caveats`. |

## Semantic review

- `file_collections` ↔ `distributions` (checker warning): 10 file collections and 18 File entries project to 28 core distributions. Ids, names, paths, descriptions, `conforms_to`/`conforms_to_standard`, and format/media type for the files match the full record. **reviewed: consistent**
- Counts and sizes against the entries beneath them (unprompted): the nine data-type collections sum to 356,334 files and 3,815,969,360,064 bytes. The stated totals are 356,343 files and 3,815,969,779,678 bytes. The 9-file difference equals the nine listed root metadata files; the 419,614-byte difference is not stated by any source. This is recorded as the record's own computation in `file_collections[9].source_caveats`. The core distributions' bytes sum to the same 3,815,969,360,064. **reviewed: consistent**
- `dialect` and `is_tabular` against the files (unprompted): no File carries a dialect, so the core has none. `is_tabular` is unset in both records because the data mix tabular, imaging and waveform files. **reviewed: consistent**
- Historical vs current release (unprompted):
  - The v2.0.0 figures (2.01 TB, 165,051 files, 1067 participants) appear only in `version_access.version_details`.
  - The v1.0.0 and v2.0.0 dates appear only as labeled `distribution_dates` entries.
  - All current-state slots carry the v3.0.0 values (2280 participants, 356,343 files, 3,815,969,779,678 bytes).
  - **reviewed: corrected.** Phase 3 F5 clarified the year labels; F1/F2 removed controlled-access content.
- Participant counts (unprompted): the split totals 1576 + 352 + 352 = 2280. The subpopulation totals each sum to 2280 (race/ethnicity 380 + 545 + 519 + 836; sex 951 + 1329; diabetes status 776 + 560 + 686 + 258). Version history 204 + 863 + 1213 = 2280. **reviewed: consistent**

## Files changed

- Written: the full record, the core record (derived twice), the coverage receipt and this report (all under this run's label).
- Phase 3 changes to the full record:
  - removed `collection_mechanisms[18]`, `raw_data_sources[5]`, `raw_data_sources[6]` and `data_governance.committee_name`;
  - revised `data_governance.access_review_process` and `.notes`, `raw_data_sources[5]` (formerly `[7]`), `participant_compensation[0]`, `version_access.version_details` and top-level `source_caveats`.
- Receipt edits:
  - affected entries re-addressed in place (c004, c005, c007, c011, c018, c023);
  - receipts added to the existing c004 and c015 entries.
- No other file was written by this run.

## Commands

- `bundle chunk --bundle … --chunk-manifest … --manifest … --check --strict` → current, 25 chunks.
- `download scope --manifest … --project AI_READI` → referent fairhub.3; no related datasets.
- `linkml validate -C Dataset <full>` → No issues found (after one YAML quoting fix in Phase 1); `linkml_term_validator validate-data <full>` → passed.
- `receipts check --method claudecode_agent --label … --project AI_READI --bundle … --chunk-manifest … --strict`:
  - Phase 1: first run exit 1 (one `slot_not_in_record`), then exit 0;
  - after Phase 3: exit 0.
- `derive core --full … --out …` (Phase 2), then `derive core --full … --out … --phase4-complete` (Phase 4).
- `linkml validate -C CoreDataset <core>` → No issues found; term validation → passed.
- `d4d_pair_consistency --full … --core …` → PASS with one `semantic-review-required` warning.
- Grounding `check_run` → 27 grounded, 32 minted, 0 absent.
- `download scope --check --record <full> --record <core> --strict` → pass.

## Final results

- Full record: valid (`Dataset`), 62 populated top-level slots.
- Core record: valid (`CoreDataset`), 54 populated top-level slots.
- Pair consistency: PASS. Receipts: strict pass. Grounding: 0 absent. Scope: pass.
- Phase 3 found 5 issues (2 major, 3 minor); all were corrected in the full record, and the core was re-derived.
