# CM4AI reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); provider Anthropic; model claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). This workflow does not observe the native runtime's sampling settings; nothing here establishes an effective temperature or deterministic generation.
- Source bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 `50037fc631eafda807e19f83f6579818`, 28 chunks under `data/preprocessed/chunks/CM4AI_chunks.yaml`)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_coverage_receipt.yaml`

## Referent

The declared scope names one referent, the CM4AI (Cell Maps for Artificial Intelligence) dataset at `https://cm4ai.org/`, and declares no related-but-distinct dataset. The scope note states that the Dataverse releases in the bundle are releases of this dataset, not separate datasets.

The record's referent is therefore the CM4AI dataset as a series of data releases. It carries `https://cm4ai.org/` as its id. The five releases the bundle identifies by DOI are recorded as component datasets under the resources slot, each with its own DOI as id: DXWOS5 (cited by the May 2024 preprint), B35XWX (March 2025), F3TD5R (June 2025), K7TGEM (October 2025) and HIGT4C (June 2026). Slots that describe the dataset's current state (intended and prohibited uses, limitations, biases, governance, human-subjects and de-identification statements, update and preservation plans, the author roster) are taken from the June 2026 release record, which the project website presents as the latest release. Earlier releases keep their own facts under their own resource entries. This choice is held in both records.

The Nature article in the bundle (chunks c002 to c009) reports a U2OS cell map and that study's own data deposits. Its text does not mention CM4AI or the CM4AI data releases. No value in the referent's own slots was taken from it. It appears once, as an entry under external resources, described by what the article itself states and by the award number its acknowledgements share with the CM4AI project.

## Phase 1 notes

- The bundle was read with the file-reading tool in manifest order, chunk c001 through c028, and a receipt entry was written after each chunk before the next was opened.
- The receipt entries written during the read carried provisional slot paths, because the record had not yet been drafted. After the record was written, the receipt was re-addressed to the record's final slot paths in one pass. Three chunk dispositions changed in that pass: c007 and c008 went from nothing-relevant to extracted (they receipt the Nature article's external-resources entry), and c011 went from extracted to nothing-relevant (the values first receipted from it, on the cell-map integration pipeline and the ethics plan, were not carried into the record; the pipeline produces computed cell maps, which the current release states it does not include).
- One receipt-address correction followed the first strict receipt check: the two copyright lists are receipted at the list path rather than at indexed entries. The check then reported every receiptable slot with a receipt.
- Before Phase 2 the file-path value was left out for the 17 files whose listed location is the file name alone, so that the value does not restate the file name. Files with a directory keep their path.
- Sizes are stated by the source in rounded units (for example 3.8 GB). They are quoted in each file's description and no byte count is derived from them.

## Phase 2 derivation facts

First derivation, from the validated Phase 1 full record:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml", "md5": "d26dfcfe2fbdc9530e696e5a2862ff1e"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

Re-derivation in Phase 4, from the audited full record (the shipped core):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml", "md5": "b7741a301056bbaefaba034bb9d98de3"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

Both derivations validated against `CoreDataset`.

## Phase 3 - Source and provenance audit

### Provenance boundary

- Files read for facts: the declared bundle and the source manifest only.
- Files read for structure and procedure: the full and core merged schemas (by search and targeted line ranges), the provenance guard, the playbook and its executable view, the uniform rules, the full-record method file, the chunk manifest, and the receipt validator's source to learn the receipt shape.
- No prior full or core D4D record, evaluation output, or reconciliation report from any run, label or date was opened, searched or consulted. Nothing under `data/d4d_concatenated/` was read other than this run's own three outputs and its receipt, and nothing under `data/ro-crate_packages/` was read.
- The same-run full record carries this run's version label, and the core header names it under `# Sources:`.

### Findings

Audit findings: 7 (1 major, 6 minor). Each was corrected in the full record; the core was then re-derived.

| # | Severity | Slot | Finding | Source | Correction |
|---|---|---|---|---|---|
| 1 | major | `maintainers` | The entry placed the person the Dataverse record calls its Point of Contact in a slot that asserts responsibility for maintaining the dataset. The source states a contact role, not a maintenance role. | c027: "Point of Contact ... Ideker Trey (University of California San Diego)" | The entry was taken out of the record. The contact role is stated as the source states it, in the top-level description. |
| 2 | minor | `ip_restrictions` | The two copyright statements come from the May 2024 preprint and carry its year; that scope was stated only in the evidence commentary. | c012: "Copyright © 2024 to these datasets is held by the Regents of the University of California" | A description naming the May 2024 preprint as the origin of the statements was added to the object. The March 2025 release's own 2025 statements stay on that release's resource entry. |
| 3 | minor | `external_resources` | Five entries carried evidence commentary (that the page gives no URL or accession) inside their description, and the Nature entry carried a negative statement about the article in its description. | c026 External Data Links; c002 to c008 | The commentary was moved to each entry's evidence-commentary field; the two embargoed entries gained a one-line description. |
| 4 | minor | `collection_mechanisms` | The name of the third mechanism said single-cell sequencing, which the release's file descriptions do not state for those files. | c023 file descriptions; c026: "CRISPRi perturbSeq data" | The name now reads "CRISPRi perturb-seq". |
| 5 | minor | `resources` | The license of the DXWOS5 release was spelled "CC-BY-NC-SA 4.0" while every other license value in the record reads "CC BY-NC-SA 4.0"; the preprint gives the license by its full name and its creativecommons.org by-nc-sa/4.0 URL, the same license. | c012; c017 | The value was written in the one form the record uses. |
| 6 | minor | `distribution_formats` | Omission: the record did not state, at the top level, the format in which the current release is distributed. | c026: "Archive (10)", "Public (10)", "The dataset is too large to download. Please select the files you need from the files table." | One entry was back-ported: format ZIP, media type application/zip, the access URL the release states, with its receipts in the c026 entry. |
| 7 | minor | `source_caveats` | The collaborator list in the description is the project website's; the March 2025 release record gives the same list without UT Austin. The two lists are compatible and the difference was not recorded. | c016; c018 | One sentence was added to the top-level evidence commentary. |

### Source disagreements and how they were handled

- **Release date of the June 2026 release.** The Dataverse record gives publication date 2026-06-17; the project website's data release page shows "Released on: June 17, 2025" for the same DOI. The Dataverse record is tier 1 and the website tier 2 in the manifest's ranking; the Dataverse date is stated and the disagreement is recorded on that resource entry.
- **Affiliation of one author (Sali A).** The June 2026 release record gives University of California San Diego; the May 2024 preprint lists University of California San Francisco. The release record ranks higher; its value is stated and the disagreement is recorded on that creator entry.
- **Number of proteins imaged.** 523 on the website, 563 in the March 2025 file descriptions, 464 in the June 2025 and October 2025 file descriptions. These describe different releases and moments, so they are not a conflict between comparable claims; each is kept with its scope.
- **AP-MS data.** The website marks AP-MS interactomes "coming soon"; the June 2026 release description lists AP-MS data for treated MDA-MB-468 cells. Different moments; both kept with their scope.
- **Data Creation Date.** All four release pages state 2025-02-27. The record carries that creation date only on the March 2025 release, the earliest of the four, and says so in its evidence commentary.

### Judgments worth a reviewer's attention

- **Principal investigator.** The NIH RePORTER record for the CM4AI data generation project designates "Principal investigator: IDEKER, TREY". The record places that designation on the creator entry for Ideker T and takes the ORCID from the release's author list, the email from the preprint's corresponding-author line, and the affiliation from the RePORTER organization line.
- **Identity joins for three named contacts.** Vardit Ravitsky, Jean-Christophe Belisle-Pipon and Jillian Parker are named in the release's governance section without ORCIDs. The record gives each the ORCID the same release's author list states for Ravitsky V, Bélisle-Pipon JC and Parker J. The Parker join rests on surname, initial and institution; it is flagged in that object's evidence commentary.
- **Affiliation stated only as an identifier.** For five authors the June 2026 release record gives the affiliation as `https://ror.org/0153tk833` with no name. The record writes it as `ROR:0153tk833` and attaches no name, although the three earlier release records give University of Virginia for the same five authors.
- **Funding stated only by the preprint.** Award 5U54HG012513-02 and the Frederick Thomas Fund of the University of Virginia are named in the preprint's acknowledgements and nowhere in the release records. Both are recorded with that limitation stated on the entry.
- **Project-wide figures.** The three instance counts (53,788 immunofluorescent images; 1,374 protein interactions; 11,739 genes targeted) are the project website's Data Insights figures. The website does not tie them to a release, and each entry says so.
- **June 2025 file inventory.** The release page reports 21 files and the captured page lists the first 10. The record lists those 10, states 21 as the release's file total, and gives no file count on the collection.
- **Enumerations left empty.** No passage classifies the limitations, the biases or the file collections, so limitation type, bias type and collection type are not populated.
- **Chunks judged to hold nothing for the record.** c003, c004 and c005 (results, methods and data availability of the Nature article's U2OS study) and c011 (the preprint's pipeline, teaming, workforce and ethics-planning sections) are marked nothing-relevant on the ground that their subject is not the released dataset. That is a judgment the receipt validator does not test.

## Phase 4 - Re-derivation, checks, report

### Checks run on the final bytes

| Check | Result |
|---|---|
| Full record schema validation (`Dataset`) | No issues found |
| Full record term validation | Validation passed |
| Core record schema validation (`CoreDataset`) | No issues found |
| Core record term validation | Validation passed |
| Pair consistency | PASS: 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class`, `conforms_to_schema` |
| Identifier grounding | 44 grounded, 0 minted fragment findings, 0 absent |
| Scope check (`--strict`) | 2 records checked; neither is about a dataset the project declares distinct |
| Receipt check (`--strict`) | chunks 28/28 reviewed; snippets 288/288 verified; slots 562/562 with a receipt (58 exempt) |
| Chunk manifest check (`--check --strict`) | current: 28 canonical chunks under the selected rule |

No checker reported a finding that required a change, so there was no repair phase and this report was not rewritten after one.

### Record shape (informational)

- Full record: 32 populated top-level slots, 1149 lines.
- Core record: 33 populated top-level slots, 865 lines. The core carries the two per-record slots that state its schema and class; the full record's data-subset slot has no counterpart in the core schema and is not projected.
- 47 creator entries in both records; 5 release resources in both; 34 file entries across 4 file collections in the full record, projected into the core's per-release distributions.

## Claims

| Slot | Action | Reason |
|---|---|---|
| `maintainers` | Removed | The source states a Point of Contact, not a maintenance role (finding 1); the slot is absent from both final records. |

## Semantic review

- `file_collections` and `distributions`: the pair checker emitted no semantic-review-required warning on this pair, because the full record has no top-level file collections; each release's collection sits under its own resource entry. The four nested collections and their 34 files were compared with the core's per-release distributions (7, 11, 9 and 11 entries: one per collection plus one per file). Ids, names, formats, media types, hashes and descriptions agree. reviewed: consistent
- Counts and sizes against the entries beneath them: March 2025 states 6 files and lists 6; October 2025 states 8 and lists 8; June 2026 states 10 and lists 10. June 2025 states 21 and lists 10, because the captured page shows the first 10 of 21; the collection carries no file count and its evidence commentary says so. No total size in bytes is populated at any level, because the source gives rounded sizes only. reviewed: consistent
- Dialect and tabular flag against the files: neither is populated in either record. The listed files are ZIP archives, JSON metadata files and HTML pages, and no passage describes a tabular layout or a format dialect. reviewed: consistent
- Historical versus current release: top-level current-state slots draw on the June 2026 release record; the March 2025, June 2025 and October 2025 releases and the release cited by the 2024 preprint hold their own versions, dates, descriptions and files under their own resource entries; statements from the May 2024 preprint are worded as that preprint's statements, in its tense. The audit found one place where a historical scope was carried only in evidence commentary (finding 2). reviewed: corrected, by adding a description that names the May 2024 preprint as the origin of the top-level copyright statements.

## Files changed

- Written: the full record, the core record (derived, never edited by hand), the coverage receipt and this report, all under this run's version label.
- Scratch: `.temp/playbook_view.md` and `.temp/playbook_view.err` hold the rendered executable playbook view read at the start of the run; they hold no dataset facts.
- No other file was created or modified.

## Commands

```bash
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CM4AI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml --core data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d.yaml --record data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml --strict
```

Also run, as inline programs with the same interpreter: the playbook's grounding check (`data_sheets_schema.grounding.check_run`) and report-claims check (`data_sheets_schema.report_claims.check_report`) on this pair; one call to `data_sheets_schema.receipts.block_for` to list which slots still lacked a receipt after the first strict check; and read-only searches of the schema files and the bundle. The schema validation, term validation and strict receipt check were each run again after every change to the full record or the receipt.

## Final results

- Both records validate against their schemas and pass term validation.
- The pair checker reports no errors on the re-derived pair.
- The core header carries `# Sources:` naming the same-run full record and `# Phase 4 reconciliation: completed`.
- The strict receipt check passes with every manifest chunk reviewed.
- The scope check reports the pair in scope.
- Reconciliation outcome: the core is the projection of the audited full record; seven audit findings were corrected in the full record during Phase 3; no repair phase was needed in Phase 4.
