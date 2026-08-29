# CHORUS reconciliation report

- **Label:** 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic-v6 prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
  (md5 `9b2ef4b65d67957f79362266cab0bc7a`, 1698 lines, 8 chunks)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_d4d_core.yaml`
- **Coverage receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The manifest declares CHORUS's referent as the
**CHoRUS dataset**, `referent_id: https://chorus4ai.org/`, with
`related_but_distinct: []`. The record is about that dataset and uses that URL
as its `id`; the manifest's note that no dataset DOI appears in any CHORUS
source document is borne out — the bundle contains no DOI, ROR or ORCID
anywhere. This choice is held consistently across both records.

Two entities in the bundle are **about** the dataset without being it, and are
deliberately not merged into the referent:

- the **AIM-AHEAD Bridge2AI for Clinical Care Training Program**, which occupies
  most of chunks c003–c005. Its eligibility rules, stipends, application
  deadlines and curriculum are facts about a training program, not about the
  dataset. Only the parts that bear on the dataset — that the program expands
  access to it, and the access conditions it states — are represented, under
  `existing_uses`, `data_governance.access_review_process` and
  `external_resources[0].restrictions`.
- the **CHoRUS GitHub organization** and its repositories, recorded as
  `external_resources[1]` and as the tooling named inside the relevant
  preprocessing, cleaning and collection entries — not as the dataset's own
  content or license.

## Phase 1 — full generation

All 8 manifest chunks were read with the file-reading tool in manifest order,
each chunk's receipt entry written before the next chunk was opened.
`d4d bundle chunk --check --project CHORUS` reported `current` before reading
began.

Receipt outcome: **chunks 8/8 reviewed, snippets 106/106 verified, no findings**
(`d4d receipts check --strict`). One chunk is closed `nothing_relevant` (c001,
the concatenation preamble and table of contents); the other seven are
`extracted`. Chunks c004 and c005 carry a `note` recording that their bulk is
training-program administration rather than dataset fact, so that a reader can
see why two large chunks yielded few extracted pairs.

## Phase 2 — core derivation

`d4d derive core` was run on the validated Phase 1 full record. No model
judgement was involved and the bundle was not an input to this phase. The
command's own output:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_d4d.yaml",
          "md5": "619fdf04bb736accceeeab0de2a489b3"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The md5 above is the corrected full record, from the Phase 4 re-derivation. The
Phase 2 derivation ran against md5 `37cc49b27e902c7f84249f1dd953d1c5`, the
pre-audit full record.

## Phase 3 — source and provenance audit

### Provenance result

No prior generated D4D record was read, searched, or cited. The factual inputs
were the declared bundle, `data/preprocessed/source_manifest.yaml` (scope,
naming and `source_priority` blocks), `data/preprocessed/chunks/CHORUS_chunks.yaml`,
and the two LinkML schemas, read through `SchemaView` for structure. No live web
content was consulted. Nothing under `data/d4d_concatenated/` other than this
run's own label directories was opened.

### Source disagreement resolved by the declared ranking

The bundle contains one substantive conflict.

| Source | Tier | Value |
|---|---|---|
| `project_documentation` (chorus4ai.org) | 2 | "Current Released Dataset **50,000** Patient admissions from ICU, PICU, and NICU" |
| `cohort_2_webinar` (AIM-AHEAD PDF) | 4 | "As of August 2025, covers 14 different hospitals with over **45K** unique admissions" |

`d4d download priority --project CHORUS --decide project_documentation,cohort_2_webinar`
returns `winner: project_documentation`. The tier-2 figure of 50,000 is recorded
in `instances[0].counts`; the webinar figure, the fact that the sources
disagreed, and which was preferred are recorded in `instances[0].source_caveats`
and in the record-level `source_caveats`. The two sources agree on 14
contributing hospitals.

A second apparent conflict is **not** one, and is recorded as such rather than
resolved by ranking: for imaging, the tier-2 source reports "7,642 Admissions
with Radiology Data" and the tier-4 source reports "currently 1000 images
available". These count different units — admissions versus images — so neither
is the other's contradiction and neither is a count of imaging studies.
`instances[8].counts` is therefore left unset and both figures are stated, with
the reason, in that entry's `source_caveats`.

### Corrections made to the full record

Every correction below was applied to the full record only; the core was
re-derived from it in Phase 4.

1. **creators[0].description** — restated the collector entry's
   20-centers/14-acquisition-centers sentence verbatim. Trimmed to the 60+
   members / 20 institutions fact, which is the consortium fact this slot
   carries.
2. **instances[8]** — the entry was named for a modality (`Imaging`) but typed
   and counted in a different unit (`admission with radiology data`, 7642). Its
   type is now "imaging study drawn from PACS", its count is no longer asserted,
   and both source figures with the unit mismatch are stated in its
   `source_caveats`.
3. **instances[9].description** — attributed the released dataset's "23 Tb
   Waveform data" wholly to telemetry, though the source gives it for waveform
   data as a whole and does not break it down between telemetry and EEG. The
   sentence no longer sits in the telemetry entry; the figure remains at dataset
   `description`, where its scope is correct, and the reason is stated in that
   entry's `source_caveats`.
4. **human_subject_research.special_populations** — read "Patient admissions
   from ICU, PICU, and NICU", a population slot holding a unit of record rather
   than people. Rephrased to "Critically ill patients admitted to ICU, PICU, and
   NICU".
5. **missing_data_documentation[0]** — `missing_data_patterns` restated the
   first known-limitation almost sentence for sentence, and `missing_data_causes`
   sat empty while the cause was buried in that prose. Rewritten to state the
   pattern (missingness falls along modality lines), with `missing_data_causes`
   populated from the in-progress pipelines and the by-design local retention of
   clinical notes.
6. **maintainers[0].role** — set to `academic_institution` for a named
   individual, a category the sources do not state. No longer asserted, and the
   gap is named in that entry's `source_caveats`.
7. **maintainers[0].maintainer_details** — carried evidence commentary
   ("transcribed as the source gives it"). The commentary now sits in
   `maintainers[0].source_caveats`, which is the slot for it.
8. **intended_uses[1].usage_notes** — restated its own sibling `examples[0]`. No
   longer present on that entry.
9. **distribution_formats — the five entries' `description` values** — each
   restated the corresponding instance entry's content rather than adding
   anything about the format. Each entry now carries `name` and `format` only,
   which is what the slot asks for.
10. **preprocessing_strategies[0].preprocessing_details** — included
    "transformed using approaches that limit re-identification", which is
    de-identification and was already stated in `is_deidentified` and
    `participant_privacy`. The clause is gone; the receipt pair for that snippet
    was re-pointed to `is_deidentified.method`, and the OMOP standardization
    snippet added for this slot.

No value was back-ported from the bundle in this phase: no source-supported
omission was found that the record lacked. The receipt was edited in place for
the three slot paths corrections 2, 3 and 10 moved (`instances[8].description`,
`description`, `is_deidentified.method`); no second entry was created for any
chunk, and `d4d receipts check --strict` was re-run clean afterwards.

### Deliberate omissions

Recorded here because an absent slot is a decision, not an oversight:

- **`license`** — no license is stated for the dataset. The MIT License in the
  GitHub organization README, and the MIT/Apache-2.0 markings on individual
  repositories, govern that software project. Recording either as the dataset's
  license would be a mis-scoped assertion; the fact and its scope are stated in
  `license_and_use_terms.source_caveats` instead.
- **`doi`, `publisher`, `version`, `download_url`, `citation`** — the bundle
  contains no DOI, no publisher identifier, no version string, no download URL
  and no citation for the dataset.
- **`license_and_use_terms.data_use_permission`** — the sources say "Controlled
  access" and require a signed licensing agreement, but state no DUO permission
  term. Selecting one would be inference.
- **`file_collections`** — the bundle describes storage locations (enclave
  versus local site retention) but names no files, paths, formats-per-file,
  counts or sizes. Emitting `FileCollection` entries would invent structure, so
  the core record correspondingly carries no `distributions`.
- **`known_biases`** — the sources name bias as something the project sets out
  to manage; they do not identify a bias present in the data. The management
  approaches are recorded under `ethical_reviews` and `sampling_strategies`.
- **`ip_restrictions`, `regulatory_restrictions`** — HIPAA and GDPR appear in
  the bundle only as topics of a training curriculum, not as statements about
  this dataset's compliance.
- **Person objects and registry identifiers** — `Person.id` is required by the
  schema, and the bundle supplies no ORCID for anyone. Rather than mint a
  fragment standing in for a person with a real external referent, the six named
  individuals are carried as `Creator` entries with `name` and `affiliations`,
  and `creators[*].principal_investigator` (a scalar reference, not an inlined
  object) is left unset. No ROR, ORCID or DOI appears anywhere in either record.

## Phase 4 — re-derivation, checks, repair

1. Core re-derived from the corrected full record with `--phase4-complete`,
   which wrote the `# Phase 4 reconciliation: completed` header line. The core
   was never edited by hand and `--sync-core` was never passed.
2. Pair consistency: `PASS: 79 schema-identical slots; projected slots=['resources'];
   per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`.
   **No `semantic-review-required` warning was emitted**, because the full record
   carries no `file_collections` and the core therefore carries no
   `distributions`.
3. Schema and term validation re-run for both records after every correction —
   all four clean.
4. Grounding: `{'grounded': 0, 'minted_fragment': 0, 'absent': 0}`. The checker
   tracks ROR, ORCID, DOI and ARK identifiers; the record asserts none, which is
   the correct outcome for a bundle that contains none. **Zero `absent`.** The
   two URLs the record does use as identifiers were confirmed present in the
   bundle by direct search: `https://chorus4ai.org/` (2 occurrences) and
   `https://github.com/chorus-ai` (9).
5. Scope: `d4d download scope --check --project CHORUS` — the record is not
   about a dataset the manifest declares distinct.

No finding from the Phase 4 checkers required a change to the records, so there
is no `repair` phase and no `report_after_repair`. The corrections listed above
all belong to Phase 3's audit of the full record and were applied before the
Phase 4 re-derivation.

## Claims

No slots were removed.

The Phase 3 corrections removed *values from nested entries* — `usage_notes`
from one `intended_uses` entry, `role` from one `maintainers` entry, `counts`
from one `instances` entry, and `description` from five `distribution_formats`
entries. None of these is a slot removed from a record: `counts` and
`description` remain populated on other entries, so claiming them here as
removals would assert something the checker would correctly contradict.

## Semantic review

| Review | Outcome |
|---|---|
| `file_collections` ↔ `distributions` (the pair checker's only semantic warning) | The checker emitted **no** warning: the full record has no `file_collections` and the core no `distributions`, because the bundle names no files, paths, per-file formats, counts or sizes. Checked that this absence is a property of the evidence and not a dropped projection — **reviewed: consistent**. |
| `total_file_count` / `total_size_bytes` against the entries beneath them | Both omitted. The only size figure in the bundle is "23 Tb Waveform data", which covers waveform data alone and so cannot serve as a dataset total; there is no file count anywhere. Setting either from a partial figure would misstate it. **reviewed: corrected** — the 23 Tb figure was moved out of `instances[9].description`, where it had been attributed to telemetry alone, to dataset `description` where its scope matches the source. |
| Instance `counts` against the entries and figures beneath them | Three counts are asserted: `instances[0].counts: 50000` (admissions, tier-2 source, preferred over the tier-4 45K), `instances[1].counts: 1600000000` (1.6 billion OMOP rows), and none for imaging. Checked each against its unit and its source, and that the dataset `description` repeats the same three figures with the same values. **reviewed: corrected** — the imaging entry no longer asserts a count of 7642, because that figure counts admissions with radiology data, not imaging studies, and so did not match its own entry's declared instance type. |
| `dialect` and `is_tabular` against the files | `dialect` is a `File`-level slot; the record has no `File` entries, so the derivation correctly derived none. `is_tabular` is omitted deliberately: the dataset spans tabular OMOP domains and non-tabular imaging, waveform and note data, so neither `true` nor `false` is a true statement about it. **reviewed: consistent**. |
| Historical versus current release read as the current one | The bundle describes two states — a "Current Released Dataset" (50,000 admissions, 1.6 billion OMOP rows, 7,642 admissions with radiology data, 23 Tb waveform) and an "Anticipated Final Dataset" (100,000 admissions, 9 modalities, 14 hospitals). Checked that every asserted count is the *current* figure and that the anticipated figures appear only where labeled as anticipated: `description`, `instances[0].description`, `known_limitations[1]` and `updates.update_details`. Also checked that the tier-5 GitHub snapshot (dated 2025-11-14) and the tier-4 webinar (August 2025) are not read as current where the tier-2 documentation speaks: the "1000 images" and "EEG extraction in process" statements are attributed to the webinar in the text that carries them. **reviewed: consistent**. |
| Repeated facts across slots | 14 contributing hospitals, 20 academic centers, the OMOP CDM, controlled access, the enclave/local-retention split, and the licensing agreement each appear in more than one slot. Checked that every occurrence states the same value and that none is a restatement filling a slot it does not answer. **reviewed: corrected** — corrections 1, 8, 9 and 10 above removed four such restatements. |
| Modality table read out of a degraded PDF extraction | The webinar's data-type/standard/access/metadata table survives PDF extraction with its column alignment broken. Checked each pairing the record asserts against the unambiguous text: Demographics→OMOP, Clinical notes→OHNLP, Imaging→DICOM, Waveform telemetry→WFDB, Waveform EEG→EDF+/Persyst are all recoverable from adjacent text; per-modality metadata status is not, and is not asserted. Recorded in the record-level `source_caveats`. **reviewed: consistent**. |

## Commands run

```bash
poetry run d4d bundle chunk --check --project CHORUS
poetry run d4d download scope --project CHORUS
poetry run d4d download priority --project CHORUS
poetry run d4d download priority --project CHORUS --decide project_documentation,cohort_2_webinar
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 --project CHORUS --strict
poetry run d4d derive core --full <full> --out <core>
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run d4d download scope --check --project CHORUS
# grounding check via data_sheets_schema.grounding.check_run
# report-claims check via data_sheets_schema.report_claims.check_report
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
```

## Final results

| Check | Result |
|---|---|
| Full record — schema validation | No issues found |
| Full record — term validation | Validation passed |
| Core record — schema validation | No issues found |
| Core record — term validation | Validation passed |
| Pair consistency | PASS, 79 schema-identical slots, 0 warnings |
| Coverage receipt (`--strict`) | chunks 8/8 reviewed, snippets 106/106 verified, 0 findings |
| Grounding | 0 grounded, 0 minted_fragment, **0 absent** |
| Scope check | in scope |
| Full record top-level slots | 47 |
| Core record top-level slots | 45 |

Top-level slot counts are informational metadata, not a quality measure.
