# AI_READI reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`
- Method: `claudecode_release`; mode: four-phase project agent, generic-v9 prompt; arm: BASELINE (input documents only)
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). The workflow does not observe the native runtime's sampling settings, and nothing here establishes an effective temperature or deterministic generation.
- Source bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `1a58ad7be37d4b08ebd9d94e6ad173a3`, 6424 lines, 25 chunks)
- Chunk manifest: `data/preprocessed/chunks/AI_READI_chunks.yaml`; source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml` (md5 `f8fc8f7142c971112373da16f3a087a0`)
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d_core.yaml` (md5 `a5516546b5128c12ec033c1e4ceffa5c`)
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The declared scope (`download scope --project AI_READI`) names the referent as "AI-READI dataset", https://doi.org/10.60775/fairhub.3, and declares no related-but-distinct dataset. The record describes that referent: version 3.0.0 of the "Flagship Dataset of Type 2 Diabetes from the AI-READI Project", the public release on FAIRhub, and both records hold to it (`id: doi:10.60775/fairhub.3`).

Three kinds of passage in the bundle are not about that referent's current state, and were handled as follows:

- Earlier releases (version 1.0.0 and 2.0.0; the FAIRhub page and documentation for version 2.0.0, including its "2.01 TB" and "165,051" file figures). Their facts appear only as version history under `version_access`; the version 2.0.0 size and file figures are not in the record.
- The controlled-access set. The documents contrast it with the public dataset; its contents are mentioned only inside statements that say they are outside the public dataset.
- Plans (the IRB protocol application, the NIH RePORTER abstract, enrollment targets). They are stated as plans, attributed to the document, or omitted.

No scope declaration lists a related dataset, so `related_datasets` is empty. The FAIRhub page notes a smaller version for pipeline development; the bundle gives no identifier for it, so it is recorded only in `source_caveats`.

## Phase 1 - full generation

- Chunk manifest check: `current`, 25 canonical chunks under the selected rule.
- All 25 chunks were read with the file-reading tool in manifest order, one receipt entry written before the next chunk was read.
- The receipt's slot addresses were provisional while reading (the record did not yet exist). After the record was written, the receipt was rewritten once with the final addresses, using only the chunks already read; every chunk kept its entry. The original entries and the rewrite are in the transcript. This is the Phase 1 correction the playbook allows before Phase 2; it does not change the reading order.
- Strict receipt check before Phase 2: `chunks 25/25 reviewed · snippets 464/464 verified`, exit 0.
- Schema validation and term validation of the full record: both passed.

Source ranking used for disagreements (`download priority --project AI_READI`): tier 1 FAIRhub dataset pages and FAIRhub structured metadata; tier 2 dataset documentation, license, IRB protocol; tier 3 the two publications; tier 4 the NIH RePORTER page.

## Phase 2 - core derivation

Command output (first derivation, before the Phase 3 corrections):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml", "md5": "e9cc14f77c602075c00776d66caad760"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated (`linkml-validate: No issues found`).

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle, the chunk manifest, and the declared scope and source ranking from the selected source manifest. Structural inputs: the full schema file and the repository's own schema digest for class `Dataset`.
- No previously generated D4D record, evaluation, or reconciliation report was read. Nothing under `data/d4d_concatenated/` was opened except this run's own AI_READI files (the full record, the core record, the receipt, this report and the provenance record); nothing under `data/ro-crate_packages/` was opened. A listing of this label's two output directories showed that they also hold another project's files from the same label (CHORUS); only their names were seen and none was opened.
- Repository instructions read: the provenance guard, the playbook (executable view), the uniform rules, the full-record method file, and the receipts pattern note (for the receipt shape). The receipt validator's snippet normalization was read in source to write snippets it can verify.
- No live web content was fetched.

### Findings

Seven findings were recorded. Three led to a correction; four were reviewed and left unchanged.

| # | Kind | Location | Finding | Outcome |
|---|---|---|---|---|
| 1 | Shape | `creators[1]` to `creators[19]` | Each entry carried only a `principal_investigator` object, so the creator entry itself had no name or identifier. | Corrected: the creator-level `name` was added to all 19 entries, and the creator-level `id` (the ORCID as a CURIE) to the 15 whose ORCID the FAIRhub study description states. The four entries known only from the Nature Metabolism author list have a name and no creator-level id. |
| 2 | Count and unit relationship | `total_size_bytes`, `file_collections[*].total_bytes` | The FAIRhub metadata give sizes as bare integers with no unit; the record states them as bytes. The directory entries do not sum to the stated totals. | Corrected by adding item (6) to the top-level `source_caveats`: the basis for reading the integers as bytes, the record's own sums with their inputs, both stated totals, and the differences. Neither figure was adjusted. |
| 3 | Receipt | `informed_consent[0].consent_type` | The in-person half of the value had no receipt from the passage that states it in the present tense. | Corrected in the receipt: one pair added to the existing c002 entry. |
| 4 | Status | `sensitive_elements[0].sensitive_elements_present` | The `false` rests on a healthsheet sentence in the future tense ("the public dataset will not contain data that is considered sensitive"). | Unchanged. The value's own `sensitivity_details` states the sentence in the source's tense, and the FAIRhub abstract states in the present tense that the data contain no protected health information. |
| 5 | Status | `at_risk_populations.at_risk_groups_included` | The `false` rests on the eligibility criteria the healthsheet says were used (40 years or older, able to consent, not pregnant) and, for prisoners and adults unable to consent, on answers in the IRB protocol application, which is a planning document. | Unchanged. The `description` attributes each part to its source. |
| 6 | Status | 28 slots flagged by `receipts status-context` | The lexical check flagged snippets whose passage carries a future or in-progress marker. | Unchanged after reading each flagged value against its passage. Every value that rests only on a plan states it as a plan or attributes it to the planning document (for example `sampling_strategies[1].description`, `participant_privacy[2].privacy_techniques`, `updates.frequency`). Values stated in the present tense have a second passage in the present or past tense (the protocol publication or the healthsheet), or describe the release that the FAIRhub metadata date as available. |
| 7 | Source conflict | Several slots | Eight disagreements between sources were checked for whether they are genuine. | Unchanged; each is recorded in the `source_caveats` of the slot it concerns, as listed below. |

Finding totals, counted from the table above: 7 findings; 3 corrected (2 in the full record, 1 in the receipt only); 4 unchanged.

### Source disagreements (finding 7)

| Subject | What the sources say | Treatment |
|---|---|---|
| Start of collection | FAIRhub metadata: collection period 2023-07-19 to 2025-05-01, study start 2023-07-19. Protocol publication: enrollment began on 18 July 2023. | The statements may describe different events, so comparability is uncertain. FAIRhub (tier 1) dates are used; the publication's date is kept in `collection_timeframes[0].source_caveats`. |
| What version 3 contains | Version 3 documentation page: "contains data from the participants of the pilot study phase". FAIRhub healthsheet: data collected up through the end of the second year. | Genuine conflict. FAIRhub (tier 1) preferred over documentation (tier 2); recorded in the top-level `source_caveats`. |
| License name | FAIRhub page: "Health Data License". FAIRhub metadata: "AI-READI custom license v2.0". License text: "AI-READI DATA LICENSE AGREEMENT (Version 2.0)". | Treated as names of one license, not a conflict; the structured-metadata name is used and the others are in `source_caveats`. |
| Enrollment target | 4000 (protocol publication, FAIRhub study description), "4,000+" (NIH RePORTER), 4600 (IRB protocol application). | All are plans at different times; none is the size of this release (2280 participants). Recorded in `source_caveats`. |
| Grant number spelling | One healthsheet answer: "OT2ODO32644". Everywhere else, including other fields of the same metadata: OT2OD032644. | OT2OD032644 used; the variant is in `funders[0].source_caveats`. |
| De-identification wording | FAIRhub metadata: no identifiers were collected, so no active de-identification was necessary. Nature Metabolism comment: the public set is stripped of PHI via the "Safe Harbor" method. | Both kept; the FAIRhub wording (tier 1, about this version) is the stated detail and the other is in `is_deidentified.source_caveats`. |
| Health-record screening window | Healthsheet: encounters within the past 2 years. Protocol publication: encounters between 2020 and 2025. | Both kept in `sampling_strategies`. |
| "First year" statement | The version 3 healthsheet says the dataset holds all participants enrolled "during the first year", and elsewhere that this version covers through the second year. | Same source, same tier; both statements are represented in `sampling_strategies[0].source_caveats`. |

One further compatibility note: the NIH RePORTER page lists the 2022 award's principal investigator at the University of Washington, and the FAIRhub study description gives the same person's affiliation as Washington University in St. Louis. These are observations at different times, not a conflict; the FAIRhub affiliation is recorded and the other is in the caveat on that person.

### Slots deliberately left empty

These are judgments about evidence, not removals; none of these slots was populated at any point in the run.

- `errata`, `extension_mechanism`, `data_protection_impacts`, `existing_uses`, `use_repository`: the healthsheet answers that the thing is absent (or leaves the answer empty). An absence is not an entry; the statements are in the top-level `source_caveats`.
- `citation`: the sources point to a documentation page for the citation and do not state it.
- `download_url`: the bundle gives the landing page and the access route, not a URL for the data itself.
- `is_tabular`: the dataset mixes tabular, imaging and waveform data.
- `status`: the only status the bundle states is the study's enrollment status, which is not the status of this release.
- `related_datasets`: no related dataset is declared, and the one candidate has no identifier in the bundle.
- `variables`: the only variable list in the bundle is the planned list in the IRB protocol application.
- `discouraged_uses`: the healthsheet answers with a pointer to the license; the license's prohibitions are recorded under `prohibited_uses`.
- `created_on`: the bundle gives an epoch integer whose conversion would be a derived value, and the availability date is already in `issued`.
- Enumeration slots with no passage stating the category: `maintainers[0].role`, the `collection_type` of the nine data directories, `regulatory_restrictions.hipaa_compliant`, `regulatory_restrictions.confidentiality_level`, and `limitation_type` on three of the four limitations.

### Judgment calls a reviewer may want to check

- `data_governance.accountable_organization` is Washington University in St. Louis. The sources call it the managing organization, the lead sponsor and the licensor (which holds title to the data); none uses the word "accountable". The caveat on the object lists the three roles as stated.
- `principal_investigator`: the FAIRhub study description designates one responsible-party Principal Investigator (recorded on the AI-READI Consortium entry) and lists 16 officials with the role "Study Principal Investigator"; the Nature Metabolism comment lists names under the heading "Principal Investigators". Each designated person is recorded once. Four names appear only in the Nature Metabolism list, which was extracted from a multi-column layout; affiliations are recorded only for the two whose affiliation superscript sits directly beside the name, and the entries carry a caveat.
- `funders[0].grants[1]`, `funders[0].grants[2]` and `funders[1]` come from the publications' funding statements ("This research is supported by ..."), not from the dataset metadata, which names only OT2OD032644. Each carries a caveat.
- `collection_mechanisms`: device and procedure descriptions written in the future tense in the healthsheet are stated in the present tense where the protocol publication states the same procedure in the present tense.

## Phase 4 - re-derivation, checks, report

### Re-derivation

Command output (second derivation, with `--phase4-complete`, from the corrected full record):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml", "md5": "f8fc8f7142c971112373da16f3a087a0"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The core was never edited by hand and `--sync-core` was not used.

### Check results

| Check | Result |
|---|---|
| Full record, schema validation (`Dataset`) | No issues found |
| Full record, term validation | Validation passed |
| Core record, schema validation (`CoreDataset`) | No issues found |
| Core record, term validation | Validation passed |
| Pair consistency | PASS: 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class`, `conforms_to_schema`. One warning, `semantic-review-required`, on `file_collections` and `distributions`: 19 deterministic matches (10 at collection level, 9 at nested resource level), no unmatched core distributions |
| Grounding of identifiers against the bundle | 27 grounded, 23 minted fragments, 0 absent |
| Strict receipt check after the Phase 3 corrections | chunks 25/25 reviewed, snippets 475/475 verified, exit 0. Reported diagnostics, not gated: 9 snippets bearing on no token of their value, 13 entry receipts overlapping one leaf, slots 414/453 with a receipt (40 exempt) |
| Receipt readdress listing | no unresolved receipt addresses |
| Scope check, report-claims check, post-record receipt write | see "Closing checks" at the end of this report |

The 23 minted fragments are 10 file-collection ids, 9 file ids and 4 person ids, all on this record's own id `doi:10.60775/fairhub.3`.

On the receipt diagnostics: the slots without a leaf receipt are mostly short labels composed for list entries (the `name` of a collection mechanism, a sampling strategy, a prohibited use or an external resource) and leaves covered by an entry-level receipt (a person's name and affiliation under a receipted creator entry). They were re-examined and not padded.

## Claims

No slots were removed.

Nothing was relocated between slots after the full record was first written. The Phase 3 corrections added values (creator-level `name` and `id`, and one item in the top-level `source_caveats`); they did not remove or move any.

## Semantic review

- `file_collections` and `distributions` (the checker's `semantic-review-required` warning): each of the 10 collections and 9 files in the full record has exactly one distribution in the core with the same id, name, path, standard and description; the nine data directories carry their size as `bytes`, and the root metadata collection carries none because the bundle states none. All of it describes version 3.0.0. reviewed: consistent
- `total_file_count` against the entries beneath it: the nine directory `file_count` values sum to 356334 (the record's own computation); the stated total is 356343; the difference of 9 equals the nine root-level metadata files listed. Both figures and the difference are in the top-level `source_caveats`, added in Phase 3. reviewed: corrected (the caveat was added; no figure changed)
- `total_size_bytes` against the entries beneath it: the nine directory `total_bytes` values sum to 3815969360064 (the record's own computation); the stated total is 3815969779678; the difference is 419614 bytes, which the bundle does not explain (the root metadata files have no stated size). Both figures and the difference are in the top-level `source_caveats`. reviewed: corrected (the caveat was added; no figure changed)
- `dialect` and `is_tabular` against the files: no file entry carries a dialect, so none was derived; `is_tabular` is set in neither record because the release mixes tabular, imaging and waveform data. The nine file entries take `format`, `media_type` and `file_type` from the file names and the source's description of each as a metadata file. reviewed: consistent
- Historical versus current release: every file-collection, size, count and standard value comes from the FAIRhub structured metadata and README for dataset 3 (version 3.0.0). The version 2.0.0 page's size and file count are not in either record, and statements about versions 1 and 2 appear only under `version_access`. reviewed: consistent

## Files changed

- Written: the full record, the core record (derived twice, never hand-edited), the coverage receipt, this report, and the provenance record the recorder writes beside them.
- One scratch file outside the three declared outputs: `.temp/playbook_view.md` (with an empty `.temp/playbook_view.err`), the output of `agents playbook --relative-toolchain`, written to the checkout's existing `.temp/` directory (untracked, and not gitignored in this checkout) so it could be read in two windows. It holds no dataset facts and was left in place. It is disclosed here because the instruction limits writes to the declared outputs.
- No other file in the repository was modified.

## Deviations and limits

- The repository's schema digest for `Dataset` was obtained by calling `data_sheets_schema.schema_digest.digest_text` inline, because the launch instruction refers to "the schema digest" and no command prints it. A few class definitions were also read directly from the full schema file.
- The transcript audit (`data_sheets_schema.agentic_observed`) and `provenance annotate-observed` are the orchestrator's steps and were not run by this agent, which cannot observe its own token use, tool-use count or duration. No observed totals are recorded.
- Receipt origin: because the receipt was rewritten once with final addresses after the record was written, a transcript-based origin measurement will see that rewrite; the per-chunk entries written while reading are earlier in the transcript.
- A verified snippet shows that a passage exists in the chunk, not that it entails the value. The receipts were written to cite the passage each value was taken from, but that judgment is not machine-checked.

## Commands

All run from the checkout root.

```bash
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project AI_READI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli receipts status-context --receipt <receipt> --bundle <bundle> --record <full> --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml
.venv/bin/python -m data_sheets_schema.cli receipts readdress --receipt <receipt> --full <full>
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d_core.yaml
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d_core.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Plus the playbook's two inline checks (`grounding.check_run` and `report_claims.check_report`), the provenance recorder line as given in the launch instruction with one `--phase` flag per phase performed, the receipt check repeated with `--write`, and the scope check with `--check --record <full> --record <core> --strict`.

## Final results

- Full record: valid against `Dataset`; terms valid; 69 populated top-level slots.
- Core record: valid against `CoreDataset`; terms valid; 60 populated top-level slots; header carries `# Sources:` naming the same-run full record and `# Phase 4 reconciliation: completed`.
- Pair consistency: PASS, no errors.
- Reconciliation outcome: completed. Phase 3 corrected the full record twice and the receipt once; Phase 4 re-derived the core and found nothing that required a repair, so no repair phase ran.

## Closing checks

These two checks need this report or the final pair to exist; they were run on the report as written above this section, and this section was then added before the provenance record was written, so that the record pins the report's final bytes.

- Report-claims check (`report_claims.check_report`): 0 findings. `claims_checked` is 0 because the report has no removal rows; the checker does not yet read the "No slots were removed." line, so this count is unmeasured rather than clean.
- Scope check (`download scope --check --record <full> --record <core> --strict`): 2 records checked against the declaration; neither is about a dataset the project declares distinct; exit 0.

Steps that run after this report is final are not described here: the provenance recorder, the receipt check repeated with `--write`, `runs validate` and the run check. Their results are in the provenance record and in the agent's final return. The recorder was run twice: once before and once after two wording corrections to this report (the description of the `.temp/` directory and the note about the directory listing), so that the record pins the corrected bytes. Neither YAML record nor the receipt changed between the two.
