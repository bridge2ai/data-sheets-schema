# VOICE_PEDIATRIC reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`
- Method: `claudecode_release`; arm: BASELINE (input documents only)
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Mode: four-phase project agent, generic-v9 prompt
- Temperature: unknown (not observed from the agent runtime). This workflow does not observe the native runtime's sampling settings.
- Repository commit at run time: `edd279fd27e1d4add4b0d536888638f55254a022`
- Declared input bundle: `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt` (md5 `0350223711484a63c21b2dd57af6f4c9`, 2866 lines, 13 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`; chunk manifest: `data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml` (reported `current`, 13 canonical chunks)

## Files

| File | Role |
|---|---|
| `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml` | full record, written in Phase 1, corrected in Phase 3 |
| `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d_core.yaml` | core record, derived in Phase 2, re-derived in Phase 4; never edited by hand |
| `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_coverage_receipt.yaml` | coverage receipt, written chunk by chunk in Phase 1, edited in place in Phases 1 and 3 |
| `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_reconciliation.md` | this report |

## Referent and scope

The declared scope names the referent as the Bridge2AI-Voice Pediatric Dataset (`https://doi.org/10.13026/mf9s-5r03`) and declares the adult Bridge2AI-Voice dataset related but distinct, to be expressed through the related-datasets slot. The record describes the Bridge2AI-Voice Pediatric Dataset on PhysioNet at its current release, version 1.1.0, and holds to that referent in both records.

- The PhysioNet page states two DOIs. The record's own identifier is the latest-version DOI as a CURIE (`doi:10.13026/mf9s-5r03`); its DOI slot carries the version 1.1.0 DOI (`10.13026/h995-bt35`), the one the recommended citation uses. Both are stated in the bundle and the choice is explained in the record's top-level caveat.
- Five of the six bundle sources (IRB protocol, project documentation, NIH RePORTER page, Data Transfer and Use Agreement, documentation repository README) chiefly describe the Bridge2AI-Voice project and its adult dataset. A value was taken from them only where the passage is about the pediatric data, about the project as a whole (funding program, project leadership), or about a named person (affiliations).
- Not used, because the passages describe the adult dataset or another protocol: the documentation's study metadata, de-identification levels and details, consent details, healthsheet composition, labeling, collection, uses, distribution and maintenance answers, folder tree and version 3.0.0 de-identification methods; the University of South Florida IRB protocol's procedures, consent, assent, compensation, retention and privacy provisions (the protocol states that the Canadian institutions, SickKids among them, apply for a separate research ethics board review and that no pediatric data collection is performed at USF); the Data Transfer and Use Agreement's terms.
- The adult dataset appears once, as one related-dataset entry of type `references`, on the strength of the pediatric page's own note that the adult dataset is also available on PhysioNet. No adult-dataset fact is carried in a slot describing the referent.
- No naming declaration exists for this project key in the selected manifest; names are written as the sources state them.

## Phase 1 - full generation

- All 13 manifest chunks were read with the file-reading tool in manifest order and a receipt entry was written after each chunk and before the next was read.
- Chunk dispositions: 10 `extracted` (c002 to c011), 3 `nothing_relevant` (c001 preamble, c012 closing clauses of the agreement template, c013 documentation repository README).
- Schema validation and ontology term validation of the full record passed on the first run.
- Receipt corrections before Phase 2 (addresses and coverage only, from chunks already read): the first strict receipt check passed with 303 of 310 receiptable slots covered. The seven uncovered slots were list-valued leaves (keywords, available versions, release dates, IRB approval, special populations, guardian consent, external resource links) receipted at item paths; a receipt at each list's own path was added to the existing c002 and c003 entries. The second check reported 310 of 310.

## Phase 2 - core derivation

Command output of the Phase 2 derivation (from the Phase 1 full record):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml", "md5": "e0ea796cd75638f90032e4845f38afc4"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The command's own validation of the derived core reported no issues.

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle, the selected source manifest, the chunk manifest, the full and core schema files (through the repository's schema digest for class `Dataset` and targeted reads of the schema), the playbook, the provenance guard and the uniform rules.
- No previously generated D4D record, evaluation or reconciliation report was opened. The same-label output directories were listed by file name only, to confirm that no VOICE_PEDIATRIC artifact existed before this run; no other project's record was read.
- Scratch files written outside the three outputs and the receipt: the rendered playbook view and the rendered schema digest under the checkout's `.temp/` directory (structure and instructions only, no dataset facts).

### Findings

Nine findings were recorded against the full record: 2 medium and 7 low. All nine were corrected in the full record; none concerns the core, which is re-derived.

| # | Severity | Location in the full record | Finding | Correction |
|---|---|---|---|---|
| 1 | medium | subpopulations entry, presence flag | The flag asserted that the dataset explicitly identifies subpopulations. The only support is the documentation's sentence that pediatric participants "are grouped by age", which states a grouping of participants and not what the release's files identify. | Flag taken out; the grouping and the protocol names stay in the identification text, and the entry's caveat says why no flag or distribution is recorded. |
| 2 | medium | features file collection, file list | `audio_quality_metrics.tsv` was listed as a file of the features collection with a caveat. The data description names the file in the paragraph on the features folder without stating which folder holds it; a structural assertion kept with a disclaimer is still unsupported. | File entry taken out of the collection. The file and what it holds are stated in the tab-separated distribution format entry, and the top-level caveat records that its folder is not stated. |
| 3 | low | `sparc_pitch.parquet` description | The description said the algorithm differs from that of `torchaudio_pitch.parquet`; the source says only "a different algorithm than before". | Reworded to quote the source. |
| 4 | low | participant privacy entry | "manually checked ... before release" added an ordering the source does not state. | Reworded to the source's statement that version 1.1 releases features for free speech tasks that were manually checked. |
| 5 | low | human subject research, special populations | "Minors" characterizes participants aged 2 to 18 beyond the source's words. | Reworded to "Pediatric participants aged 2 to 18 years." |
| 6 | low | top-level caveat | The caveat said the documentation's healthsheet answers were not used, but the designation of the two co-principal investigators and five affiliations come from the healthsheet's answer on who leads the project. | Caveat corrected to state that exception, and a sentence added on where creator affiliations come from. |
| 7 | low | funder description, subpopulation identification, sampling source data | Evidence commentary ("the project documentation states ...") sat inside the values. | Commentary moved to the entries' caveats (funder, subpopulation) or dropped where the value needs none (sampling). |
| 8 | low | direct collection (omitted) | The pediatric page states that all participants completed the recording and demographic data collection in one session and that parents or decision-makers completed the survey for some participants; the direct-collection slot was empty. | Entry added with its two receipts in the existing c002 receipt entry. |
| 9 | low | b2aiprep software object | Version and license come from two different passages (the dataset page's reference; the documentation's supporting materials) with no caveat saying so. | Caveat added on the software object. |

Checks that produced no finding:

- Counts and their units: 23,533 is the number of recordings with derived features and 300 the number of participants, both from the version 1.1.0 abstract; the four `sparc_*` files are stated with n=23532 and the instance entry's caveat records the difference without adjusting either figure. No figure in the record is derived by the record.
- Dates and versions: version 1.1.0 published May 1, 2026; version 1.0.0 dated Dec. 17, 2025 appears only as version history. The documentation's sentence that the pediatric dataset v1.0 contains data from 300 participants is recorded as a statement about v1.0.
- Roles: the principal-investigator objects rest on passages that use that title for the project that produced the dataset (project documentation: Bensoussan and Elemento as co-principal investigators; NIH RePORTER: Bensoussan as principal investigator). These are compatible, not a conflict; both designations are recorded and the difference is in the entries' caveats.
- Funding: the dataset page states NIH project number 3OT2OD032720-01S1; the NIH RePORTER page in the bundle is the record of 3OT2OD032720-01S3 under the same core project number and title. One grant is recorded, with the number the dataset page states; the other forms are in the funder's caveat.
- Privacy fields: no de-identification entry is recorded, because the only de-identification statements in the bundle describe the adult dataset. The participant privacy entry states operations the sources attest in a privacy role.
- Enumerations: confidentiality level `restricted` rests on "This is a restricted-access resource"; the metadata collection's type rests on "metadata information for the recordings (available under metadata)"; the relationship type `references` rests on the pediatric page's note pointing to the adult dataset. No collection type is recorded for the features and phenotype collections, and no variable data type, because no passage states the category.
- Identifiers: no registry identifier was supplied from outside the bundle. No ORCID or ROR appears in the bundle; none is in the record.
- Affiliations: recorded only where an investigator row or a parenthesis names the person's institution unambiguously. Rows of the protocol's first investigator table that continue under another row's institution cell were not used; the affiliations of "Jennifer Sui" and "Don Bolser" in the documentation were not attached to the authors "Jennifer Siu" and "Donald Bolser".
- The documentation's questionnaire table is flattened so that column ownership cannot be established; no questionnaire is attributed to the pediatric cohort.

## Phase 4 - re-derivation, checks, report

### Re-derivation

Command output of the Phase 4 derivation (from the corrected full record, with the phase-4 header line):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml", "md5": "222c67f963ed0b937a51f8955375689b"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

### Pair checker

```
PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: Phase 4 must semantically review related distribution content; deterministic matches=14 (3 at collection level, 11 at nested resource level), unmatched core distributions=[]
```

No error. The single warning is answered in the semantic review section below.

### Grounding

`{'grounded': 1, 'minted_fragment': 21, 'absent': 0}` - no identifier in either record is absent from the bundle.

### Scope

`download scope --check --strict` on the pair: 2 records checked, none is about a dataset its project declares distinct.

### Repair

No Phase 4 checker (pair consistency, grounding, report claims) reported a finding that required a change, so no repair phase ran.

## Claims

| Slot | Action | Reason |
|---|---|---|
| `subpopulations[0].subpopulation_elements_present` | Removed | presence flag not supported for the release's contents (finding 1); the Phase 1 full record carried it, the corrected full record and the re-derived core do not |

The file entry for `audio_quality_metrics.tsv` (finding 2) was one entry of a list that remains populated, not a slot; no slot was emptied by that correction. The direct-collection entry (finding 8) is an addition from the bundle, not a relocation.

## Semantic review

- File collections in the full record against distributions in the core (the pair checker's warning): 3 collections and 11 files in the full record, 14 distributions in the core, each matched by identifier; names, paths, descriptions and the TSV format and media type of the two tab-separated files are the same on both sides, and the nine Parquet files carry no format on either side because the file format vocabulary has no Parquet term - reviewed: consistent
- Total file count and total size against the entries beneath them: neither record states a total file count, a total size, a per-collection file count or a per-file size, and the bundle states none; the 11 listed files are the ones the sources name with a folder, and the JSON data dictionaries, `audio_quality_metrics.tsv` and the unnamed phenotype and metadata files are described in prose only - reviewed: consistent
- Dialect and the tabular flag against the files: no file states a dialect and the core derives none; the tabular flag is true in both records and the listed files are Parquet (stated as column-oriented) and tab-separated files - reviewed: consistent
- Historical against current release: the top-level version, date, DOI slot, citation, counts and file descriptions are those of version 1.1.0; version 1.0.0 appears only in the version list, the release dates and the version notes, where it is labeled as the earlier release - reviewed: consistent

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE_PEDIATRIC
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1 --project VOICE_PEDIATRIC --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c '<grounding check_run program from the playbook>'
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC --check --record <full> --record <core> --strict
```

One command was refused for its spelling and re-run correctly: `download priority` does not take its own `--manifest` option, so the manifest was passed through the root option.

## Final results

| Check | Result |
|---|---|
| Full record, schema validation (class `Dataset`) | No issues found |
| Full record, ontology term validation | Validation passed |
| Core record, schema validation (class `CoreDataset`) | No issues found |
| Core record, ontology term validation | Validation passed |
| Pair consistency | PASS, 79 schema-identical slots, 1 semantic-review warning, 0 errors |
| Grounding | grounded 1, minted fragment 21, absent 0 |
| Report claims against the records | 1 claim checked, 0 unnamed, 0 findings |
| Scope check (strict) | in scope |
| Receipt check (strict), final bytes | chunks 13/13 reviewed, snippets 348/348 verified, slots 306/306 with a receipt (34 exempt) |

Informational, not a quality gate: the full record has 43 populated top-level slots in 711 lines; the core record has 41 populated top-level slots in 568 lines. Full record md5 `222c67f963ed0b937a51f8955375689b`; core record md5 `eb67f65959ef80c0e5316c094439c4ba`.

Limits of what was checked: the receipt validator establishes that every snippet is in its chunk and every populated receiptable slot has a receipt; it does not establish that a snippet supports the value it sits under, or that a chunk marked as holding nothing relevant held nothing. 21 verified snippets share no token with their value (booleans, enumeration values, format names and composed labels); these rest on the judgment recorded in this report, not on the validator.
