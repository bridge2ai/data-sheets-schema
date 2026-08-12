# AI_READI full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep1

Run label: `2026-08-11_claude-opus-5-claudecode-generic_rep1`
Arm: BASELINE (input documents only)
Mode: four-phase project agent, generic prompt
Runtime / provider / model: Claude Code / Anthropic / claude-opus-5

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d_core.yaml`
- This report

Declared inputs actually read, in full:

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 sources, 6,220 lines)
- `data/preprocessed/source_manifest.yaml` (scope block and the AI_READI source list)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`, resolved
  with `SchemaView`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`
- `src/data_sheets_schema/d4d_pair_consistency.py` (to derive the Phase 4 rules)

## Referent

`Dataset` admits one referent. The referent chosen is **the AI-READI dataset,
`https://doi.org/10.60775/fairhub.3`** — the identifier the manifest's `scope:` block
declares for this project and the DOI of release 3.0.0, the current accessible release.

The bundle documents three releases of that one dataset (1.0.0 / `fairhub.1`, 2.0.0 /
`fairhub.2`, 3.0.0 / `fairhub.3`), and the manifest states that the earlier two are
earlier releases of the same dataset rather than separate datasets. The record therefore
describes release 3.0.0 in its top-level identity, size, count and date slots, and
carries the earlier releases only under `version_access.versions_available` and
`related_datasets` (`is_new_version_of`). Both records hold that choice identically.
`d4d download scope --check --project AI_READI --strict` reports the record in scope.

The FAIRhub "Mini Version" (`data.child: 4`) is **not** represented. The bundle mentions
only "A smaller version is available for pipeline development…" and the integer `4`; no
identifier for it appears in the bundle, so `related_datasets` would have had to invent
a `target_dataset`. Omitted rather than guessed.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior D4D record of any arm, label or date was read, opened, grepped or consulted.
Nothing under `data/d4d_concatenated/` was read except the two files this run wrote, and
nothing under `data/ro-crate_packages/` was touched at all. Structure was derived from
the two schemas with `SchemaView`, not from any example record; no `d4d:docExample`
value was copied. The core record's only generated-YAML input is the same-run full
record at the exact label path above.

### Grounding check

Every URL, DOI, ORCID, ROR, ISO date, grant number and 3-or-more-digit figure in the
full record (164 distinct tokens) was matched against the bundle and manifest. Eight did
not match verbatim; all eight are normalisations of text that is present, and each was
checked by hand:

| token | how it appears in the bundle |
|---|---|
| `2022-12-20` | healthsheet: "The initial IRB approval … was received on December 20, 2022" |
| `2024-05-03` | FAIRhub version list "May 3, 2024"; README "5/3/2024" |
| `2024-11-08` | FAIRhub version list "Nov 8, 2024" |
| `https://aireadi.org/goals/data-sharing` | BMJ Open, broken across lines by PDF extraction as `https://aireadi.` / `org/goals/data-sharing` |
| `https://doi.org/10.60775/fairhub.1` | bundle gives the bare DOI `10.60775/fairhub.1`; resolver prefix added for consistency with the record's own `id`, which the manifest declares in that form |
| `https://doi.org/10.60775/fairhub.2` | as above |
| `https://w3id.org/bridge2ai/data-sheets-schema` | not a dataset fact — it is the `id` of the schema this record is written in, read from the schema file |

Cross-figure checks that hold inside the bundle and are reproduced in the record:

- The nine datatype directory `numberOfFiles` values sum to 356,334; the declared total
  is 356,343, and the dataset root carries exactly 9 metadata files. Consistent.
- The nine directory `size` values sum to 3,815,969,360,064 against a declared
  3,815,969,779,678 — a 419,614-byte difference, the same 9 root metadata files.
- Split totals: 1,576 + 352 + 352 = 2,280; race/ethnicity 380+545+519+836 = 2,280; sex
  951+1,329 = 2,280; diabetes status 776+560+686+258 = 2,280.
- Version participant counts: 204 (v1) + 863 (year 2) = 1,067 (v2); 1,067 + 1,213
  (year 3) = 2,280 (v3). The healthsheet and README agree.

### Source disagreements — represented, not resolved

Each of these is recorded in the record itself, in the `source_caveats` of the object it
affects, rather than silently decided:

1. **Managing organization / PI affiliation.** The FAIRhub structured metadata names
   "Washington University in St. Louis" (ROR `01yc7t268`) as managing organization, lead
   sponsor, and affiliation of Aaron Lee and Cecilia Lee. The Nature Metabolism author
   list places both at the University of Washington, Seattle (corresponding address
   `leeay@uw.edu`), NIH RePORTER records the awardee as UNIVERSITY OF WASHINGTON, and the
   same FAIRhub record lists the University of Washington separately as a study location
   under ROR `00cvxb145`. Both statements are transcribed; neither is preferred.
2. **Licence version.** The licence text captured as a source is AI-READI-LICENSE-v1.0
   (Zenodo 10642459), cited by the 2024 Nature Metabolism comment. The FAIRhub record and
   README for release 3.0.0 name a licence at `https://doi.org/10.5281/zenodo.17555036`,
   described in the FAIRhub rights block as "AI-READI custom license v2.0"; the FAIRhub
   landing page labels it "Health Data License". The v2.0 text is not in the bundle, so
   the clause-level terms recorded are explicitly those of v1.0, and the top-level
   `license` names v2.0 with its DOI.
3. **De-identification.** Nature Metabolism describes the public set as stripped of PHI
   via the HIPAA Safe Harbor method — an active step. The FAIRhub dataset description
   records `deIdentType: NoDeIdentification`, on the ground that no identifiers were
   collected in the first place. Both appear in `is_deidentified`.
4. **Target enrolment.** 4,000 (BMJ Open, Nature Metabolism, FAIRhub study description),
   "4,000+" (NIH RePORTER), 4,600 (UW IRB protocol form, whose own subject table
   nonetheless sums to 4,000).
5. **Project end date.** Enrolment to 30 November 2026 (BMJ Open); collection window
   2022–2026 (Nature Metabolism); anticipated completion 2027-01-01 (FAIRhub study
   description); funded project period ending 2025-08-31 (NIH RePORTER). Four statements
   about four different things, recorded together.
6. **Collection start.** 18 July 2023 (BMJ Open, enrolment began) versus 2023-07-19
   (FAIRhub `dateType: Collected` and study start). The FAIRhub value is used in
   `start_date` because it is the one attached to this release; the one-day discrepancy
   is named.
7. **Grant number spelling.** The healthsheet writes `OT2ODO32644`; every other source,
   including NIH RePORTER and the FAIRhub funding reference, writes `OT2OD032644`, which
   is what the record carries.
8. **Sampling.** The recruitment design is an explicitly stratified, non-random sample of
   three health systems' patient populations; the healthsheet composition section says
   "the dataset contains all possible instances". Both are true of different things
   (selection into the study versus inclusion in the release) and both are recorded.
9. **Release cut-offs.** BMJ Open, written before release 2.0.0 existed, says data
   through 31 July 2024 were released in November 2024. The FAIRhub records give the
   release dates used.
10. **Demographic sub-populations.** The healthsheet answers "No" to whether the dataset
    identifies demographic sub-populations; the README publishes per-group counts and the
    controlled tier carries the fields. The counts are recorded with that tension named.

### Deliberate omissions

Slots left absent because the bundle does not support them: `resources`, `subsets`,
`parent_datasets`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `errata`, `variables`, `download_url`, `created_on`,
`last_updated_on`, `was_derived_from`, `compression`, `dialect` (core).

Three are worth naming:

- **`errata`** — the healthsheet's erratum question has an empty response. An empty
  answer is not a statement that there is no erratum, so nothing is written.
- **`variables`** — the only per-variable inventory in the bundle is BMJ Open Table 2.
  PDF extraction separates its columns (analyte, unit, reference range, rationale) into
  non-adjacent blocks, so units and ranges cannot be attached to the right analyte
  without guessing. Recorded as a dataset-level `source_caveats` instead of a fabricated
  variable list.
- **`credit_roles`** — the bundle's contributorship statements are ICMJE authorship
  criteria and a Nature-style role grouping, both about the papers rather than the
  dataset. Mapping them onto the CRediT enum would be inference.

### Shape corrections made during Phase 3

Three shape defects in the Phase 1 draft were found by the Phase 3 shape audit and fixed
in the full record before Phase 4 (and therefore propagated to core):

1. `distribution_formats[0].media_type` held a prose list of four media types plus a
   sentence. `media_type` is single-valued and means one IANA media type. Removed; the
   four types moved into `description`, with `format` reduced to the layout standard
   ("Clinical Dataset Structure (CDS) v0.1.1 directory tree") and the absence of a single
   applicable media type stated explicitly.
2. `ip_restrictions.restrictions[0]` was evidence commentary about what the healthsheet
   does and does not say. Moved to `ip_restrictions.source_caveats`; the list now holds
   only the actual restriction (licence clause 6).
3. `regulatory_restrictions.regulatory_restrictions[0]` was the same kind of commentary.
   Moved to `source_caveats`; the list now holds only the NIH GDS and HIPAA items.

### Phase 3 finding not fixed: `conforms_to_class` is unrepresentable

`conforms_to_class` is described in the schema as "`Dataset` for a full datasheet,
`CoreDataset` for a core one" — a value that is *required to differ* between the two
records of a pair. The schema-derived Phase 4 rule classifies it as a strict-identity
slot, because its induced range, cardinality and inlining are the same in both classes,
and `--sync-core` would copy the full record's value into core. The two cannot both be
satisfied: writing the schema-correct values fails the gate, and passing the gate makes
the core record claim it instantiates `Dataset`.

Resolution taken: **`conforms_to_class` is omitted from both records.** That is the only
option that neither fails the consistency gate nor writes a false statement. Each record
is validated against its own class by an explicit `-C` argument and its header names its
schema, so no information a consumer needs is lost. `conforms_to_schema` is unaffected —
it is the same value for both and is present in both.

This is a schema/tool defect rather than a property of this project's evidence, and it
will recur for every pair. It is reported here rather than worked around silently.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time from `Dataset` and `CoreDataset` with LinkML
`SchemaView` via `data_sheets_schema.d4d_pair_consistency.load_pair_schema()`; no
hand-written field list was used.

- Shared slots total: **79**
- Schema-identical (strict identity): **78**
- Projected (range differs): **1** — `resources` (`Dataset` in full, `CoreDataset` in
  core). Absent from both records, so the projection is vacuous and coverage is equal.
- Full-only, dropped from core: 17 — `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `parent_datasets`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`. Of these,
  14 are populated in the full record and 3 (`parent_datasets`, `subsets`, `variables`)
  are absent from both.
- Core-only: 2 — `distributions` (populated, the `file_collections` projection) and
  `dialect` (absent; the bundle carries no CSV dialect information).

The core record was **constructed by deep copy** of the full record's identity slots
rather than re-written, so identity is structural and not merely observed. Nothing in
core was condensed, paraphrased, reordered or omitted relative to full; no narrative
field was shortened.

Top-level slot counts (informational metadata, not a quality gate):

- Full: **80** populated top-level slots
- Core: **67** populated top-level slots (66 identity + `distributions`)

80 − 14 populated full-only slots = 66, + `distributions` = 67. The arithmetic closes.

### Related-content mapping: `file_collections` → `distributions`

The validator matched all 9 core distributions to full file collections at collection
level by `id`, with 0 unmatched, and reported no `distribution-related-content`
conflicts. The semantic review the warning asks for was performed and is recorded here:

| id | path | full `total_bytes` → core `bytes` | full `file_count` | `conforms_to` |
|---|---|---|---|---|
| `aireadi:fc-cardiac-ecg` | `cardiac_ecg` | 302,931,703 | 4,515 | WFDB |
| `aireadi:fc-clinical-data` | `clinical_data` | 176,182,781 | 7 | OMOP CDM |
| `aireadi:fc-environment` | `environment` | 55,625,676,514 | 2,232 | NASA ASCII guidelines |
| `aireadi:fc-retinal-flio` | `retinal_flio` | 1,069,466,876,718 | 7,969 | DICOM |
| `aireadi:fc-retinal-oct` | `retinal_oct` | 1,317,625,293,027 | 56,478 | DICOM |
| `aireadi:fc-retinal-octa` | `retinal_octa` | 1,155,908,809,724 | 173,721 | DICOM |
| `aireadi:fc-retinal-photography` | `retinal_photography` | 174,381,046,406 | 93,921 | DICOM |
| `aireadi:fc-wearable-activity` | `wearable_activity_monitor` | 38,313,536,220 | 15,245 | Open mHealth |
| `aireadi:fc-wearable-glucose` | `wearable_blood_glucose` | 4,169,006,971 | 2,246 | Open mHealth |

Review findings:

- `id`, `name`, `path`, `description` and `conforms_to` are byte-identical between the
  matched pairs. `total_bytes` → `bytes` is a lossless rename onto the same integer.
- `file_count` and `collection_type` have **no counterpart on `CoreDistribution`** and
  are dropped in the projection. This is a genuine loss of content, not a conflict:
  `FileCollection` is collection-level (`file_count`, `total_bytes`, `collection_type`)
  while `CoreDistribution` is file-level (`bytes`, `hash`, `md5`, `sha256`, `path`,
  `media_type`). The nine entries here are directories, not files, so they match at
  collection level and the file counts are recoverable only from the full record.
- `format`, `media_type`, `encoding`, `compression`, the three hash slots and
  `used_software` are absent from every distribution because the bundle supplies none of
  them for any directory. No checksum of any kind appears anywhere in the bundle.
- Scope agreement: `total_file_count` (356,343) and `total_size_bytes`
  (3,815,969,779,678) are full-only. Both describe release 3.0.0, the same scope as the
  nine directories, and reconcile against them to within the 9 root metadata files (see
  Phase 3). No contradiction.
- `is_tabular: false` agrees with the distributions: the dataset mixes DICOM imaging,
  WFDB waveforms, Open mHealth JSON and OMOP CSV, so it is not a table. `dialect` is
  absent in core and has no full counterpart; `compression` is absent everywhere,
  consistent with a directory tree rather than an archive.
- Top-level identity, version and access facts agree with the distributions and with the
  version history: `version: 3.0.0`, `doi: 10.60775/fairhub.3`, `issued: 2025-11-17`,
  `version_access.latest_version_doi: https://doi.org/10.60775/fairhub.3`, and the three
  `distribution_dates.release_dates` (2024-05-03, 2024-11-08, 2025-11-17) line up with
  the three `versions_available` entries and the two `related_datasets` entries. Nothing
  restates a superseded figure as current: the 2.01 TB / 165,051-file figures for release
  2.0.0 appear only inside `version_access` and `related_datasets`, explicitly labelled as
  that release's.

### Result

**No divergence between the full and core records.** All 78 schema-identical slots have
identical presence and deeply identical parsed content. The one projected slot is absent
from both. The one related-content projection maps 9-for-9 with zero conflicts and the
only differences are the two collection-level fields the core class does not define.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml

poetry run d4d download scope --project AI_READI
poetry run d4d download scope --check --project AI_READI --strict
```

## Final results

| check | result |
|---|---|
| `linkml-validate` full, class `Dataset` | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core, class `CoreDataset` | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` (final, no `--sync-core`) | PASS: 78 schema-identical slots; projected `['resources']`; 0 errors; 1 semantic-review warning, reviewed above |
| `d4d download scope --check --strict` | in scope — does not identify itself as a dataset the manifest declares distinct |
| Phase 4 header in core | `# Phase 4 reconciliation: completed` present |

## Provenance record

Not written by this agent. The launcher writes the live provenance record for this run:

```bash
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

Reasoning effort is not asserted here. This run was launched through Claude Code without
an effort setting the agent can observe, so nothing is claimed rather than a value being
guessed (#397).
