# CHORUS reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`
- Mode: four-phase project agent, generic-v9 prompt; arm BASELINE (input documents only)
- Agent runtime: Claude Code (release); provider Anthropic; model claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). This workflow does not observe the native runtime's sampling settings; nothing here establishes an effective temperature or deterministic generation.
- Source bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (md5 `9b2ef4b65d67957f79362266cab0bc7a`, 1698 lines, 8 chunks)
- Chunk manifest: `data/preprocessed/chunks/CHORUS_chunks.yaml` (`bundle chunk --check --strict`: current, 8 canonical chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_coverage_receipt.yaml`

## Referent

The declared scope (`download scope --project CHORUS`) names the referent as the CHoRUS dataset, <https://chorus4ai.org/>, and declares no related-but-distinct dataset. Both records describe that one referent: the dataset the CHoRUS data generation project produces, identified by the project site, which the bundle states as a source URL. No dataset DOI appears in the bundle, so the records carry none. The record `id` and `page` are the project site URL; parts that the schema forces an `id` on (one person, one software tool) are labeled as fragments on that id.

The bundle's four sources are ranked by the manifest: project website (tier 2), NIH RePORTER project page and Cohort 2 webinar (tier 4), chorus-ai GitHub organization overview (tier 5, historical documentation). No genuine source conflict was found, so the ranking did not have to decide any value (see Phase 3).

## Phase 1 - full generation

- All 8 chunks were read with the file-reading tool in manifest order, and each chunk's receipt entry was written before the next chunk was read.
- After the record was composed, the receipt's slot addresses were corrected to the paths the record actually uses (the entries written during reading used provisional paths). One further address correction followed the first strict check: the scalar list `conforms_to_standard` is addressed as the slot, not by index.
- Strict receipt check before Phase 2: `chunks 8/8 reviewed · snippets 135/135 verified (2 bearing on no token of their value) · slots 101/101 with a receipt (3 exempt)`, exit 0.
- Schema validation and term validation of the full record: passed.

## Phase 2 - core derivation

Derived with `derive core`; no model judgment. The command printed (final Phase 4 re-derivation shown; the Phase 2 run printed the same facts with the pre-audit md5 `e2349b882a61268b0ecd3da47812fcf4`):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_d4d.yaml", "md5": "96771f27457a9b9f126428ff6a6b621e"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

## Phase 3 - source and provenance audit

### Provenance boundary

- Factual inputs read: the declared bundle, the chunk manifest, and the source manifest (scope, naming and ranking declarations). Structural inputs read: the full schema file and `src/data_sheets_schema/receipts.py` (for the receipt shape and normalization).
- No prior generated D4D record, evaluation, or reconciliation report was read, from any arm, label or date. Nothing under `data/d4d_concatenated/` was opened other than this run's own three outputs and receipt.
- Deviations from the playbook's tool discipline, recorded as they happened: (1) the executable playbook view was first redirected to `.temp/playbook_view.txt` to compare it with the source playbook, and that file was deleted immediately afterwards; it held playbook text only. (2) The schema's class and slot listings were read with inline `awk` over the schema file, and one inline Python call to the receipts module listed the single unreceipted slot path; neither wrote a file.

### Source findings

Each row is one recorded audit entry against the full record; all were resolved in the full record, with receipts added to the existing chunk entries.

| ID | Severity | Slot | Finding | Source (chunk) | Resolution |
|---|---|---|---|---|---|
| F1 | low | `description` | The sentence read as though the dataset, not the project, were organized around three pillars. | NIH project page (c002): "Through 3 pillars, the CHoRUS data generation project will addresses multiple challenges" | Reworded so the pillars belong to the project. |
| F2 | low | `instances[8].description` | Clinical notes listed as a data type without the slide's storage qualifier. | Webinar (c003): "Clinical notes – stored locally except tokens" | Qualifier added. |
| F3 | medium | `instances[9].description` | Imaging listed as a data type without its availability status. | Webinar (c003): "Imaging – currently 1000 images available with de-id in process for larger cohort" | Status added. |
| F4 | medium | `instances[11].description` | Waveform EEG listed as a data type without its in-process status. | Webinar (c003): "EEG – extraction in process at this point" | Status added. |
| F5 | low | `collection_mechanisms[1].mechanism_details` | "Sites follow a process" and "sites provide regular status updates" were stronger than the source, which points data managers to the SOP page and says sites "have been asked" for updates; repository descriptions were not marked as descriptions. | GitHub overview (c007, c008) | Reworded to the source's reach. |
| F6 | low | `intended_uses[1].description` | The website's word "transnational" was carried unmarked in composed prose. | Website (c006) | Quoted and attributed to the website. |
| F7 | low | `source_caveats` | The caveat did not say that the website's 50,000 and 1.6 Billion are round display figures, nor that the abstract's "publicly available" is a goal while the webinar describes current access as controlled. | Website (c006), NIH project page (c002), webinar (c003) | Both statements added. |
| B1 | low | `description` | Source-supported omission: the ethics statements (planned community-facing ethics focus groups; the consortium's evaluation of community perspectives). | NIH project page (c002), website (c006) | Back-ported into the description, the plan marked as a plan. |
| B2 | low | `description` | Source-supported omission: the abstract's planned data content, including social determinants of health. | NIH project page (c002) | Back-ported into the description as planned content. |

Totals, counted from the nine rows above: 9 entries, of which 2 medium (F3, F4) and 7 low (F1, F2, F5, F6, F7, B1, B2); 0 high. Seven are corrections to existing values and two are back-ported omissions. All 9 are resolved; none is open.

### Source conflicts

None genuine. The webinar reports "over 45K unique admissions" as of August 2025 and the website's current-release snapshot reports 50,000 patient admissions; a bound and a later round figure are compatible, so both are retained with their scope and the manifest ranking was not applied. The website's 14 data contributing hospitals and 20 institutions agree with the GitHub overview's 20 academic centers, of which 14 contribute data.

### Scope and status review

- Plans are stated as plans. The NIH project abstract and the GitHub overview are written in the future tense; values from them (`splits`, `sampling_strategies`, `labeling_strategies`, `participant_privacy`, parts of `preprocessing_strategies[0]`, `intended_uses[0]`) carry "planned" in their own value.
- No presence boolean was set. `is_deidentified` carries only the webinar's statement that imaging de-identification is in process; tokenization of clinical notes is recorded as preprocessing, not as de-identification.
- The webinar's CHoRUS Dataset table is extracted without its row and column alignment. The record lists the data types and, at dataset level, the standards the table names; it does not assign a standard, an access control or a metadata status to an individual data type. `conforms_to_standard` holds the three named standards that have an enumeration value (OMOP, DICOM, WFDB); OHNLP and EDF+ and Persyst are named in `source_caveats` only.
- The training-program passages of the webinar are about the AIM-AHEAD training program, not the dataset. Only its statements about the dataset and about access to it were used, scoped in the value to program participants.
- `principal_investigator` is populated only for the person the NIH project page designates with that title. The other five people on the webinar's "Bridge2AI CHoRUS Leadership Team" slide are recorded as creators with the role the slide states.
- The website's "Contact Us" entry is recorded under `maintainers` with the role the website states (Program Manager); the `role` enumeration is left empty.

### Continued omissions (absent in both the first and the final full record)

Left empty because the bundle does not support them: a dataset license (the GitHub overview's MIT statement concerns the GitHub project), a DOI, a version, release dates, keywords (the NIH page's "Preferred terms" line indexes the grant project record and includes terms unrelated to the dataset), data use permission categories, human-subjects and IRB statements, consent, at-risk populations, variables, file collections, and registry identifiers for any organization or person.

## Phase 4 - re-derivation, checks, report

### Claims

No slots were removed.

### Semantic review

- Pair checker `semantic-review-required` warnings: none emitted (the full record has no `file_collections`, so the core has no `distributions`) - reviewed: consistent.
- `total_file_count` and `total_size_bytes` against the entries beneath them: neither is populated and no file or collection entry exists; the website's 23 Tb is waveform data only and is kept in the description, not as a total - reviewed: consistent.
- `dialect` and `is_tabular` against the files: neither is populated and the record names no file - reviewed: consistent.
- Historical versus current release: the record separates the website's "Current Released Dataset" from its "Anticipated Final Dataset", dates the webinar's state to August and September 2025, and marks the GitHub overview as historical documentation captured 11/14/25; instance counts come from the current-release snapshot only - reviewed: consistent.
- Counts against their units: 50,000 patient admissions, 1.6 Billion rows of EHR OMOP data and 7,642 admissions with radiology data each sit on an instance entry naming that unit - reviewed: consistent.

### Checks on the final pair

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Core schema validation (`CoreDataset`) | No issues found |
| Full term validation | Validation passed |
| Core term validation | Validation passed |
| Pair consistency | PASS: 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class`, `conforms_to_schema` |
| Identifier grounding | grounded 0, minted_fragment 0, absent 0 |
| Strict receipt check (after Phase 3) | chunks 8/8 reviewed, snippets 143/143 verified (2 bearing on no token of their value), slots 101/101 with a receipt (3 exempt), exit 0 |
| Scope check on the pair | none is about a dataset its project declares distinct |
| Prompt pin (`api prompts check`) | 28 prompt files, 0 not at their pin; `d4d_generic_arm_prompt_v9.md` canonical |

The two snippets bearing on no token of their value were reviewed: "Controlled access" under `regulatory_restrictions.confidentiality_level` (value `restricted`, whose enumeration description is restricted access requiring approval or registration) and "This project is funded by the NIH under award number OT2OD032701" under `funders[0].grantor` (a second snippet at that path spells the name out).

No checker finding required a change, so no repair phase ran.

### Slot counts (informational)

- Full record: 30 top-level slots; 104 populated leaf slots as the receipt checker counts them; 344 lines.
- Core record: 30 top-level slots (28 shared with the full record plus the per-record `conforms_to_class` and `conforms_to_schema`); 267 lines. The full-only slots `splits` and `participant_privacy` are not part of the core schema's projection.

### Files changed

- Written: the full record, the core record (derived twice, never hand-edited), the coverage receipt, and this report.
- No other file in the repository was changed.

### Commands

```bash
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CHORUS
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1 --project CHORUS --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "... data_sheets_schema.grounding.check_run ..."   # the playbook's identifier grounding program
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS --check --record <full> --record <core> --strict
.venv/bin/python -m data_sheets_schema.cli api prompts check
```

## Final result

Both records validate against their schemas and term checks, the pair checker passes, the receipt check passes its strict floors, and the scope check reports the pair in scope. Reconciliation outcome: completed with 9 audit entries resolved in the full record, no slot removed, no repair phase.
