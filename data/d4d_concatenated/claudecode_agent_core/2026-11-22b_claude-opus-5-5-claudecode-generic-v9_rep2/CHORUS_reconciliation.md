# CHoRUS reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2

- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt; arm BASELINE (input documents only)
- Bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (md5 9b2ef4b65d67957f79362266cab0bc7a, 8 chunks)
- Chunk manifest: `data/preprocessed/chunks/CHORUS_chunks.yaml`; source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed; not recorded.

## Referent

The manifest scope declares the referent "CHoRUS dataset" with referent id
`https://chorus4ai.org/` and no related-but-distinct datasets. Both records use
`id: https://chorus4ai.org/` and describe the CHoRUS dataset produced by the
CHoRUS data generation project. No dataset DOI appears in the bundle. Labels
minted for parts of the dataset (the five `subsets` ids and the principal
investigator's person id) are fragments on that id.

Source ranking used (from `download priority`): project_documentation (tier 2)
> nih_reporter_project, cohort_2_webinar (tier 4) > github_organization_overview
(tier 5, historical, captured 2025-11-14). No genuine conflict needed the ranking
to decide (see Phase 3).

## Phase 1 — full generation

- Chunk check: `bundle chunk ... --check --strict` reported current (8 canonical chunks).
- All 8 chunks were read with the file-reading tool in manifest order, and
  each chunk's receipt entry was written before the next chunk was read
  (c001 nothing_relevant; c002–c008 extracted).
- Full record: schema validation reported no issues, and term validation passed.
- Strict receipt check before Phase 2: 8/8 chunks reviewed, 134/134 snippets
  verified, exit 0.

## Phase 2 — core derivation

`derive core` printed the following facts (Phase 2 run; full md5 at that point 11c6f373e4c1a07724cf7c9afa4f558f):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml", "md5": "11c6f373e4c1a07724cf7c9afa4f558f"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against `CoreDataset`.

## Phase 3 — source and provenance audit

Provenance: this run read only the declared bundle (by chunk), the source and
chunk manifests (via the registered commands), the two schema files, the
playbook, the provenance guard, the uniform rules and `d4d-agent.md`. No prior
D4D record, evaluation or reconciliation report was opened. The only directory
listing of the output directories showed another project's files under this
label; none of them were opened.

Conflict review (uniform-rules compatibility check):

- Current admissions: the website (tier 2) gives 50,000 patient admissions
  (current released dataset), and the webinar (tier 4) gives "over 45K unique
  admissions" as of August 2025. These figures are compatible (a lower bound at
  an earlier stated date), so this is not a conflict. Both are recorded, and
  `instances[0].counts` is 50000.
- Targets: the website's anticipated 100,000 patient admissions and the grant's
  "more than 100,000 critically ill patients" use different units and are both
  targets. Neither is treated as current, and they are not compared.
- Imaging: the webinar's "1000 images available" and the website's "7,642
  admissions with radiology data" use different units and are not compared.
- License: the GitHub overview's MIT License statement covers the GitHub
  project. No source states a dataset license, so `license` stays empty and the
  point is recorded in `source_caveats`.

Findings (recorded entries; all concern the full record):

| # | Severity | Slot | Finding | Source (chunk) | Action |
|---|---|---|---|---|---|
| 1 | moderate | `description` | The phrase "Data types … include … waveform EEG" read as a present-data inventory, but the webinar states that EEG extraction was in process and that imaging de-identification was in process. | cohort_2_webinar (c003) | Rephrased as the webinar table's listing, with both in-process statuses stated |
| 2 | moderate | `subsets[2].description` | The website's "7,642 admissions with radiology data" was attached to the imaging subset, which treats radiology data as the same thing as the PACS imaging row. The sources do not establish that mapping. | project_documentation (c006) | Removed from the subset; the figure stays in top-level `description` as the website states it |
| 3 | minor | `participant_privacy[0].name` | The name read as an applied privacy operation, but the grant states a plan and the webinar states an operation in process. | nih_reporter_project (c002), cohort_2_webinar (c003) | Renamed to state planned or in-process status |
| 4 | minor | `data_governance.access_review_process` | The ".edu" email requirement comes from the training program's eligibility section, and that scope was missing. | cohort_2_webinar (c005) | Qualified as applying to program participants |
| 5 | minor | `license_and_use_terms.license_terms` | "All participants" refers to training program participants, and that scope was missing. | cohort_2_webinar (c003–c004) | Qualified |
| 6 | minor | `description` (omission) | The grant's plan for contextual factors such as geographic distance to the nearest hospital was omitted. | nih_reporter_project (c002) | Back-ported as a plan, with its receipt |

Totals, counted from the six rows above: 6 findings (2 moderate, 4 minor), all
corrected in the full record. After the corrections, the receipt entries were
edited in place: the c006 snippet for `subsets[2].description` was removed, and
snippets were added to c002 and c003 for `description`. The full record passed
schema validation, term validation and the strict receipt check again (8/8
chunks, 140/140 snippets verified).

Other audit notes (no change made):

- 12 of 96 receiptable leaves have no receipt at their own path. These are
  composed entry labels (for example the `subsets[*].name` values, `instances[0].name`,
  `instances[0].instance_type` and `distribution_formats[0].name`) whose content
  is receipted at the sibling `description` or details path. The checker reports
  them as diagnostics, not gated failures.
- The grant abstract (fiscal year 2022) and the GitHub overview (captured
  2025-11-14) describe plans with "will". Every value taken from them is stated
  as a plan or attributed with its date.
- `creators` lists the six people the webinar names as the "Bridge2AI CHoRUS
  Leadership Team", each as a separate entry with an affiliation. Only Eric S.
  Rosenthal is given a `principal_investigator`, because NIH RePORTER designates
  him with that title. No ORCID is stated, so his person id is a fragment on the
  record id.
- The website contact email domain "mgh.havard.edu" is reproduced as written
  and noted in `source_caveats`.

## Phase 4 — re-derivation, checks, report

- Re-derived the core with `--phase4-complete`; the core validated. Full md5
  a77bdfef12c6375a1d6a48b135543090; core md5 cb43beb5f3e36a5cee21e1e45b0bd74e.
- Pair checker result: `PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`. No errors and no warnings.
- Grounding check: `{'grounded': 0, 'minted_fragment': 0, 'absent': 0}`. No absent identifiers.
- Scope check (`download scope --check --strict` on both records): "none is
  about a dataset its project declares distinct".
- Schema and term validation passed for both records.
- Full-only slots not carried into the core (not declared on CoreDataset):
  `subsets`, `splits` and `participant_privacy`. Core-only slots written by
  derivation: `conforms_to_class` and `conforms_to_schema`.
- Header note: the launch instruction's CORE HEADER BLOCK gives an absolute
  `# Schema:` path. `derive core` writes the repo-relative path to the same
  core schema file (`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`).
  The core is not edited by hand, so the derived spelling stands.
- No repair phase: no checker reported a finding that required a change.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions`: the pair checker emitted no `semantic-review-required` warning. Neither record carries `file_collections` or `distributions` (the bundle names no files). **reviewed: consistent**
- `total_file_count` / `total_size_bytes` against the entries beneath them: both are absent in both records, and no file inventory exists. The size figure "23 Tb waveform data" stays in prose and is not used as `total_size_bytes`. **reviewed: consistent**
- `dialect` / `is_tabular` against the files: both are absent in both records, and no files are described. **reviewed: consistent**
- Historical vs current release: the website's current released dataset (50,000 admissions), its anticipated final dataset (100,000), the August 2025 webinar status, the 2025-11-14 GitHub capture and the 2022 grant plans are each stated with their scope. The description's data-type inventory was corrected (Finding 1). **reviewed: corrected** (description rephrased to the table listing with in-process statuses)
- Counts against their units: `instances[0].counts` 50000 is website patient admissions, compatible with the webinar's "over 45K unique admissions". The 1.6 billion figure counts rows of EHR OMOP data and the 7,642 figure counts admissions with radiology data, and both keep their units. **reviewed: corrected** (the 7,642 figure was detached from the imaging subset, Finding 2)

## Files changed

- Full record (written in Phase 1, corrected in Phase 3)
- Coverage receipt (written in Phase 1, edited in place in Phase 3)
- Core record (derived in Phase 2, re-derived in Phase 4)
- This report
- Intermediate snapshot: `.temp/CHORUS_d4d_phase1_snapshot.yaml` (gitignored scratch, taken during Phase 3)

## Commands

- `.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict`
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS`
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CHORUS`
- `.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <full schema> -C Dataset <full>` (Phase 1, Phase 3 and Phase 4)
- `.venv/bin/linkml-term-validator validate-data <full> --schema <full schema> --target-class Dataset`
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2 --project CHORUS --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --strict`
- `.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>` (Phase 2), then the same with `--phase4-complete` (Phase 4)
- `.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>`
- grounding `check_run` (playbook Phase 4 step 2)
- `.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <core schema> -C CoreDataset <core>`; `.venv/bin/linkml-term-validator validate-data <core> --schema <core schema> --target-class CoreDataset`
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS --check --record <full> --record <core> --strict`

## Final results

- Full record: 28 top-level slots; schema and term validation passed.
- Core record: 27 top-level slots; schema and term validation passed.
- Pair check: PASS. Grounding: 0 absent. Scope: in scope. Receipt check (strict): pass.
- Reconciliation outcome: 6 Phase 3 findings (2 moderate, 4 minor), all corrected in the full record; the core was re-derived; Phase 4 checkers found nothing; there was no repair phase.
