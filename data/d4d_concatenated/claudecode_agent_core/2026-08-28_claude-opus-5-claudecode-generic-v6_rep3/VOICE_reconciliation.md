# VOICE — Phase 3 / Phase 4 reconciliation

- **Version label:** 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3
- **Arm:** BASELINE (input documents only)
- **Condition:** generic-v6 (`src/download/prompts/d4d_generic_arm_prompt_v6.md`)
- **Mode:** four-phase project agent, Claude Code / Anthropic / claude-opus-5
- **Declared bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
  (md5 `dcd717170da6762569c0b4eeafc1c3d2`, 5,746 lines, 22 chunks)
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_d4d_core.yaml`
- **Receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The record is about the **adult Bridge2AI-Voice
dataset** distributed on PhysioNet, identified by `doi:10.13026/37yb-1t42` — the
DOI the source labels "DOI (latest version)" — and describing release **3.1.0**
(`doi:10.13026/8xbn-nq66`, published 1 May 2026). This matches the manifest's
`scope:` declaration for VOICE.

The **Bridge2AI-Voice Pediatric Dataset** (`doi:10.13026/mf9s-5r03`) is declared
related-but-distinct. Its documentation is legitimately in the bundle (chunks
c020, c021, source id `physionet_pediatric_1_1_0`), and it is expressed solely
through `related_datasets[0]` with `relationship_type: is_supplemented_by`. No
pediatric identifier appears in `resources`, `distribution_formats[].access_urls`
or `file_collections[].download_url`. `d4d download scope --check --project VOICE`
reports the record in scope and does not list it among the 32 records that place a
related-but-distinct dataset outside its declared slot.

## Phase 1 — coverage

The chunk manifest was current (`d4d bundle chunk --check --project VOICE` →
`current`) before reading. All 22 chunks were read with the file-reading tool in
manifest order and a receipt entry written per chunk before moving on:

| status | chunks |
|---|---|
| `extracted` | 20 (c002, c003, c005–c022) |
| `nothing_relevant` | 2 (c001 preamble/TOC; c004 PMC page furniture) |
| `redundant_with` / `duplicate_of` | 0 |

Final receipt check: **chunks 22/22 reviewed, snippets 276/276 verified, no
findings**. `slots 194/531 with a receipt (29 exempt)` is reported, not gated;
the unreceipted majority are sub-fields of objects whose attesting passage is
receipted at the parent or sibling level.

## Phase 2 — core derivation

`d4d derive core` was run on the validated Phase 1 file. No model judgement was
involved. The command reported:

```json
{"derived": true, "identity_slots": 79, "projected_slots": ["resources"],
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_d4d.yaml"},
 "distribution_slots": {"collection": ["compression","conforms_to","conforms_to_standard","description","id","name","notes","path","source_caveats"],
   "file": ["bytes","compression","conforms_to","conforms_to_standard","description","encoding","format","hash","id","md5","media_type","name","notes","path","sha256","source_caveats"]},
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The core was re-derived after every Phase 3 correction and finally with
`--phase4-complete`, which wrote the `# Phase 4 reconciliation: completed` header
line. The core was never edited by hand and `--sync-core` was never passed.

## Phase 3 — source and provenance audit

**Provenance.** Only the declared bundle, `data/preprocessed/source_manifest.yaml`,
the chunk manifest, the two LinkML schemas and the repository playbooks were read.
No prior full or core D4D record, from any arm, label or date, was opened, grepped
or consulted; nothing under `data/d4d_concatenated/` other than this run's own
output directories was read. The `d4d download scope --check` run prints excerpts
from other runs' records as part of its own report; those were not used as
evidence for any value.

**Source disagreements resolved by the manifest ranking.** `source_priority`
places data resources at tier 1, documentation/IRB/DUA at tier 2, publications and
white papers at tier 3 and the NIH project page at tier 4.

| Disagreement | Sources | Resolution |
|---|---|---|
| Frank Rudzicz's affiliation | project_documentation + irb_protocol (tier 2): University of Toronto; feasibility_publication (tier 3): Dalhousie University | Higher tier preferred; caveat on `creators[8].source_caveats` |
| Vardit Ravitsky's affiliation | project_documentation (tier 2) + audiomics_white_paper (tier 3): The Hastings Center; feasibility_publication (tier 3): University of Montreal | Higher tier preferred; caveat on `creators[14].source_caveats` |
| Spelling of Jennifer Siu / Sui | physionet_3_1_0 (tier 1): "Siu"; project_documentation (tier 2): "Sui" | Higher tier preferred; caveat on `creators[17].source_caveats` |
| Distribution platform | physionet_* (tier 1): PhysioNet, credentialed access; project_documentation healthsheet (tier 2): Health Data Nexus | Tier 1 preferred for the current release; the Health Data Nexus statements are retained only with explicit historical scope (`version_access`, `distribution_dates[0].description`, `maintainers[2]`) |

**Disagreement the ranking cannot decide.** The target collection size is given as
10,000 (project_documentation, tier 2 — "flagship … dataset of 10,000 voices" and
"Enrollment Count (Anticipated by 2027): 10,000") and as 30,000 (irb_protocol,
tier 2 — "Sample Size 30 000 participants"). The two sources share a tier, so the
ranking cannot decide and neither is selected: both are stated in
`subpopulations[2].distribution` with a `source_caveats` naming the conflict. The
audiomics white paper's "database of 30 000 human voices" is tier 3 and is noted
in the top-level `source_caveats` rather than preferred.

**Grant number variants.** The bundle spells the award as `OT2 OD032720`,
`1OT2OD032720-01`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3` and
`3Tf-OTOD03272001S2`. The core project number `OT2OD032720` is common to all;
only the two supplements a source states as a project number are recorded as
separate `Grant` entries, with `funders[0].source_caveats` naming the variants.

**Mis-scoped statements checked.** Statements written for the v2.0.0-era
healthsheet (English-only language option, semi-annual release cadence, Health Data
Nexus hosting, "no external data released in this v3.0.0 release") were kept only
where the record states their scope explicitly. The feasibility study reported in
`feasibility_publication` is a study *of the collection application*, not of the
dataset: its 47 participants, its single-site limitation, its USF IRB number
004890 and its statement that participants received no financial incentives were
not attributed to the dataset. The last of these is noted in
`participant_compensation[0].source_caveats` because it appears to contradict the
dataset's compensation schedule and does not.

**Corrections made to the full record in Phase 3** (all re-receipted; the core was
re-derived afterwards):

| # | Change | Reason |
|---|---|---|
| 1 | Removed `data_governance.access_decision_timeframe` and `data_governance.appeal_process` | Both opened "Not stated." — a value recording that information is absent has not answered the field. The substantive content they carried (agreement term, thirty-day termination notice) moved to the fields it answers |
| 2 | Added the agreement term and termination-notice clause to `license_and_use_terms.license_terms` | Destination for the content removed in (1) |
| 3 | Split `updates.frequency` | The observed PhysioNet release dates are evidence commentary, not the stated cadence; moved to `updates.source_caveats` |
| 4 | Removed `distribution_formats[0].media_type` and `[1].media_type` | `application/octet-stream` and `text/tab-separated-values` were inferred; the bundle states the format, not an IANA media type |
| 5 | Removed `external_resources[5].archival: false` and renamed the entry | The healthsheet answers "NA", not "no"; asserting `false` is inference |
| 6 | `creators[17].description` rewritten and a `source_caveats` added | Was "Investigator for the pediatric cohort", which over-read the evidence and leaned on the related dataset; the bundle supports "Lead investigator at the Hospital for Sick Children" |
| 7 | Added the FAIR-structure statement to `notes` | The evidence for it had no home in the record; `intended_uses` was the wrong field for a structural property |
| 8 | `word-colour Stroop` → `word-color Stroop`; `Temerty Centre` → `Temerty Center` | House style is American English, and both are names the sources spell that way — a proper noun keeps its source spelling |

**Omissions deliberately left.** `publisher` (`uriorcurie`) is omitted: the bundle
names PhysioNet and the MIT Laboratory for Computational Physiology in prose but
supplies no registry identifier for either, and supplying a ROR from model
knowledge would be an unsupported claim. `Person` objects are omitted throughout
(`Creator.principal_investigator`, `DataGovernance.committee_contact`,
`EthicalReview.contact_person`, `LicenseAndUseTerms.contact_person`): `Person.id`
is required, the bundle contains no ORCID for anyone, and a fragment on an
organization's identifier does not identify a person. People are therefore carried
as `Creator` entries with `name` and `affiliations`. `total_file_count`,
`total_size_bytes`, `compression`, `is_tabular`, `download_url`, `created_on`,
`created_by`, `was_derived_from`, `subsets`, `imputation_protocols`,
`annotation_analyses`, `use_repository`, `other_tasks` and
`data_protection_impacts` are omitted for want of evidence.

## Claims

No slots were removed.

Nothing was projected into the core and then deleted; the Phase 3 removals in the
table above were removals of values from the *full* record before derivation, not
removals of slots the core carried.

## Semantic review

| Review | Finding |
|---|---|
| `file_collections` ↔ `distributions` (checker's `semantic-review-required` warning) | 14 deterministic matches — 3 at collection level (`#features`, `#phenotype`, `#metadata`) and 11 at nested resource level (the nine feature Parquet files plus `static_features.tsv` and `audio_quality_metrics.tsv`); `unmatched core distributions=[]`. Each core distribution carries the same `id`, `name`, `path` and `description` as its full-record counterpart, and the descriptions remain accurate as distribution descriptions: they name the file, its dimensionality and its v3.1.0 record count. **reviewed: consistent** |
| `total_file_count` / `total_size_bytes` against the entries beneath them | Both omitted from the full record and therefore from the core. The bundle states per-feature record counts (numbers of *recordings* represented, not file counts) and no byte sizes anywhere, so no aggregate could be computed without inventing one. `file_collections[0]` enumerates 11 files but the bundle also says each has an accompanying JSON data dictionary, so 11 is not the collection's file count either; `file_count` is likewise omitted. Nothing to reconcile. **reviewed: consistent** |
| `dialect` / `is_tabular` against the files | Both absent. No `File` entry carries a `dialect`, so the derivation's conditional rule correctly emitted none in the core. `is_tabular` was deliberately not set: the release mixes tab-delimited phenotype tables with Parquet tensor files, and neither `true` nor `false` is supported for the dataset as a whole. **reviewed: consistent** |
| Historical release read as the current one | Checked every value whose evidence comes from the v2.0.0-era healthsheet or from the v1.1 / v3.0.0 PhysioNet pages. `instances[0].counts: 833` is stated by both v3.0.0 and v3.1.0 and is current. Per-feature record counts are taken from the v3.1.0 page only (29,278 / 32,522 / 28,640 / 31,855 / 31,872 / 29,289), not from the v3.0.0 page, which gives different figures for the same files. `version` and `doi` name 3.1.0. Health Data Nexus, the English-only language option, the v1.0 recording counts and the "no external data in v3.0.0" statement each carry explicit historical scope in the text that states them. The documentation's "~61,937 voice-derived recordings" for v3.0 is recorded as a `source_caveats` on `instances[1]` rather than as a current count. **reviewed: consistent** |
| Minted fragment identifiers against the v6 density rule | `grounding` reports 14 `minted_fragment` and 0 `absent`. All 14 hang off the record's own grounded DOI CURIE. The v6 rule asks that a fragment be minted only where another value must point at that part; here no *other* value points at these parts, but `FileCollection.id` and `File.id` are **required** by the schema, so the choice was whether to emit the objects at all, not whether to label them. Emitting them was judged right: the bundle documents each file individually with its own dimensionality and record count, the v2 rule requires one object per distinct entity rather than eleven files collapsed into one, and the core's `distributions` are built from exactly these entries. Recorded here as a judgement rather than left silent. **reviewed: consistent** |
| Canonical project label | The manifest's `naming:` block declares `Voice` as the canonical label for this project. Every occurrence of `Bridge2AI-Voice` / `Bridge2AI Voice` remaining in the records was checked against the three carve-outs. Those kept are proper nouns the sources state: the dataset's own name and title, `Bridge2AI-Voice Consortium`, `Bridge2AI-Voice App`, `Bridge2AI Voice Web app`, `Bridge2AI Voice Registered Access License` and `Registered Access Agreement`, `Bridge2AI Voice Data Acquisition` (the IRB protocol title), `Bridge2AI Voice REDCap`, and `Bridge2AI-Voice Pediatric Dataset`. Six labels that were **my own composed prose**, not source names, used the project name inconsistently and were rewritten to the canonical label in Phase 4 — see the repair below. **reviewed: corrected** |
| Identifier form (`uriorcurie` vs `uri` vs `string`) | `id`, `related_datasets` targets, `version_access.latest_version_doi` and all minted fragments use `doi:` CURIEs, not resolver URLs. `raw_sources[0].access_url`, `distribution_formats[].access_urls` and `extension_mechanism.contribution_url` are declared `uri` and carry URLs. The `doi` slot is declared `string` and carries the bare DOI `10.13026/8xbn-nq66`, neither prefixed nor resolved. URLs inside prose (`external_resources`, descriptions, the Synapse and PhysioNet links in `related_datasets[0].description`) are left exactly as the sources wrote them. **reviewed: consistent** |

## Phase 4 — deterministic checks

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full (`Dataset`) | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core (`CoreDataset`) | Validation passed |
| `d4d_pair_consistency` | PASS: 79 schema-identical slots; projected `resources`; per-record exempt `conforms_to_class`, `conforms_to_schema`. One `semantic-review-required` warning, reviewed above |
| `grounding.check_run` | `{'grounded': 1, 'minted_fragment': 14, 'absent': 0}` |
| `d4d receipts check --strict` | chunks 22/22 reviewed, snippets 276/276 verified, no findings |
| `d4d download scope --check --project VOICE` | Record in scope; not among the records placing a related-but-distinct dataset outside its declared slot |
| `d4d api prompts check --strict` | 13 prompt files, 0 not at their pin; `d4d_generic_arm_prompt_v6.md` canonical |

## Phase 4 — repair

The `form` check block written by `d4d provenance record` reported
`gc_label_variants: {"Bridge2AI-Voice": 15, "Bridge2AI Voice": 25}` — 40
occurrences of two spellings of the project name, against a declared canonical
label of `Voice`. Auditing them showed most are source-stated proper nouns and
exempt, but six were labels this record composed itself and therefore governed by
the rule:

| Slot | Before | After |
|---|---|---|
| `external_resources[3].name` | Bridge2AI-Voice documentation and dashboard | Voice documentation and dashboard |
| `external_resources[4].name` | Bridge2AI-Voice project pages | Voice project pages |
| `funders[0].grants[1].name` | Bridge2AI Voice data release supplement | Voice data release supplement |
| `data_governance.name` | Bridge2AI Voice data access governance | Voice data access governance |
| `funders[0].grants[0].description` | …the Bridge2AI Voice award. | …the Voice award. |
| `data_governance.accountable_organization.description` | …concerning the Bridge2AI Voice award. | …concerning the Voice award. |

Two further corrections of the same kind were made earlier in Phase 4, in the
`reconcile` loop rather than as repairs: `word-colour Stroop` → `word-color
Stroop` and `Temerty Centre` → `Temerty Center`. Both were British spellings this
record had introduced into names the sources spell the American way, so both the
house-style rule and its proper-noun carve-out pointed the same direction.

The core was re-derived from the repaired full record and every validation, the
pair checker, the grounding check and the receipts check were re-run; all pass.
This report was then rewritten so that it describes the bytes that exist, and the
provenance record re-written to hash them.

## Commands run

```bash
poetry run d4d bundle chunk --check --project VOICE
poetry run d4d download scope --project VOICE
poetry run d4d download priority --project VOICE
poetry run d4d api prompts check --strict
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 --project VOICE --strict
poetry run d4d derive core --full <full> --out <core>
poetry run d4d download scope --check --project VOICE
poetry run python -c "... data_sheets_schema.grounding.check_run ..."
poetry run d4d derive core --phase4-complete --full <full> --out <core>
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -c "... data_sheets_schema.report_claims.check_report ..."
poetry run d4d provenance record --project VOICE --method claudecode_agent --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 ...
poetry run d4d runs validate --project VOICE --method claudecode_agent --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3
poetry run d4d runs check --strict
```

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_d4d.yaml` (Phase 1, corrected in Phase 3 and Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_d4d_core.yaml` (derived, re-derived after every correction)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_coverage_receipt.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/VOICE_provenance.yaml`

No file outside these five was written.
