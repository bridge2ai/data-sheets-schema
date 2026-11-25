# CM4AI reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); provider Anthropic; model claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). This workflow does not observe the native runtime's sampling settings, and nothing here should be read as establishing an effective temperature or deterministic generation.
- Source bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 `50037fc631eafda807e19f83f6579818`, 7866 lines, 28 chunks)
- Chunk manifest: `data/preprocessed/chunks/CM4AI_chunks.yaml` (`bundle chunk --check --strict`: current, 28 canonical chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_coverage_receipt.yaml`

## Referent

Declared scope (`download scope --project CM4AI`): the referent is "CM4AI (Cell Maps for Artificial Intelligence) dataset", <https://cm4ai.org/>, with no dataset declared related but distinct.

Choice held across both records: the record describes the CM4AI dataset as the project's series of data releases. Its `id` is `https://cm4ai.org/`. Each Dataverse release the bundle names is a component under `resources` (five entries: DOIs 10.18130/V3/DXWOS5, B35XWX, F3TD5R, K7TGEM, HIGT4C), and the files of the four captured releases are four entries under `file_collections`. The June 2026 Data Release (10.18130/V3/HIGT4C) is treated as the current state. Statements taken from earlier releases, from the 2024 project preprint or from the project website are attributed in the value or in `source_caveats`.

## Evidence boundary

- Factual inputs read: the declared bundle (all 28 chunks, each through the file-reading tool in manifest order, with its receipt entry written before the next chunk was opened), the chunk manifest, and the CM4AI entries of the source manifest (scope, naming, source ranking, source list).
- Structural inputs read: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset` and the classes it ranges over), and the receipts validator source for the receipt file's shape.
- No previously generated D4D record, evaluation or reconciliation report was read, opened or searched. The only generated YAML read is this run's own pair.
- The source manifest's curation notes were not used as dataset facts.

## Source ranking and disagreements

Ranking (`download priority --project CM4AI`): tier 1 `october_2025_dataverse_release`, `june_2026_dataverse_release`; tier 2 `project_documentation`, `data_release_documentation`, `dataset_license`; tier 3 `nature_publication`, `biorxiv_preprint`; tier 4 `nih_reporter_project`; tier 5 `march_2025_dataverse_release`, `june_2025_dataverse_release`. The manifest marks the October 2025 release as superseded by the June 2026 release.

| Subject | Sources | Outcome |
|---|---|---|
| Release date of the June 2026 Data Release | Data releases page (tier 2): "Released on: June 17, 2025". Dataverse citation metadata (tier 1): Publication Date 2026-06-17. | Genuine conflict (same release, same event). The Dataverse date is recorded (`resources[4].issued`, `distribution_dates[0].release_dates`); the disagreement is stated in the top-level `source_caveats`. |
| End of the project | Dataverse Maintenance Plan (tier 1): "through the end of the project in November 2026". NIH RePORTER (tier 4): project end 2026-08-31 for project 3OT2OD032742-01S2. | Comparability uncertain (project versus one award record). Both kept where stated; noted in `source_caveats`. Not resolved. |
| Proteins imaged by IF | March 2025 release: 563 proteins per condition. June 2025 (revised) and October 2025 releases: 464 proteins. Data releases page: IF images for 523 proteins. | Different releases and an undated page; not a conflict. Each figure is kept in the entry of the release or page that states it. |
| AP-MS availability | Data releases page: AP-MS interactomes "coming soon". June 2026 release: AP-MS data included. | The page is undated; the release is the higher-ranked source. The release's statement is recorded as the current state and the page's wording is kept, marked, in `subsets[1]` and `source_caveats`. |
| Collaborating institutions | Data releases page lists UT Austin; the March 2025 release description does not. | Lists stated at different times; the page's list is quoted in `description` as the page's statement. No institution list is used to populate `creators`. |

## Unused source

Chunks c002 to c009 are a Nature article on a multimodal cell map of U2OS cells. No passage in the bundle states how that study's data relate to the CM4AI data releases, and U2OS is not among the cell lines of any captured release, so none of the article's dataset facts are in the record and the article is not listed as a resource. One value is taken from c002: the ORCID printed beside the author name "Trey Ideker", which is a fact about a person and identifies the principal investigator.

## Phase 1 - full record

- Schema validation: `No issues found`. Term validation: `Validation passed`.
- Receipt check before Phase 2 (`receipts check ... --strict`): chunks 28/28 reviewed, snippets 297/297 verified, slots 615/615 with a receipt (48 exempt); exit 0.
- Before the first validation, two wording edits were applied to the freshly written file with an inline script instead of the file-editing tool: the description of the two "untreated" IF image files was restored to the source's wording with a `source_caveats` note on each, and the description of `distribution_formats[1]` was replaced by a statement about the ro-crate files the releases distribute. The receipt file was first written chunk by chunk during reading and then rewritten once in full, with the same 28 entries, to match the final slot addresses of the record; the disposition of c002 changed from a provisional resource entry to the ORCID pair above and that of c008 to `nothing_relevant`.

## Phase 2 - core derivation

Command output of the first derivation (from the Phase 1 full record, md5 `84d82d15d629584b674b604eb92fbe3c`): derived true, 79 identity slots, `resources` projected, `linkml-validate: No issues found`.

## Phase 3 - source and provenance audit

Findings recorded against the full record: 6 in total (2 medium, 4 low; 2 + 4 = 6). All six were corrected in the full record; none remains open.

| # | Severity | Slot | Finding | Correction |
|---|---|---|---|---|
| 1 | medium | `instances[3].counts` | The value 53788 is the project website's undated "Immunofluorescent Images" panel figure (c015, c016). It sat on an instance described as the June 2026 release's IF images in MDA-MB-468 cells, which no passage says the figure counts. A count attached to a different counted set is a different claim, and the caveat beside it could not qualify it. | The count and the caveat that explained it were taken out of the instance. The figure remains in `description` as the website's own statement. Receipt pairs re-addressed to `description`. |
| 2 | low | `conforms_to` | One receipt pair (c010) quoted a preprint passage whose subject is output cell maps, which the releases state they do not include. | The pair was deleted from the receipt; the value keeps its receipt from the March 2025 release description (c018), whose subject is CM4AI output data. The top-level `source_caveats` now says the June 2026 release page does not repeat the statement. |
| 3 | medium | `subsets` | Omission. The data releases page (c016) describes two curated datasets, for iPSCs and iPSC-derived cells and for TNBC cells, with their modalities and stated coverage; the record did not represent them. | Two `subsets` entries added, each stating which members the page presents as included and which it marks "coming soon". Receipts added to c016. |
| 4 | low | `preprocessing_strategies[0].preprocessing_details` | The value described what the FAIRSCAPE framework does without the passage that attests its use on released data. | Added the preprint's statement that the toolkits "have been used to package and release our cell-line perturbation and measurement data" (c012), with its receipt. |
| 5 | low | `collection_mechanisms[0]`, `collection_mechanisms[1]` | The method text comes from file descriptions of earlier releases; the June 2026 page carries no file descriptions, and the values did not say so. | `source_caveats` added to both entries naming the releases the text was taken from. |
| 6 | low | `source_caveats` | The differently scoped project-end dates and the undated website figures were not flagged. | Three notes added to the top-level `source_caveats` (project end, website figures, packaging standard). |

Checks made with no finding: every entry of `creators` against the June 2026 author list (47 entries, one per listed author, ORCID where the list states one); the principal investigator against the NIH RePORTER designation; every file entry's name, directory, checksum, displayed size and publication date against the release page that lists it; versions, DOIs and publication dates of the four captured releases; the license name; the governance, intended-use, limitation, prohibited-use and bias statements against the June 2026 release description; future-tense statements (hierarchical cell maps to be delivered, predicted cell maps to be added, the Data Access Committee) kept as plans in the tense their source uses; enumeration slots (`limitation_type`, `bias_type`, `collection_type`, `credit_roles`, maintainer `role`) left empty where no passage states the category.

Recorded limits of this audit: the match of the ORCIDs of three named contacts to the author-list entries Parker J, Ravitsky V and Bélisle-Pipon JC rests on surname and initial; the name "University of Virginia" for `ROR:0153tk833` rests on the earlier releases stating that name for the same five authors. Both are stated in `source_caveats`.

After the corrections: schema validation `No issues found`; term validation `Validation passed`; `receipts check ... --strict` chunks 28/28 reviewed, snippets 304/304 verified, slots 618/618 with a receipt (51 exempt); exit 0.

## Phase 4 - re-derivation and checks

Derivation facts printed by `derive core --phase4-complete` on the corrected full record:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_d4d.yaml", "md5": "d53147874112c2943b3eb26575fffa43"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

- Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`, with one warning, `semantic-review-required` on `$.file_collections <-> $.distributions` (deterministic matches 38: 4 at collection level, 34 at nested resource level; unmatched core distributions none). The core was never edited by hand and `--sync-core` was not used.
- Identifier grounding (`grounding.check_run`): grounded 44, absent 0.
- Schema validation: full `No issues found`; core `No issues found`. Term validation: full `Validation passed`; core `Validation passed`.
- Scope check (`download scope --check --record <full> --record <core> --strict`): 2 records checked, none is about a dataset its project declares distinct.
- Core header: carries `# Sources:` naming this run's full record and `# Phase 4 reconciliation: completed`.
- Repair: no checker finding required a change after re-derivation, so no repair phase ran.

Informational sizes, not a quality measure: full record 39 populated top-level slots, 1236 lines; core record 40 populated top-level slots, 992 lines.

## Claims

| Slot | Change | Reason |
|---|---|---|
| `instances[3].counts` | Removed | Phase 3 finding 1: the website panel figure is not a count of the instance it was attached to. |
| `instances[3].source_caveats` | Removed | It only explained the count taken out by finding 1. |

No other slot was taken out of either record. Additions in Phase 3: `subsets` (two entries), `collection_mechanisms[0].source_caveats`, `collection_mechanisms[1].source_caveats`; amended values: `preprocessing_strategies[0].preprocessing_details` and the top-level `source_caveats`. The core record follows by projection.

## Semantic review

- `file_collections` <-> `distributions` (the pair checker's warning): the 4 collections and their 34 files appear in the core as 38 distributions with the same ids, names, paths, formats, media types, compression, checksums, descriptions and caveats; each collection's name states the release it belongs to. reviewed: consistent
- Counts and sizes against the entries beneath them: `total_file_count` and `total_size_bytes` are absent from both records; collection `file_count` values 6, 21, 8 and 10 stand over 6, 10, 8 and 10 listed files, the June 2025 collection's shortfall being the captured page's "1 to 10 of 21 Files", stated in its `source_caveats`, which the core carries; no byte sizes are recorded because the pages display rounded sizes. reviewed: consistent
- `dialect` and `is_tabular` against the files: neither slot is populated in either record; the listed files are ZIP archives, JSON metadata and HTML pages, for which the bundle states no dialect or tabular structure. reviewed: consistent
- Historical versus current release: the June 2026 Data Release is identified as current in `description`, `version_access.latest_version_doi` and `resources[4]`; the three earlier captured releases and the release cited by the 2024 preprint are separate `resources` entries with their own versions and dates, and their files are separate, release-named collections, so no earlier release's file, count or date is stated as the current one. reviewed: consistent

## Files changed

- Written: the full record, the core record (derived twice, never hand-edited), the coverage receipt and this report, all under the version label above.
- A scratch copy of the executable playbook view was written to `.temp/playbook_view.md` for reading; it is not an output of the run.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CM4AI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
grounding.check_run(<full>, <core>, <bundle>, uriorcurie_slots())
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record <full> --record <core> --strict
report_claims.check_report(<report>, full, core, declared_slots())
```

One command was first run in a spelling the tool refused (`download priority --manifest ...`, exit 2, "No such option") and then re-run with the root `--manifest` option.

## Final results

- Full record: schema-valid and term-valid.
- Core record: derived by projection, schema-valid and term-valid, header complete.
- Pair checker: PASS, one semantic-review warning, reviewed above.
- Receipts: 28/28 chunks reviewed, 304/304 snippets verified, 618/618 slots with a receipt.
- Grounding: 0 identifiers absent from the bundle.
- Scope: in scope.
- Reconciliation outcome: completed; 6 Phase 3 findings, all corrected in the full record; no Phase 4 repair.
