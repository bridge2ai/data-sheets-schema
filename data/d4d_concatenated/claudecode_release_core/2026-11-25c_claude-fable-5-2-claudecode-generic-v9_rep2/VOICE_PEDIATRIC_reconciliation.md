# VOICE_PEDIATRIC reconciliation report

- Version label: 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2
- Method: claudecode_release
- Mode: four-phase project agent, generic-v9 prompt, BASELINE arm (input documents only)
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). No sampling setting
  was inferred from the prompt, the model name or an effort level.
- Source bundle: data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt
  (bundle_md5 0350223711484a63c21b2dd57af6f4c9, 13 chunks, 2866 lines)
- Chunk manifest: data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml
- Source manifest: data/preprocessed/source_manifest.yaml
- Full record: data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d.yaml
- Core record: data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d_core.yaml
- Coverage receipt: data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_coverage_receipt.yaml

## Referent

The record describes the Bridge2AI-Voice Pediatric Dataset, release 1.1.0
(DOI 10.13026/h995-bt35), which is the referent the source manifest declares
for this project. The record's own id is the release DOI as a CURIE; the
project-level DOI the page gives as "DOI (latest version)", 10.13026/mf9s-5r03,
is recorded under version access. Both records hold to this referent.

The manifest declares the adult Bridge2AI-Voice dataset related but distinct,
to be expressed through related datasets. It is recorded there once, as a
dataset the pediatric page points to. Five of the six sources in the bundle
(the Bridge2AI Voice Data Acquisition protocol, the project documentation,
the NIH RePORTER page, the Data Transfer and Use Agreement template and the
documentation repository README) are about the wider project and its adult
dataset. A value from them was kept only where its passage is about the
pediatric cohort, about a named person, or about the project as a whole.

## Phase 1 - full generation

All 13 chunks were read with the file-reading tool in manifest order and
receipted. Chunks c009 and c010 were read in one window and their two entries
were written together, directly after that read and before chunk c011.
Dispositions: 10 chunks extracted (c002 to c011), 3 chunks nothing_relevant
(c001 preamble, c012 closing agreement clauses, c013 documentation repository
README).

Corrections made before Phase 2, all to this run's own files:

- Validation: the first schema validation rejected the publication date
  because the date-time form requires a UTC offset. The value was rewritten
  with the offset the schema's description prescribes; the source states the
  date only ("Published: May 1, 2026"), so the time and offset carry no
  information. One fix-and-revalidate loop.
- Receipt addressing: the first strict receipt check passed its floors and
  reported 368 of 375 receiptable leaves covered. The seven uncovered leaves
  were three scalar lists receipted by index instead of at the list path
  (keywords, available versions, IRB approval statements) and four leaves
  with no receipt (the funder name, the privacy entry's name, and the
  sensitive-elements entry's name and details). The list receipts were
  re-addressed and the four receipts added from chunks c002 and c003. Two
  receipts written while reading were re-addressed to the fields the values
  ended up in: the eligibility criteria (description of the sampling entry,
  not its strategies field) and the phenotype usage example (description of
  the phenotype collection, not a file entry).

Judgment calls in Phase 1 that a reader should know about:

- The usage notes load a phenotype file named demographics.tsv. The same
  usage notes load torchaudio_spectrogram.parquet, where the data description
  names torchaudio_spectrograms.parquet, so an example file name is not
  treated as a file listing. No file entry was created for demographics.tsv;
  the example is mentioned in the phenotype collection's description.
- Format for the parquet files is left empty: the schema's file format
  enumeration has no Parquet value. Parquet is recorded as a distribution
  format, whose field is a string.
- Collection type is left empty for all three file collections: no passage
  classifies them in the enumeration's terms.
- Principal investigator is populated for Yael Bensoussan and Olivier
  Elemento. The designations come from passages about the wider project (the
  documentation's "co-principal investigators for the project", the protocol's
  principal investigator line, the NIH RePORTER principal investigator line),
  and the pediatric page states that this project funded the dataset. The
  entries carry a caveat saying so.
- Affiliations are populated for 27 of the 121 creators, each from a passage
  naming that person. Three people the protocol's first-page table appears to
  place under an institution are handled as follows: Anais Rameau and Olivier
  Elemento are affiliated from the protocol's Table 4 and the documentation,
  which name the institution on their own rows; Alexander Gelbard has no
  affiliation recorded, because the only passage is a continuation line whose
  institution cell the extracted text does not preserve.
- The documentation writes three names differently from the PhysioNet author
  list (Jennifer Sui for Jennifer Siu, Frank Rudzizc for Frank Rudzicz, Don
  Bolser for Donald Bolser). The author-list spelling is the recorded name.
  The affiliation of Jennifer Siu and of Donald Bolser rests on the
  documentation alone and each entry carries a caveat; Frank Rudzicz is also
  affiliated by the protocol under the author-list spelling.
- Jordan Lerner-Ellis carries two affiliations, Mount Sinai Hospital (protocol)
  and Sinai Health (documentation). The two sources share a rank, so both are
  recorded as stated.
- The grant recorded is 3OT2OD032720-01S1, the number the dataset page cites.
  The NIH RePORTER page in the bundle is for 3OT2OD032720-01S3 of the same
  core project; it is a different award, not a disagreement, and is noted in
  the funder's caveat.

Not recorded, by decision:

- Publisher. The slot takes an identifier. The page gives PhysioNet an RRID,
  whose prefix the schema does not declare, and states no other identifier
  or root URL for PhysioNet.
- Language, tabular flag, de-identification, compensation, collection
  timeframe, update plan, retention, maintainers, existing uses. The bundle
  states these only for the adult dataset or the PhysioNet platform, or
  states an eligibility criterion (English proficiency) rather than the
  dataset's language.
- The protocol's consent, assent, withdrawal and data-handling procedures.
  The protocol is the University of South Florida single-IRB protocol and
  states that the Canadian institutions, SickKids among them, apply for a
  separate research ethics board; the pediatric page states approval by the
  Research Ethics Board at the Hospital for Sick Children.
- The agreement template's terms. Its data description is the
  Bridge2AI-Voice dataset in general and its provider is the University of
  South Florida; only its expansion of the DACO abbreviation was used.
- Named validated questionnaires. The documentation's questionnaire table
  has a Pediatrics column, but the extracted text does not preserve which
  column each mark belongs to.
- The PhysioNet footer line about the MIT Laboratory for Computational
  Physiology and its grant numbers, which describe the platform.

## Phase 2 - core derivation

The core was derived by projection from the validated full record with
`derive core`; no model judgment was involved. Derivation facts printed by the
command on the first derivation (full record md5 35652caf58451a2fe2aaaeea86549b9a):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d.yaml", "md5": "35652caf58451a2fe2aaaeea86549b9a"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against CoreDataset ("No issues found").

## Phase 3 - source and provenance audit

Provenance: the only factual inputs read were the declared bundle, the chunk
manifest, the source manifest and the two schema files, plus the repository's
playbook, uniform rules and provenance guard. No previously generated D4D
record, evaluation or reconciliation report was opened. The two output
directories were listed by name only, to confirm that no VOICE_PEDIATRIC
artifact existed under this label before the run.

Schema and term validation of the full record were re-run at the start and
end of the audit and passed.

Findings, counted from the entries below: 4 in total (1 medium, 3 low). All
four led to a change in the full record.

1. Low, wording beyond the source. The description under at-risk
   populations called the participants "children and adolescents". The
   bundle states the inclusion criterion (2 to 18 years of age) and calls the
   cohort pediatric; "adolescents" is not in it. Reworded to what the page
   states. Chunk c002.
2. Low, interpretation in place of the source's words. The description of
   sparc_pitch.parquet said the algorithm differs from "the torchaudio
   pitch". The page says "a different algorithm than before" and does not
   name what "before" is. Restored to the page's wording. Chunk c002.
3. Medium, structural assertion stated more firmly than the source.
   audio_quality_metrics.tsv is listed under the features collection, and
   the collection's description said the folder "holds" it. The page names
   the file in its paragraph on the contents of the features folder,
   directly after static_features.tsv, without restating the folder. The
   file stays under features on that reading; the collection description now
   says only that the page also names the file, and the file entry carries a
   caveat stating the basis. Chunk c002.
4. Low, supported omission. The page asks users to include the standard
   citation for PhysioNet and gives it with a DOI link. This was not in the
   Phase 1 record. Added as a second dataset-level external resource, with
   two receipts in chunk c002. It is a new addition from the bundle, not a
   value moved from elsewhere in the record.

Checks that produced no finding:

- Counts are paired with their units as the source states them: 23,533
  recordings, 300 participants, and the per-file element counts (n=23533 or
  n=23532) quoted in each file's description. No figure in the record is
  derived by arithmetic.
- No availability, privacy or de-identification claim is stated more
  strongly than its passage. Raw audio access via Synapse is recorded with
  the page's future tense ("will be made available"). No de-identification
  method or identifiability flag is recorded, because the bundle's
  de-identification text is about the adult dataset. The privacy entry
  records only the manual check for unconsented speakers and PII that the
  release notes state for version 1.1.
- Enumerations: relationship type (references), confidentiality level
  (restricted, from "This is a restricted-access resource"), the two
  identifier-typed variables (from "a unique identifier for ...") and file
  type, format and media type read from file names. No other enumeration
  slot is populated.
- Identifiers: every identifier for something outside the dataset is one
  the bundle states (the two DOIs, the Synapse URL, the b2aiprep repository
  URL, the adult dataset's PhysioNet URL). No ORCID or organization
  identifier is recorded; the bundle states none.

After the four corrections the full record was re-validated (schema and
terms, both clean) and the strict receipt check re-run: 13 of 13 chunks
reviewed, 334 of 334 snippets verified, 378 of 378 receiptable leaves with a
receipt, 31 exempt.

## Phase 4 - re-derivation, checks, report

The core was re-derived from the corrected full record (full record md5
f38e03f05d0fbb087dac925561ab90ce), first without and then with
`--phase4-complete` once the checks below had run. The second derivation
printed the same derivation facts as Phase 2 with the new md5 and validated
("No issues found").

- Pair consistency: PASS, 79 schema-identical slots, projected slots
  resources, per-record slots conforms_to_class and conforms_to_schema. One
  warning, semantic-review-required on file collections and distributions
  (14 deterministic matches: 3 at collection level, 11 at file level; no
  unmatched core distribution).
- Identifier grounding: 2 grounded, 21 minted fragments, 0 absent.
- Scope check (strict): 2 records checked, none is about a dataset the
  project declares distinct.
- Schema validation: full record clean against Dataset, core record clean
  against CoreDataset.
- Term validation: both records passed.
- Receipt check (strict): passed, figures as given at the end of Phase 3.

No checker finding required a change, so no repair phase ran. The reconcile
step ran once (one re-derive and re-check pass; the second derivation only
added the completion header line).

## Claims

No slots were removed.

## Semantic review

- `file_collections` and `distributions` (the pair checker's warning): the
  three collections and eleven files in the full record each appear once in
  the core distributions with the same id, name, path and description; the
  core entries drop only the fields the core class does not share. reviewed: consistent
- Counts and sizes against the entries beneath them: neither record states a
  total file count, a total size, a per-collection file count or a
  per-collection size, and the bundle states none; there is no total to
  compare with the entries. reviewed: consistent
- Dialect and tabular flag against the files: no file states a dialect, so
  the core derives none, and neither record sets the tabular flag. reviewed: consistent
- Historical versus current release: every value in the referent's own slots
  describes release 1.1.0. Release 1.0.0 appears only as an earlier version
  under version access and distribution dates, and the documentation's
  statement about the pediatric dataset v1.0 is recorded there as a
  statement about that version. reviewed: consistent
- Scope of each kept value: the values taken from the five project-wide
  sources (creator affiliations and roles, the principal investigator
  designations, the funder description, the access review steps, the
  pediatric task list, the conversion to BIDS and the b2aiprep license) were
  re-read against the passages behind them; each passage is about the named
  person, the pediatric cohort or the project as a whole, and none is a
  statement about the adult dataset. reviewed: consistent

## Files changed

- Full record: written in Phase 1; one validation fix before Phase 2; four
  Phase 3 corrections.
- Coverage receipt: written chunk by chunk in Phase 1; addresses corrected
  and receipts added before Phase 2; two receipts added in Phase 3 for the
  back-ported external resource.
- Core record: derived in Phase 2; re-derived twice in Phase 4. Never edited
  by hand.
- This report.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE_PEDIATRIC
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project VOICE_PEDIATRIC --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "<grounding check_run program from the playbook>"
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC --check --record <full> --record <core> --strict
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

One command was refused by its own argument parser and not by policy:
`download priority` does not take `--manifest` after the subcommand, and was
re-run with the root `--manifest` option as the launch instruction allows.
`receipts check --initial-structure` was tried once to list uncovered leaves
and exited with a usage error (it needs a native shared selection); nothing
was written by it.

Run after this report was written, and therefore not described above: the
report-claims check, the live provenance record, the receipt check with
`--write`.

## Final results

- Full record: valid against Dataset; term validation passed; 44 top-level
  slots populated; 820 lines (informational only).
- Core record: valid against CoreDataset; term validation passed; 42
  top-level slots populated; 657 lines (informational only); header carries
  `# Sources:` naming the same-run full record and
  `# Phase 4 reconciliation: completed`.
- Pair consistency: PASS with the one expected semantic-review warning,
  reviewed above.
- Reconciliation outcome: 4 audit findings, all corrected in the full
  record; no slot removed; no repair phase.
- Limits: the temperature of the run is unknown. The receipt check does not
  test that a chunk marked nothing_relevant held nothing, nor that a verified
  snippet supports the value it sits under; those remain review work.
