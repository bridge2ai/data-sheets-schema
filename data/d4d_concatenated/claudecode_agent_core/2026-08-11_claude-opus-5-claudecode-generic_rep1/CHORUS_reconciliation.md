# CHORUS full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep1

- Runtime: Claude Code; Provider: Anthropic; Model: claude-opus-5
- Mode: four-phase project agent, generic prompt condition
- Arm: BASELINE (input documents only)
- Declared input bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- Manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The record is about the **CHoRUS dataset**, identified
as `https://chorus4ai.org/`, matching the manifest `scope:` declaration for CHORUS
(`referent: CHoRUS dataset`, `referent_id: https://chorus4ai.org/`,
`related_but_distinct: []`). No source in the bundle gives a DOI or a dataset version
identifier, so the project site URL is the identifier, as the manifest anticipates.

The bundle also describes two entities that are *not* the referent and were kept out of
the dataset's own slots: the NIH award OT2OD032701 (recorded only under `funders`, as
the funding of the dataset) and the AIM-AHEAD Bridge2AI for Clinical Care Training
Program (recorded only where it bears on the dataset — as an existing use, and as the
access route through which registration, licensing agreement and `.edu` email
requirements are stated). Program-only facts — stipend, citizenship and visa
eligibility, application deadlines, curriculum, mentorship — were not imported into the
dataset record.

The record holds the same referent in both files: `id`, `name`, `title` and
`description` are byte-identical across full and core.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D was read. The complete set of factual inputs was: the declared
bundle, `source_manifest.yaml` (scope block and the CHORUS source list), the full and
core LinkML schemas, and — in Phase 2 only — the same-run Phase 1 full record at the
label `2026-08-11_claude-opus-5-claudecode-generic_rep1`. No file under
`data/d4d_concatenated/` other than this run's own two outputs was opened, and no
`*_crate_d4d.yaml` or evaluation artifact was consulted. Structure was derived at
runtime from `SchemaView` over `Dataset` and `CoreDataset` rather than from any example
record; enum values (`CRediTRoleEnum`, `LimitationTypeEnum`, `CreatorOrMaintainerEnum`,
`DataUsePermissionEnum`) were read from the schema, and nested-object shapes were probed
against the validator before writing (this is how `principal_investigator` and
`contact_person` were established as non-inlined string references rather than embedded
`Person` objects).

### Source disagreements, represented rather than resolved

The four sources are of different dates and authority, and they disagree. In each case
both statements are carried with their attribution instead of one being silently chosen:

1. **Admission count.** Webinar (2025-09-09): "as of August 2025, covers 14 different
   hospitals with over 45K unique admissions". Website: "Current Released Dataset —
   50,000 patient admissions from ICU, PICU, and NICU". Recorded as two separate
   `instances` entries; the exact figure (50,000) carries `counts`, the "over 45K"
   figure carries none because it is a bound, not a count. The conflict is named in
   `instances[0].source_caveats` and in the top-level `source_caveats`.
2. **Imaging volume.** Webinar: "Imaging – currently 1000 images available with de-id in
   process for larger cohort". Website: "7,642 Admissions with Radiology Data". These
   are different units as well as probably different dates; both are recorded as
   separate instances and the incommensurability is stated.
3. **Anticipated vs released.** Website distinguishes "Anticipated Final Dataset"
   (100,000 admissions, 9 modalities, 14 hospitals) from the current release; the NIH
   abstract speaks of "more than 100,000 critically ill patients". The anticipated
   figure is recorded as its own instance labelled as anticipated, and as a
   `known_limitations` scope limitation, so a reuser cannot read the target as the
   holding.
4. **License.** The GitHub README's "This project is licensed under the MIT License"
   scopes the GitHub *software* project in that document; repositories carry MIT and
   Apache-2.0. No source licenses the data. The top-level `license` slot is therefore
   **left empty**, MIT is recorded only inside the GitHub `external_resources` entry,
   and `license_and_use_terms.source_caveats` says why. Populating `license: MIT` would
   have been the single most consequential wrong inference available in this bundle.

### Correction made during the audit

One claim written in Phase 1 did not survive checking and was corrected in the full
record before Phase 4:

- `distribution_formats[format_omop].description` originally read "the published
  metadata schema is the OMOP schema, with extensions for nursing flowsheets". The
  webinar data-type table is a slide whose rows do not survive PDF text extraction in
  aligned form. The extracted column contains five OMOP-family entries of which the
  fifth reads "Yes (OMOP schema with extensions)"; the positional reading would assign
  it to *Diagnoses*, while the semantically plausible reading assigns it to *Nursing
  flowsheets*. The bundle does not determine which. The description now states that one
  of the five OMOP rows is listed as "OMOP schema with extensions" without assigning it,
  a slot-level `source_caveats` explains the extraction problem, and clause (8) was
  added to the top-level `source_caveats`. Full was corrected first and core was then
  re-synchronized from it.

The column assignments that *are* determinate — every data type Controlled; metadata
"Yes" for the OMOP types and for waveform telemetry, "Planned" for clinical notes,
imaging and EEG — were retained.

### Other audit checks

- **Numbers and identifiers re-read against the bundle**: application ID 10472824,
  project number 1OT2OD032701-01, core project OT2OD032701, FY2022, award amount
  5,880,300, project period 2022-09-01 to 2026-11-30, 50,000 / 1.6 billion / 7,642 /
  23 Tb / 100,000 / 9 modalities / 14 hospitals / 20 centers / 60+ members / 28
  repositories / 37 followers / 1,000 images / up to 30 trainees. All verbatim.
- **Currency and units not asserted**: the award amount is recorded without a currency
  symbol because the source states none, and "23 Tb" is recorded as written with a
  caveat rather than converted to `total_size_bytes`, because terabits and terabytes
  differ by a factor of eight and the source does not say which is meant.
- **Verbatim transcription of a probable typo**: the program manager address is recorded
  as `cmccrary@mgh.havard.edu` exactly as the website gives it, with the anomaly noted
  in `source_caveats` rather than silently repaired.
- **Historical source handled as historical**: the GitHub organization overview is a
  manual PDF capture dated 2025-11-14, selected by the manifest as
  `source_type: historical documentation`. Its repository inventory, follower count and
  "updated" timestamps are attributed to that capture date wherever they appear.
- **Absence recorded as absence**: no IRB, ethics board, protocol number, consent
  procedure, retrospective collection window, release date, version, DOI, retention
  policy, update cadence, data dictionary, discouraged use or prohibited use appears in
  any source. Those slots are omitted rather than filled, and the omissions are named in
  `ethical_reviews.source_caveats`, `human_subject_research.source_caveats`,
  `collection_timeframes`, `updates` and `known_limitations[limitation_scope_of_sources]`.
- **Judgements that are inferences, declared here**: `credit_roles: [supervision]` on the
  six named leadership-team members maps the slide title "Bridge2AI CHoRUS Leadership
  Team" onto the CRediT definition of supervision; `direct_collection.is_direct: false`
  reads the repeated description of retrospective extraction from hospital systems, and
  carries its own `source_caveats` saying so; `acquisition_methods.was_directly_observed:
  true` reads the table's "documentation by providers" and bedside-monitor capture. No
  other boolean was set from silence — `is_deidentified.identifiable_elements_present`,
  `sampling_strategies.is_representative` and `is_tabular` were all left unset because
  the sources characterize the pipeline, not its completed state.
- **Shape audit**: every populated slot was checked against its induced range. No prose
  sits in a list slot, no enum value outside the schema is used, no commentary is
  embedded in a name, identifier or affiliation, and evidence commentary is confined to
  `source_caveats` (top level and on six nested objects). `notes` is unused in both
  files: nothing in this bundle needed a home that `description` could not provide.

Both records re-validated clean after the correction.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView` over `Dataset` and `CoreDataset`;
no hand-written field list was used.

- **Schema-identical shared slots: 78.** All 78 have identical presence and deeply
  identical parsed YAML content in both files, including every narrative field. Core
  condenses, paraphrases, reorders and omits nothing. 45 of the 78 are populated; the
  remaining 33 are absent from both.
- **Projected slots: `resources`** (`Dataset` in full, `CoreDataset` in core). Absent
  from both records: the sources describe modalities and standards, not sub-datasets
  with their own identity, so no resource was invented to fill the projection.
- **Full-only slots populated in full and therefore not present in core (5):**
  `relationships`, `splits`, `direct_collection`, `participant_privacy`,
  `third_party_sharing`. These are not in `CoreDataset` at all, so their absence is the
  schema's answer, not a loss. Their content was deliberately *not* smuggled into a
  neighbouring core slot: the privacy narrative was not folded into `is_deidentified`,
  and the controlled-access/third-party-sharing narrative was not folded into
  `license_and_use_terms`, because both of those are schema-identical shared slots and
  any addition would have broken deep identity while creating a fact in core that full
  does not carry.
- **Core-only slots (2): `distributions`, `dialect` — both left empty, deliberately.**
  Full has no `file_collections` to project into `distributions`, and the bundle
  supports none: there is no file listing, no download URL, no file count, no checksum
  and no byte count anywhere in the four sources, because the data are not distributed
  as downloadable files but accessed inside a provisioned cloud enclave. `dialect`
  (delimiter, header, quoting) is likewise unstated. The per-modality standards that a
  reader might expect here are carried in `distribution_formats`, which is shared and
  identical in both files.
- **Related-content semantic review.** With `file_collections`/`distributions` both
  empty and `total_file_count`/`total_size_bytes` unset, the quantitative
  cross-checks the playbook calls for (file counts and byte totals against
  distribution-level values) have no operands. The checks that do apply were performed:
  the five `distribution_formats` entries agree with the five `raw_data_sources` entries
  on standard per modality (OMOP / OHNLP / DICOM / WFDB / EDF+ and Persyst) and on
  access control (controlled for all five); `conforms_to` names the same standard set;
  the enclave/local-storage split for clinical notes is stated consistently in
  `confidential_elements`, `known_limitations[limitation_notes_not_in_enclave]`,
  `raw_source_clinical_notes` and `raw_sources`; and the released-versus-anticipated
  distinction is stated the same way in `description`, `instances`, `known_limitations`
  and `future_use_impacts`. `is_tabular` is unset in both, consistent with a dataset that
  is part tabular (OMOP) and part waveform and imaging.
- **Historical versus current.** The two admission counts and the two imaging figures are
  represented as dated observations, not as contradictions; nothing in either file
  presents the anticipated 100,000-admission dataset as the current holding.

Result: `PASS: 78 schema-identical slots; projected slots=['resources']`, reported both
with `--sync-core` and on the independent re-run without it. No unresolved contradiction
within or between the two records.

## Provenance record

`record_mode: live`. The record names the input bundle
(md5 `9b2ef4b65d67957f79362266cab0bc7a`, 35,920 bytes, verified identical to the bytes
consumed), the manifest, both schema hashes, the three playbook files, the repo commit,
software and hardware.

- **Prompt.** `src/download/prompts/d4d_generic_arm_prompt.md` is recorded as the prompt
  file, and the instruction as sent is recorded as `prompts.request`
  (sha256 `87a4bb…945e84`, 4,041 bytes). It was not retyped: it was produced with
  `d4d prompt render --project CHORUS --label … --condition generic --runtime 'Claude
  Code'` and compared against the launch message received, which it matches.
  `d4d api prompts check --strict` reports all 10 prompt files at their pins, including
  this one, so the run was made under a published version of the generic condition.
- **Reasoning effort.** Not recorded. The route this run took does not express effort as
  a model-name suffix and the effort it was launched at is not known to the agent, so
  the field is left absent and the gap is named, per #397. No guess and no "default" was
  written.
- **Residual warning.** `d4d runs check --strict` exits 0 for this run, with one
  non-fatal note: `unverifiable: request hash recorded without the spec that produced
  it`. This is a property of the agentic path rather than of this run — `provenance
  record` accepts the rendered instruction but has no flag for the render spec that
  produced it, which only `d4d api run` writes in-process. The instruction hash is
  therefore recorded and pinned, but cannot be independently re-derived from the record
  alone; re-deriving it requires re-running the render command above.

## Files changed

- Created `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d.yaml` (Phase 1, corrected in Phase 3)
- Created `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d_core.yaml` (Phase 2, synchronized in Phase 4)
- Created this report

## Commands

```bash
# Phase 1 / Phase 3 validation (full)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 validation (core)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>

# Scope
poetry run d4d download scope --project CHORUS
poetry run d4d download scope --check --project CHORUS

# Provenance
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
```

## Results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass — no issues found |
| Full term validation | pass |
| Core schema validation (`CoreDataset`) | pass — no issues found |
| Core term validation | pass |
| Schema-identical shared slots | 78, all deeply identical and identically present |
| Projected slots (`resources`) | absent from both, coverage equal |
| Pair consistency (`--sync-core`, then independent) | PASS both times |
| Scope check | in scope; record does not identify itself as a dataset the manifest declares distinct |
| Populated top-level slots, full | 50 |
| Populated top-level slots, core | 45 |
| Prior-D4D factual reuse | none |
| Corrections made in Phase 3 | 1 (OMOP "with extensions" attribution withdrawn) |
