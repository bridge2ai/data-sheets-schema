# CM4AI reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2

- Runtime: Claude Code; provider Anthropic; model claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt (one agent context ran all four phases)
- Arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 50037fc631eafda807e19f83f6579818, 7,866 lines, 28 chunks)
- Chunk manifest: `data/preprocessed/chunks/CM4AI_chunks.yaml` (strict check: current, 28 canonical chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime)

## Referent

Declared scope (`download scope --project CM4AI`): referent "CM4AI (Cell Maps for
Artificial Intelligence) dataset", referent id `https://cm4ai.org/`; no
related-but-distinct dataset is declared. The manifest's referent note states that
the four Dataverse releases in the bundle (B35XWX, F3TD5R, K7TGEM, HIGT4C) are
releases of this dataset.

Choice held in both records: the referent is the CM4AI dataset as a series of
quarterly releases. Its own id is `https://cm4ai.org/`. The four captured releases
are recorded as `resources` entries identified by their DOIs. Series-level slots
that describe the current state (governance, limitations, intended uses,
prohibited use, biases, creators, keywords, license) follow the current release,
June 2026 (doi:10.18130/V3/HIGT4C). The May 2024 preprint's statements are
qualified as the project's state at that time.

The Nature article in the bundle (U2OS cell map, chunks c002–c009) is not used.
No CM4AI release page or project page links it to this dataset, and the article's
data are deposited in other repositories (NDEx, MassIVE, ProteomeXchange, HPA).
Its chunks are receipted `nothing_relevant` with that reason.

## Phase 1 — full generation

- Every chunk was read with the file-reading tool in manifest order, and each
  chunk's receipt entry was written before the next chunk was read.
- Receipt corrections made before Phase 2, within the Phase 1 correction loop,
  using chunks already read:
  - c018: the March 2025 file receipts were re-addressed from four per-folder
    file collections to one per-release collection.
  - c002 and c008: changed from provisional `existing_uses` and
    `external_resources` receipts for the Nature article to `nothing_relevant`.
  - c012: the funding receipts drawn from the preprint's "This work was funded
    by" passage were withdrawn. That passage's subject is the article's work, and
    the release records state the dataset's own award.
  - c014: the principal-investigator and intended-use addresses were moved to
    their final indices (`creators[46]`, `intended_uses[4]`).
  - Receipts were added for release dates, data collectors, copyright and
    conforms_to.
- The first strict receipt check passed (28/28 chunks, 307/307 snippets) but left
  5 receiptable slots without a receipt. Four were collection `name` labels I had
  composed with no source, so I removed them from the full record before Phase 2.
  The fifth, the F3TD5R collection description, was receipted. The re-check
  showed 519/519.
- Schema validation (`Dataset`) and term validation passed on the Phase 1 file.

## Phase 2 — core derivation (`derive_core`)

`derive core` ran on the validated Phase 1 file and wrote a core that validated.
The command's JSON from the final (Phase 4) derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml", "md5": "ab7765b6ae45e8f16cf4916786ad7e2b"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

Header deviation: the launch instruction's core header block gives the core
schema as the absolute path
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/fast-d4d-20261121-rep2/src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`.
`derive core` writes the repository-relative form
`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`. Both name the
same file in this checkout. The core is never edited by hand, so the derived
line stands. Every other core header line matches the instruction, including
`# Sources:` and `# Phase 4 reconciliation: completed`.

## Phase 3 — source and provenance audit (full record)

Provenance: the factual inputs read were the declared bundle (all 28 chunks), the
source manifest's CM4AI scope, naming and source entries, and the schemas. I did
not open any prior D4D record, evaluation, or report from any run, label or
project. The run's output directories contain other projects' files from the same
label; I listed their names when checking the directory and opened none.

Source ranking used: june_2026_dataverse_release and october_2025_dataverse_release
(tier 1) > project_documentation, data_release_documentation, dataset_license
(tier 2) > nature_publication, biorxiv_preprint (tier 3) > nih_reporter_project
(tier 4) > march_2025 and june_2025 releases (tier 5).

Recorded findings (3; computed from the entries below: 1 moderate, 2 minor):

| # | Slot | Severity | Finding | Action |
|---|---|---|---|---|
| F1 | `addressing_gaps[0]` | moderate | The value said the project "addresses this by generating maps". The RePORTER passage (c014) is a plan ("project will launch … creating a library of large-scale maps"). | Rewritten in the source's future tense; receipt added from c014. |
| F2 | `subpopulations[0]` | minor | The value joined the data-releases page's "TNBC cells" (c016) to MDA-MB-468 without stating the basis. | `source_caveats` added naming the preprint (c010) and release pages as the basis. |
| F3 | `conforms_to` | minor | RO-Crate packaging is stated by the 2024 preprint and the March 2025 release. The June 2026 release page does not state a packaging format. | Basis stated in top-level `source_caveats`. |

Checks with no finding:
- Conflict: the data-releases page shows "Released on: June 17, 2025" for HIGT4C
  (tier 2). Dataverse gives Publication Date 2026-06-17 (tier 1). Resolved by
  ranking to the Dataverse date, and recorded in `resources[3].source_caveats`.
- Version labels: page headers (1.4, 2.1, 2.1, 2.0) and citations (V1, V2, V2,
  V2) are compatible. Both are recorded per release.
- IF image protein counts (563, 464, 523) describe different releases or
  summaries. They are kept unreconciled and named in `source_caveats`.
- Plans and statuses: "Data Access Committee will supervise", "will be added in
  future releases", "coming soon" members (AP-MS for TNBC, IF for iPSC) and "data
  are currently being QCed" are all stated as plans or statuses. The AP-MS
  "coming soon" item is kept beside the June 2026 release's AP-MS data with each
  source named.
- Privacy fields: `is_deidentified` carries only the release page's
  "De-identified Samples: Yes" and the preprint's statement. No method is claimed.
- `principal_investigator`: set only for Trey Ideker, whom NIH RePORTER designates
  "Principal investigator". "Point of Contact" is recorded as that role in prose.
- Person ids: ORCIDs come from the release author list. Three of them join a
  role-listed full name to an author entry (Jillian Parker, Vardit Ravitsky,
  Jean-Christophe Belisle-Pipon), and each join is stated in `source_caveats`.
- Identifiers: every ORCID, the ROR (`ROR:0153tk833`) and every DOI are taken
  from the bundle. Labels minted for file collections and files sit on the record
  id `https://cm4ai.org/`.

Files changed in Phase 3: the full record (F1–F3) and the coverage receipt (one
added `addressing_gaps[0]` snippet in c014). After the changes, schema and term
validation passed and the strict receipt check reported 28/28 chunks, 309/309
snippets and 519/519 slots.

## Phase 4 — re-derivation, checks, report

1. The core was re-derived with `--phase4-complete` (output above) and validated
   (`CoreDataset`: no issues; term validation passed).
2. Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources'];
   per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`.
   It emitted no `semantic-review-required` warning: the full record has no
   top-level `file_collections`, so the core has no top-level `distributions`.
3. Grounding: `{'grounded': 43, 'minted_fragment': 0, 'absent': 0}`, so no
   identifier is absent from the bundle.
4. Scope check (`--strict`): 2 records checked, and neither is about a dataset its
   project declares distinct.
5. No checker reported a finding that required a change, so no repair phase ran.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions`: the checker emitted no warning, because
  no top-level collection exists. Inside each projected resource, the core's
  `distributions` hold the collection plus one entry per listed file: B35XWX 7 =
  1+6, F3TD5R 11 = 1+10, K7TGEM 9 = 1+8, HIGT4C 11 = 1+10. Every file id and md5
  matches the full record. **reviewed: consistent**
- Counts against entries: `file_count` equals the listed files for B35XWX (6),
  K7TGEM (8) and HIGT4C (10). For F3TD5R, `file_count` is 21 but the captured
  page lists only the first 10, which the collection description states.
  `total_file_count` and `total_size_bytes` are not populated, because the
  sources give sizes only rounded in KB, MB or GB. **reviewed: consistent**
- `dialect` and `is_tabular`: neither is populated. The files are ZIP, JSON and
  HTML, and no source describes a tabular dialect. **reviewed: consistent**
- Historical vs current release: series-level slots follow the June 2026 release
  (doi:10.18130/V3/HIGT4C), which `version_access.latest_version_doi` names.
  March 2025, June 2025 and October 2025 appear only as `resources` entries, each
  marked superseded in its `source_caveats`. **reviewed: consistent**

## Commands

```
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
.venv/bin/python -m data_sheets_schema.cli agents playbook
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <abs>/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema <abs>/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
.venv/bin/python scripts/adhoc/list_unreceipted_slots.py --full <full> --receipt <receipt> --bundle <bundle> --chunk-manifest <chunk manifest>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s <abs>/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c "from data_sheets_schema.grounding import check_run …"   (grounding, Phase 4 step 2)
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record <full> --record <core> --strict
```

## Final results

- Full record: schema validation passed; term validation passed.
- Core record: schema validation passed; term validation passed.
- Receipts: 28/28 chunks reviewed, 309/309 snippets verified, 519/519 receiptable slots receipted.
- Pair: PASS. Grounding: 43 grounded, 0 absent. Scope: in scope.
- Reconciliation outcome: 3 Phase 3 findings, all corrected in the full record
  and carried into the re-derived core. No Phase 4 findings, so no repair phase.
