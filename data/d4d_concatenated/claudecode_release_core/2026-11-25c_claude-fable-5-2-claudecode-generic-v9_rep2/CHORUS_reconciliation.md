# CHORUS reconciliation report

- Label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2`
- Method: `claudecode_release`, four-phase project agent, generic-v9 prompt, BASELINE arm (input documents only)
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_coverage_receipt.yaml`
- Declared bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (md5 `9b2ef4b65d67957f79362266cab0bc7a`, 1698 lines, 8 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Temperature: unknown (not observed from the agent runtime). No sampling setting is inferred from the prompt, the model name or the effort level.

## Referent

The declared scope names one referent, the CHoRUS dataset (`https://chorus4ai.org/`), and declares no related-but-distinct dataset. The record describes that referent: the multicenter clinical care dataset the CHoRUS project generates. Both records use `https://chorus4ai.org/` as `id` and `page`; no dataset DOI or version identifier appears in the bundle. The scope check reports that neither record is about a dataset the project declares distinct.

The bundle's four sources are about the referent or the project that produces it, at different times and in different modes, and the record keeps them apart:

| Source (manifest tier) | What it is | How the record uses it |
|---|---|---|
| Project website (tier 2) | Current website snapshot, undated | Current released dataset figures; anticipated final dataset stated as anticipated |
| NIH RePORTER project page (tier 4) | Fiscal year 2022 award abstract | Funding and principal investigator as facts; everything in the abstract stated as a plan |
| AIM-AHEAD cohort 2 webinar (tier 4) | Training-program slides dated September 09, 2025 | Dataset state "as of August 2025"; access process scoped to the training program |
| GitHub organization overview (tier 5) | Historical capture of 2025-11-14 | Project aims stated as plans; repositories as an external resource |

## Phase 1 - full generation

All eight chunks were read with the file-reading tool in manifest order, and each chunk's receipt entry was written before the next chunk was read. One chunk (`c001`, the concatenation preamble) is `nothing_relevant`; seven are `extracted`.

Phase 1 correction loop, before Phase 2: after the full record was written the receipt was rewritten once so that its slot paths address the record as written, and four list-valued slots (the keyword list, the standards list and the two link lists under the external resources) were given a receipt at the list path the checker counts in addition to the per-item paths. No bundle text was re-read through any other route and no chunk entry was dropped.

Strict receipt check before Phase 2: `chunks 8/8 reviewed · snippets 185/185 verified (1 bearing on no token of their value) · slots 99/99 with a receipt (7 exempt)`. The one snippet bearing on no token of its value receipts the `OTHER` member of the standards list, which is an enumeration value standing for standards the vocabulary lacks (OHNLP, EDF+ and Persyst); the snippet names one of those standards.

## Phase 2 - core derivation

The core was derived by projection from the validated full record. JSON printed by the first derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d.yaml", "md5": "2d58e8cf526b04a2a031df94a8e75a23"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle and the source manifest. Structural inputs read: the full schema, the playbook, the uniform rules, the provenance guard and the receipt checker's source.
- No previously generated D4D record, evaluation or reconciliation report was read, opened or searched, from any arm, label or date. The only generated YAML read is this run's own full record, core record and coverage receipt.
- Only the two output directories of this label were listed, to confirm they did not exist before the run.

### Findings

Five findings were recorded, all in the full record, all corrected there. Totals are counted from the rows below: 5 findings, of which 1 moderate and 4 minor.

| # | Severity | Slot | Finding | Source passage (chunk) | Correction |
|---|---|---|---|---|---|
| F1 | minor | `purposes[1].response` | Said the website "heads its dataset section" with the quoted line; the flattened page text does not establish section structure | "Expanding Artificial Intelligence and Machine Learning to Improve Recovery from Acute Illness" (c006) | Reworded to say the website carries the heading |
| F2 | minor | `tasks[1].response` | Attached "among patients with acute or critical illness" to predicting complications; the passage attaches that phrase unambiguously only to the last item of its list | "predicting complications, and measuring treatment response among patients with acute or critical illness" (c002) | Narrowed to the task alone |
| F3 | minor | `existing_uses[0].description` | Stated in the present tense what the webinar states as future | "Trainees will receive hands-on training on the Bridge2AI AI/ML for Clinical Care Network" (c004) | Restated in the source's tense |
| F4 | moderate | `license_and_use_terms.license_terms` | Claimed the webinar table lists every data type as controlled: an inference from equal cell counts in a table whose row and column ownership the flattened text does not preserve | "Controlled access" (c003) | Clause deleted from the value; the slot keeps the stated "Controlled access" and the licensing-agreement requirement |
| F5 | minor | `conforms_to` | Carried evidence commentary inside the value | "Demographics OMOP"; "EEG – extraction in process at this point" (c003) | Reduced to the standards the source names, keeping only the in-process status of the EEG standard |

No source-supported omission was back-ported and no receipt entry was added in Phase 3: every corrected value is still supported by the snippets already receipted at its path. The strict receipt check was re-run after the corrections and reports the same counts as before Phase 2.

### Source conflicts and compatibility

No genuine source conflict was found, so the manifest ranking was not needed to decide a value.

- Admissions: the website (tier 2) lists 50,000 patient admissions for its current released dataset; the webinar (tier 4) says "over 45K unique admissions" as of August 2025. A lower bound at one date and a figure from an undated snapshot are compatible; both are kept in `instances[0]` and the comparison is explained in its `source_caveats`.
- Final size: the NIH abstract aims at a data set "from more than 100,000 critically ill patients"; the website anticipates 100,000 patient admissions. Different units, both plans; neither is merged into the other.
- Sites: 14 hospitals (website, webinar) and 14 Data Acquisition centers among 20 academic centers (GitHub overview) agree.

### Judgments recorded for review

- **Creators.** The six `creators` entries are the people the webinar lists as the "Bridge2AI CHoRUS Leadership Team", each with the institution printed under the name. Only Eric S. Rosenthal is designated principal investigator (NIH RePORTER), so only that entry carries `principal_investigator`; the other five are recorded with the role the source states, in `description`.
- **Contact.** The website's "Contact Us" person is a program manager, not a designated maintainer, so `maintainers` stays empty and the contact is kept in `notes`. The address is transcribed as the website spells it.
- **License.** The GitHub overview's MIT statement concerns the GitHub project. No source states a license for the dataset, so the top-level `license` slot stays empty; the controlled-access and licensing-agreement statements are in `license_and_use_terms`.
- **Flattened table.** The webinar's data-type table lost its row and column structure in extraction. A data standard is attributed to a data type only where the text prints it on the same line as, or directly after, that type's label (demographics, imaging, waveform telemetry, waveform EEG). The "Metadata" and "Published metadata schema" columns are not transcribed.
- **Plans.** Sampling, labeling, the holdout test set and the re-identification-limiting transformation are stated only as plans in the sources and are written as plans. `is_deidentified` carries no presence boolean and no method.
- **Enumerations left empty.** No passage classifies a creator's CRediT role, a maintainer type, a data use permission or a limitation type, so those slots are not populated.
- **Access.** The registration, licensing-agreement and ".edu" email statements come from a training-program webinar and are scoped to that program's participants in the record.

## Phase 4 - re-derivation, checks, report

The core was re-derived from the corrected full record with the Phase 4 marker. JSON printed by the final derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d.yaml", "md5": "c8ccc2472c849f18bbbc66cc6bc519fe"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

### Check results

| Check | Result |
|---|---|
| Full record, schema validation (class Dataset) | No issues found |
| Full record, term validation | Validation passed |
| Core record, schema validation (class CoreDataset) | No issues found |
| Core record, term validation | Validation passed |
| Pair checker | PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema'] |
| Grounding check | `{'grounded': 0, 'minted_fragment': 0, 'absent': 0}`; no finding |
| Scope check (strict) | 2 records checked; none is about a dataset the project declares distinct |
| Receipt check (strict) | chunks 8/8 reviewed; snippets 185/185 verified; slots 99/99 with a receipt (7 exempt) |

The pair checker reported no error and emitted no warning. No finding from the grounding check, the pair checker or the report-claims check required a change, so no repair phase ran.

Identifiers minted by this record: two labels, both fragments on the record's own id, both for objects whose class requires an id and for which the bundle states no identifier (the principal investigator, for whom the bundle states no ORCID, and the OHNLP toolkit under `used_software`). No identifier for an organization, a grant or a program was supplied from outside the bundle.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions`: the pair checker emitted no `semantic-review-required` warning; the full record has no file collections, because the bundle names no files, and the core has no distributions. reviewed: consistent
- `total_file_count` and `total_size_bytes` against the entries beneath them: neither slot is populated; the website's "23 Tb" is the size of the waveform data alone and is kept in prose with its unit, not converted or summed. reviewed: consistent
- `dialect` and `is_tabular` against the files: neither slot is populated and no file is named. reviewed: consistent
- Historical versus current release: the single count in the record (`instances[0].counts`, 50000) comes from the website's "Current Released Dataset"; the anticipated final dataset is in `updates`, the August 2025 state and the 2022 plans carry their dates in the prose that states them. reviewed: consistent
- Counts against their units: every figure is paired with the unit its source counts (patient admissions, rows of EHR OMOP data, admissions with radiology data, hospitals, images). reviewed: consistent

## Files changed

- Written: the full record, the core record (derived twice, never edited by hand), the coverage receipt, this report.
- Nothing else in the repository was created or modified by the generation phases. A scratch copy of the rendered playbook view was written under the checkout's `.temp/` directory for reading.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project CHORUS
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project CHORUS --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CHORUS_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "... data_sheets_schema.grounding.check_run ..."   (the playbook's grounding program)
.venv/bin/python -c "... data_sheets_schema.report_claims.check_report ..."   (the playbook's report-claims program)
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CHORUS --check --record <full> --record <core> --strict
```

One read-only diagnostic was also run inline: a call to the receipt checker's own `check` function to list which slot paths it counted without a receipt (it named the four list-valued slots described under Phase 1). It wrote nothing.

## Final results

- Both records validate against their schemas and pass term validation.
- The pair checker passes on the re-derived pair with no warning.
- Phase 3: 5 findings (1 moderate, 4 minor), all corrected in the full record; no back-port.
- Phase 4: no repair needed; reconciliation completed.
